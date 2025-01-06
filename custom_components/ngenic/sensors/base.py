"""Base class for Ngenic sensors."""

from datetime import timedelta
import logging

from homeassistant.components.sensor import SensorEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.event import async_track_time_interval

from ..ngenicpy import AsyncNgenic  # noqa: TID252
from ..ngenicpy.models.measurement import MeasurementType  # noqa: TID252
from ..ngenicpy.models.node import Node  # noqa: TID252
from ..ngenicpy.models.room import Room  # noqa: TID252
from . import get_measurement_value

_LOGGER = logging.getLogger(__name__)


class NgenicSensor(SensorEntity):
    """Representation of an Ngenic Sensor."""

    def __init__(
        self,
        hass: HomeAssistant,
        ngenic: AsyncNgenic,
        room: Room | None,
        node: Node,
        name: str,
        update_interval: timedelta,
        measurement_type: MeasurementType,
        device_info: DeviceInfo,
    ) -> None:
        """Initialize the sensor."""

        self._hass = hass
        self._state = None
        self._available = False
        self._ngenic = ngenic
        self._name = name
        self._node = node
        self._update_interval = update_interval
        self._measurement_type = measurement_type
        self._updater = None
        self._attributes = {}
        if room is not None:
            self._attributes["room_uuid"] = room.uuid()
        self._attr_device_info = device_info

    @property
    def name(self) -> str:
        """Return the name of the sensor."""
        return f"{self._name} {self.device_class}"

    @property
    def available(self) -> bool:
        """Return if the sensor is available."""
        return self._available

    @property
    def state(self) -> int | None:
        """Return the state of the sensor."""
        return self._state

    @property
    def unique_id(self) -> str:
        """Return a unique ID for the sensor."""
        part = (
            self._measurement_type.name
            if isinstance(self._measurement_type, MeasurementType)
            else self._measurement_type
        )
        return f"{self._node.uuid()}-{part}-sensor"

    @property
    def should_poll(self) -> bool:
        """An update is pushed when device is updated."""
        return False

    @property
    def extra_state_attributes(self):
        """Return entity specific state attributes."""
        return self._attributes

    async def async_will_remove_from_hass(self) -> None:
        """Remove updater when sensor is removed."""
        if self._updater:
            self._updater()
            self._updater = None

    def setup_updater(self) -> None:
        """Configure a timer that will execute an update every update interval."""
        # async_track_time_interval returns a function that, when executed, will remove the timer
        self._updater = async_track_time_interval(
            self._hass, self.async_update, self._update_interval
        )

    async def _async_fetch_measurement(self):
        """Fetch the measurement data from ngenic API.

        Return measurement formatted as intended to be displayed in hass.
        Concrete classes should override this function if they
        fetch or format the measurement differently.
        """
        current = await get_measurement_value(
            self._node, measurement_type=self._measurement_type
        )
        return round(current, 1)

    async def async_update(self, event_time=None):
        """Fetch new state data for the sensor.

        This is the only method that should fetch new data for Home Assistant.
        """
        _LOGGER.debug(
            "Fetch measurement (name=%s, type=%s)",
            self._name,
            self._measurement_type,
        )
        try:
            new_state = await self._async_fetch_measurement()
            self._available = True
        except Exception:
            # Don't throw an exception if a sensor fails to update.
            # Instead, make the sensor unavailable.
            _LOGGER.exception("Failed to update sensor '%s'", self.unique_id)
            self._available = False
            return

        if self._state != new_state:
            self._state = new_state
            _LOGGER.debug(
                "New measurement: %d (name=%s, type=%s)",
                new_state,
                self._name,
                self._measurement_type,
            )

            # self.hass is loaded once the entity have been setup.
            # Since this method is executed before adding the entity
            # the hass object might not have been loaded yet.
            if self.hass:
                # Tell hass that an update is available
                self.schedule_update_ha_state()
        else:
            _LOGGER.debug(
                "No new measurement: %d (name=%s, type=%s)",
                self._state,
                self._name,
                self._measurement_type,
            )

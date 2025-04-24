"""Base class for Ngenic sensors."""

from datetime import timedelta
import logging
from typing import Any

from ngenicpy import AsyncNgenic
from ngenicpy.models.measurement import MeasurementType
from ngenicpy.models.node import Node
from ngenicpy.models.room import Room

from homeassistant.components.sensor import SensorEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.event import async_track_time_interval

from . import get_measurement_value

_LOGGER = logging.getLogger(__name__)


class SlimNgenicSensor(SensorEntity):
    """Representation of a Slim Ngenic Sensor."""

    def __init__(
        self,
        hass: HomeAssistant,
        ngenic: AsyncNgenic,
        unique_id: str,
        name: str,
        update_interval: timedelta,
        device_info: DeviceInfo,
        should_update_on_startup: bool = False,
    ) -> None:
        """Initialize the sensor."""
        self._state = None
        self._available = False
        self._updater = None
        self._hass = hass
        self._ngenic = ngenic
        self._unique_id = unique_id
        self._name = name
        self._update_interval = update_interval
        self._attr_device_info = device_info
        self._should_update_on_startup = should_update_on_startup

    @property
    def unique_id(self) -> str:
        """Return a unique ID for the sensor."""
        return self._unique_id

    @property
    def name(self) -> str:
        """Return the name of the sensor."""
        return self._name.title()

    @property
    def available(self) -> bool:
        """Return if the sensor is available."""
        return self._available

    @property
    def state(self) -> int | None:
        """Return the state of the sensor."""
        return self._state

    @property
    def should_poll(self) -> bool:
        """An update is pushed when device is updated."""
        return False

    @property
    def should_update_on_startup(self) -> bool:
        """Return if the sensor should update on startup or not."""
        return self._should_update_on_startup

    async def _force_update(self) -> None:
        """Force update of data."""
        _LOGGER.debug(
            "Force update (sensor=%s)",
            self.unique_id,
        )
        await self.async_update()
        self.async_write_ha_state()

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

    async def _async_fetch_measurement(self, first_load: bool = False) -> Any:
        """Fetch the measurement data from ngenic API.

        Return measurement formatted as intended to be displayed in hass.
        Concrete classes should override this function if they
        fetch or format the measurement differently.
        """
        return None

    async def async_update(self, first_load: bool = False) -> None:
        """Fetch new state data for the sensor.

        This is the only method that should fetch new data for Home Assistant.
        """
        _LOGGER.debug(
            "Fetch measurement (sensor=%s)",
            self.unique_id,
        )
        try:
            new_state = await self._async_fetch_measurement(first_load)
            self._available = True
        except Exception:
            # Don't throw an exception if a sensor fails to update.
            # Instead, make the sensor unavailable.
            _LOGGER.exception("Failed to update (sensor=%s)", self.unique_id)
            self._available = False
            return

        if self._state != new_state:
            self._state = new_state
            _LOGGER.debug(
                "New measurement: %s (sensor=%s)",
                new_state,
                self.unique_id,
            )

            # self.hass is loaded once the entity have been setup.
            # Since this method is executed before adding the entity
            # the hass object might not have been loaded yet.
            if self.hass:
                # Tell hass that an update is available
                self.schedule_update_ha_state()
        else:
            _LOGGER.debug(
                "No new measurement: %s (sensor=%s)",
                self._state,
                self.unique_id,
            )


class NgenicSensor(SlimNgenicSensor):
    """Representation of a Ngenic Sensor."""

    def __init__(
        self,
        hass: HomeAssistant,
        ngenic: AsyncNgenic,
        room: Room | None,
        node: Node,
        name: str,
        update_interval: timedelta,
        measurement_type: MeasurementType | str,
        device_info: DeviceInfo,
        should_update_on_startup: bool = False,
    ) -> None:
        """Initialize the sensor."""

        super().__init__(
            hass,
            ngenic,
            f"{node.uuid()}-{
                (
                    measurement_type.name
                    if isinstance(measurement_type, MeasurementType)
                    else measurement_type
                )
            }-sensor",
            name,
            update_interval,
            device_info,
            should_update_on_startup,
        )

        self._node = node
        self._measurement_type = measurement_type

        self._attributes = {}
        if room is not None:
            self._attributes["room_uuid"] = room.uuid()

    @property
    def name(self) -> str:
        """Return the name of the sensor."""
        return f"{self._name} {self.device_class}".replace("_", " ").title()

    @property
    def extra_state_attributes(self):
        """Return entity specific state attributes."""
        return self._attributes

    async def _async_fetch_measurement(self, first_load: bool = False):
        """Fetch the measurement data from ngenic API.

        Return measurement formatted as intended to be displayed in hass.
        Concrete classes should override this function if they
        fetch or format the measurement differently.
        """
        current = await get_measurement_value(
            self._node, measurement_type=self._measurement_type
        )
        return round(current, 1)

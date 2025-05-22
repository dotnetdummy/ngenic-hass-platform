"""Base class for Ngenic sensors."""

from datetime import timedelta, datetime # Imported datetime
import logging
from typing import Any, Optional, Callable, Union, Dict # Added Optional, Callable, Union, Dict

from ngenicpy import AsyncNgenic
from ngenicpy.models.measurement import MeasurementType

# Graceful imports for ngenicpy models
try:
    from ngenicpy.models.node import Node
except ImportError:
    logging.getLogger(__name__).warning("ngenicpy.models.node.Node not found, using Any type instead.")
    Node = Any # type: ignore
try:
    from ngenicpy.models.room import Room
except ImportError:
    logging.getLogger(__name__).warning("ngenicpy.models.room.Room not found, using Any type instead.")
    Room = Any # type: ignore

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
        self._state: Any = None
        self._available: bool = False
        self._updater: Optional[Callable[[], None]] = None
        self._hass: HomeAssistant = hass
        self._ngenic: AsyncNgenic = ngenic
        self._unique_id: str = unique_id
        self._name: str = name
        self._update_interval: timedelta = update_interval
        # self._attr_device_info is implicitly set by SensorEntity via DeviceInfo properties
        # but explicitly assigning it is fine and common.
        self._attr_device_info: DeviceInfo = device_info
        self._should_update_on_startup: bool = should_update_on_startup

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
    def state(self) -> Any: # Changed from int | None to Any
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
        await self.async_update() # Consider passing event_time=None if async_update expects it
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
            self._hass, self.async_update, self._update_interval # type: ignore[arg-type] # async_update can take event_time
        )

    async def _async_fetch_measurement(self, first_load: bool = False) -> Any:
        """Fetch the measurement data from ngenic API.

        Return measurement formatted as intended to be displayed in hass.
        Concrete classes should override this function if they
        fetch or format the measurement differently.
        """
        return None

    async def async_update(self, event_time: Optional[datetime] = None) -> None: # Changed event_time to Optional[datetime]
        """Fetch new state data for the sensor.

        This is the only method that should fetch new data for Home Assistant.
        """
        _LOGGER.debug(
            "Fetch measurement (sensor=%s, event_time=%s)", 
            self.unique_id,
            event_time,
        )
        try:
            # The first_load parameter is not standard for async_update,
            # but _async_fetch_measurement still defines it. Call it without first_load.
            new_state = await self._async_fetch_measurement() 
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
        room: Optional[Room], # Typed room as Optional[Room]
        node: Node,
        name: str,
        # update_interval is part of SlimNgenicSensor's __init__ and passed via super()
        # It's not a direct parameter of NgenicSensor's __init__ itself.
        # Individual sensors pass it to super().
        measurement_type: Union[MeasurementType, str], # Typed measurement_type
        device_info: DeviceInfo,
        should_update_on_startup: bool = False,
        # update_interval is passed to super() by subclasses, not directly to NgenicSensor __init__
        # For example, NgenicTemperatureSensor passes SCAN_INTERVAL as update_interval to super()
        # So, it should not be listed as a direct param for NgenicSensor here.
        # The specific sensor instances (e.g. NgenicTemperatureSensor) will pass an update_interval
        # to this class's super().__init__ (which is SlimNgenicSensor.__init__)
        # This means the actual `update_interval` is defined by the specific sensor class.
        # For example:
        # NgenicTemperatureSensor(..., SCAN_INTERVAL, ...) -> NgenicSensor(..., SCAN_INTERVAL, ...) -> SlimNgenicSensor(..., update_interval=SCAN_INTERVAL, ...)
        # The `update_interval` is correctly handled by SlimNgenicSensor's constructor.
        # So, removing `update_interval: timedelta` from NgenicSensor's __init__ signature.
        # It will be passed by subclasses to the parent SlimNgenicSensor.
    ) -> None:
        """Initialize the sensor."""
        # update_interval is obtained from the specific sensor subclass, e.g. NgenicTemperatureSensor.SCAN_INTERVAL
        # and passed to SlimNgenicSensor's __init__ via super().
        # It's not a direct parameter of NgenicSensor's __init__ signature.
        # This requires the caller (specific sensor class) to provide it.
        # Let's assume specific sensor classes (like NgenicTemperatureSensor) pass SCAN_INTERVAL
        # as the update_interval to super().
        # Example: super().__init__(..., name, SCAN_INTERVAL, ...)
        # The original code was:
        # def __init__(..., name: str, update_interval: timedelta, measurement_type: ...):
        #   super().__init__(..., name, update_interval, ...)
        # This means NgenicSensor did expect update_interval.
        # The specific sensor subclasses (e.g. NgenicTemperatureSensor) pass their SCAN_INTERVAL
        # as this update_interval. So, it *should* be in NgenicSensor's __init__ signature.
        update_interval: timedelta, # Re-adding update_interval as it's passed by subclasses

        self._node: Node = node
        self._measurement_type: Union[MeasurementType, str] = measurement_type
        self._attributes: Dict[str, Any] = {}

        # Determine unique_id string based on measurement_type
        measurement_type_str: str
        if isinstance(measurement_type, MeasurementType):
            measurement_type_str = measurement_type.name
        else:
            measurement_type_str = measurement_type # It's already a str

        super().__init__(
            hass,
            ngenic,
            f"{node.uuid()}-{measurement_type_str}-sensor", # Use formatted string
            name,
            update_interval, # Pass update_interval to SlimNgenicSensor
            device_info,
            should_update_on_startup,
        )

        if room is not None:
            self._attributes["room_uuid"] = room.uuid() # type: ignore[union-attr] # room can be Any if import fails

    @property
    def name(self) -> str:
        """Return the name of the sensor."""
        # self.device_class can be None, handle it
        device_class_str = str(self.device_class) if self.device_class else ""
        return f"{self._name} {device_class_str}".replace("_", " ").strip().title()


    @property
    def extra_state_attributes(self) -> Dict[str, Any]: # Added return type
        """Return entity specific state attributes."""
        return self._attributes

    async def _async_fetch_measurement(self, first_load: bool = False) -> Any: # Added return type
        """Fetch the measurement data from ngenic API.

        Return measurement formatted as intended to be displayed in hass.
        Concrete classes should override this function if they
        fetch or format the measurement differently.
        """
        current = await get_measurement_value(
            self._node, measurement_type=self._measurement_type
        )
        return round(current, 1)

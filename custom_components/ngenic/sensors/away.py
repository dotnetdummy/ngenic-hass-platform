"""Ngenic Away Sensors."""

from datetime import timedelta, datetime # Added datetime
import logging
from typing import Optional, Any # Added Optional, Any

from ngenicpy import AsyncNgenic
try:
    from ngenicpy.models.tune import Tune
except ImportError:
    logging.getLogger(__name__).warning("ngenicpy.models.tune.Tune not found, using Any type instead.")
    Tune = Any # type: ignore
try:
    from ngenicpy.models.setpoint_schedule import SetpointSchedule
except ImportError:
    logging.getLogger(__name__).warning("ngenicpy.models.setpoint_schedule.SetpointSchedule not found, using Any type instead.")
    SetpointSchedule = Any # type: ignore


from homeassistant.components.sensor import SensorDeviceClass, SensorStateClass
from homeassistant.core import HomeAssistant
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.helpers.entity import DeviceInfo, slugify

from ..const import (  # noqa: TID252 # Relative import is fine here
    BRAND,
    DOMAIN,
    SETPONT_SCHEDULE_NAME, # Note: Typo in constant name (SETPONT vs SETPOINT)
    UPDATE_SCHEDULE_TOPIC,
)
from .base import SlimNgenicSensor

_LOGGER = logging.getLogger(__name__)


class NgenicBaseAwaySensor(SlimNgenicSensor):
    """Base representation of a Ngenic Away Sensor."""

    def __init__(
        self,
        hass: HomeAssistant,
        ngenic: AsyncNgenic,
        update_interval: timedelta,
        tune: Tune,
        name: str,
    ) -> None:
        """Initialize the sensor."""

        # Using type: ignore for dictionary access on Tune object if its structure isn't fully known by stubs
        device_info_name: str = f"Ngenic Tune {tune['tuneName']}" # type: ignore[index]

        super().__init__(
            hass,
            ngenic,
            slugify(f"{tune.uuid()} {name} sensor"), # type: ignore[union-attr] # tune can be Any
            f"{device_info_name} {name}",
            update_interval,
            DeviceInfo(
                identifiers={(DOMAIN, f"tune_{tune['tuneUuid']}")}, # type: ignore[index]
                manufacturer=BRAND,
                name=device_info_name,
                model="Tune",
            ),
            True, # should_update_on_startup
        )

        self._tune: Tune = tune

    async def async_added_to_hass(self) -> None:
        """Register callbacks."""
        _LOGGER.debug("Registering callbacks for %s", self.unique_id)
        # _force_update is defined in SlimNgenicSensor and takes no arguments other than self
        # The dispatcher will call it without arguments.
        self.async_on_remove(
            async_dispatcher_connect(
                self.hass, UPDATE_SCHEDULE_TOPIC, self._force_update
            )
        )


class NgenicAwayModeSensor(NgenicBaseAwaySensor):
    """Representation of a Ngenic Away Mode Sensor."""

    # These are class attributes, already correctly typed by their values
    device_class: SensorDeviceClass = SensorDeviceClass.ENUM
    state_class: SensorStateClass = SensorStateClass.MEASUREMENT
    _attr_icon: str = "mdi:home-off"
    # For ENUM device class, options should be specified if possible
    # _attr_options: List[str] = ["Active", "Inactive"] (Example)


    def __init__(
        self,
        hass: HomeAssistant,
        ngenic: AsyncNgenic,
        update_interval: timedelta,
        tune: Tune,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(hass, ngenic, update_interval, tune, "Away mode")

    async def _async_fetch_measurement(self, first_load: bool = False) -> Optional[str]: # Return Optional[str]
        # isinstance check is good, but if Tune is Any, it might not behave as expected
        # Assuming self._tune has async_setpoint_schedule if it's not Any
        schedule: Optional[SetpointSchedule] = None
        try:
            if hasattr(self._tune, "async_setpoint_schedule"):
                schedule = await self._tune.async_setpoint_schedule( # type: ignore[union-attr]
                    SETPONT_SCHEDULE_NAME, not first_load
                )
            if schedule and hasattr(schedule, "active"):
                return "Active" if schedule.active() else "Inactive" # type: ignore[union-attr]
        except Exception as e:
            _LOGGER.error("Error fetching away mode for %s: %s", self.unique_id, e)
        return None


class NgenicAwayScheduledFromSensor(NgenicBaseAwaySensor):
    """Representation of a Ngenic AwayScheduled From Sensor."""

    device_class: SensorDeviceClass = SensorDeviceClass.TIMESTAMP
    state_class: SensorStateClass = SensorStateClass.MEASUREMENT # Timestamps are points in time, not measurements. Consider removing.

    def __init__(
        self,
        hass: HomeAssistant,
        ngenic: AsyncNgenic,
        update_interval: timedelta,
        tune: Tune,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(hass, ngenic, update_interval, tune, "Away scheduled from")

    async def _async_fetch_measurement(self, first_load: bool = False) -> Optional[str]: # Returns ISO str or None
        val: Optional[str] = None
        schedule: Optional[SetpointSchedule] = None
        try:
            if hasattr(self._tune, "async_setpoint_schedule"):
                schedule = await self._tune.async_setpoint_schedule( # type: ignore[union-attr]
                    SETPONT_SCHEDULE_NAME, not first_load
                )
            if schedule and hasattr(schedule, "start_time"):
                start_dt: Optional[datetime] = schedule.start_time() # type: ignore[union-attr]
                if start_dt:
                    val = start_dt.isoformat()
        except Exception as e: # Catch more specific exceptions if possible
            _LOGGER.warning("Could not fetch away schedule start_time for %s: %s", self.unique_id, e)
            val = None # Ensure val is None on error
        return val


class NgenicAwayScheduledToSensor(NgenicBaseAwaySensor):
    """Representation of a Ngenic Away Scheduled To Sensor."""

    device_class: SensorDeviceClass = SensorDeviceClass.TIMESTAMP
    state_class: SensorStateClass = SensorStateClass.MEASUREMENT # Timestamps are points in time, not measurements. Consider removing.

    def __init__(
        self,
        hass: HomeAssistant,
        ngenic: AsyncNgenic,
        update_interval: timedelta,
        tune: Tune,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(hass, ngenic, update_interval, tune, "Away scheduled to")

    async def _async_fetch_measurement(self, first_load: bool = False) -> Optional[str]: # Returns ISO str or None
        val: Optional[str] = None
        schedule: Optional[SetpointSchedule] = None
        try:
            if hasattr(self._tune, "async_setpoint_schedule"):
                schedule = await self._tune.async_setpoint_schedule( # type: ignore[union-attr]
                    SETPONT_SCHEDULE_NAME, not first_load
                )
            if schedule and hasattr(schedule, "end_time"):
                end_dt: Optional[datetime] = schedule.end_time() # type: ignore[union-attr]
                if end_dt:
                    val = end_dt.isoformat()
        except Exception as e: # Catch more specific exceptions if possible
            _LOGGER.warning("Could not fetch away schedule end_time for %s: %s", self.unique_id, e)
            val = None # Ensure val is None on error
        return val

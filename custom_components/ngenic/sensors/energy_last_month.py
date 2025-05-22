"""Ngenic Energy Sensor (last month)."""

import logging # Added logging
from datetime import datetime, timedelta
from typing import Optional, Tuple, Any # Added Optional, Tuple, Any

from ngenicpy import AsyncNgenic
try:
    from ngenicpy.models.measurement import MeasurementType
except ImportError:
    logging.getLogger(__name__).warning("ngenicpy.models.measurement.MeasurementType not found, using Any type instead.")
    MeasurementType = Any # type: ignore
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


from homeassistant.components.sensor import SensorDeviceClass, SensorStateClass # Added SensorStateClass
from homeassistant.const import UnitOfEnergy
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo

from . import get_measurement_value # TIME_ZONE removed as _get_last_month_naive_period returns datetimes
from .base import NgenicSensor


def _get_last_month_naive_period() -> Tuple[datetime, datetime]: # Renamed and changed return type
    """Get a period for last month.

    Returns two naive datetime objects:
    The first datetime will be at 00:00 on the first day of last month.
    The second datetime will be at 00:00 on the first day of this month.
    """
    now = datetime.now()
    this_month_first_day = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    last_month_last_day = this_month_first_day - timedelta(days=1)
    last_month_first_day = last_month_last_day.replace(day=1)
    
    return last_month_first_day, this_month_first_day


class NgenicEnergyLastMonthSensor(NgenicSensor):
    """Representation of an Ngenic Energy Sensor (last month)."""

    device_class: SensorDeviceClass = SensorDeviceClass.ENERGY
    # TOTAL_INCREASING might not be suitable for "last month" as it's a fixed past period.
    # Consider SensorStateClass.TOTAL or None if it represents a snapshot.
    # For now, keeping it consistent with NgenicEnergySensor if that's the desired behavior.
    # However, a sensor for "last month's total" is typically not "increasing".
    # Let's assume it's a total for that specific past period, so SensorStateClass.TOTAL might be more appropriate.
    state_class: Optional[SensorStateClass] = SensorStateClass.TOTAL 
    _attr_native_unit_of_measurement: str = UnitOfEnergy.KILO_WATT_HOUR # Set as attribute
    # _attr_icon: str = "mdi:counter" # Example icon

    def __init__(
        self,
        hass: HomeAssistant,
        ngenic: AsyncNgenic,
        room: Optional[Room], # room can be Optional
        node: Node,
        name: str, # Base name
        measurement_type: MeasurementType,
        device_info: DeviceInfo,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(
            hass,
            ngenic,
            room,
            node,
            name, # Pass base name
            timedelta(minutes=60), # update_interval
            measurement_type,
            device_info,
            # should_update_on_startup can be True, defaults to False in NgenicSensor.
            # For a "last month" sensor, it should probably update on startup.
            should_update_on_startup=True 
        )
        # Override unique_id to make it distinct from other energy sensors for the same node/measurement_type
        measurement_type_str: str = self._measurement_type.name if hasattr(self._measurement_type, "name") else str(self._measurement_type) # type: ignore
        self._attr_unique_id = f"{self._node.uuid()}-{measurement_type_str}-sensor-last-month" # type: ignore[union-attr]


    # unit_of_measurement property is now handled by _attr_native_unit_of_measurement

    @property
    def name(self) -> str: # Typed return
        """Return the name of the sensor."""
        measurement_type_name: str = "Energy" # Default
        if hasattr(self._measurement_type, "name"):
            measurement_type_name = self._measurement_type.name.replace('_', ' ') # type: ignore
        
        return f"{self._name} Last Month {measurement_type_name}".title()

    # The unique_id property is overridden by setting self._attr_unique_id in __init__

    async def _async_fetch_measurement(self, first_load: bool = False) -> Optional[float]: # Return Optional[float]
        """Ask for measurements for a duration.

        This requires some further inputs, so we'll override the _async_fetch_measurement method.
        """
        from_dt_naive, to_dt_naive = _get_last_month_naive_period()
        
        val: Optional[float] = await get_measurement_value(
            self._node, # type: ignore[arg-type]
            measurement_type=self._measurement_type, # type: ignore[arg-type]
            from_dt=from_dt_naive,
            to_dt=to_dt_naive,
            invalidate_cache=True # Always invalidate for past fixed periods? Or use first_load.
                                  # For "last month", it should be fairly static after the month ends.
                                  # Let's use first_load for now, implying it refetches if HA restarts mid-month.
                                  # Or, True if we want it to refresh on its scan_interval (e.g., daily for this sensor).
                                  # Given SCAN_INTERVAL is 60 mins, True seems reasonable for daily data.
        )
        
        if val is not None:
            return round(val, 1)
        return None

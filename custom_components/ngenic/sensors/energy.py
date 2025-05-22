"""Ngenic Energy Sensor."""

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


from homeassistant.components.sensor import SensorDeviceClass, SensorStateClass
from homeassistant.const import UnitOfEnergy
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo

from . import TIME_ZONE, get_measurement_value # TIME_ZONE is str
from .base import NgenicSensor


def _get_from_to_iso_timestamps(days: int = 1) -> Tuple[datetime, datetime]: # Changed return to tuple[datetime, datetime]
    """Get a period.

    Returns two datetime objects:
    The first datetime will be at 00:00 today.
    The second datetime will be at 00:00 n days ahead of now.
    These are naive datetimes, timezone will be handled by ngenicpy if needed or by API.
    """
    # It's better to use timezone-aware datetimes if the API expects specific timezone handling for from/to.
    # However, the original code used naive datetime.now() and appended TIME_ZONE string separately.
    # For now, returning naive datetimes as the original function's string combination was complex.
    # ngenicpy or the underlying API might handle timezone conversion based on the TIME_ZONE string.
    # The get_measurement_value function now takes Optional[datetime] for from_dt, to_dt.
    from_dt_naive = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    to_dt_naive = from_dt_naive + timedelta(days=days)
    return (from_dt_naive, to_dt_naive)


class NgenicEnergySensor(NgenicSensor):
    """Representation of an Ngenic Energy Sensor."""

    device_class: SensorDeviceClass = SensorDeviceClass.ENERGY
    state_class: SensorStateClass = SensorStateClass.TOTAL_INCREASING
    _attr_native_unit_of_measurement: str = UnitOfEnergy.KILO_WATT_HOUR # Set as attribute
    # _attr_icon: str = "mdi:flash" # Example icon

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
            timedelta(minutes=10), # update_interval
            measurement_type,
            device_info,
            True,  # should_update_on_startup
        )
        # The name property below will override the default name generation in NgenicSensor
        # to include the specific measurement type (ENERGY or PRODUCED_ENERGY).

    # unit_of_measurement property is now handled by _attr_native_unit_of_measurement

    @property
    def name(self) -> str: # Typed return
        """Return the name of the sensor."""
        measurement_type_name: str = "Energy" # Default
        if hasattr(self._measurement_type, "name"):
            measurement_type_name = self._measurement_type.name.replace('_', ' ') # type: ignore
        
        return f"{self._name} {measurement_type_name}".title()

    async def _async_fetch_measurement(self, first_load: bool = False) -> Optional[float]: # Return Optional[float]
        """Ask for measurements for a duration.

        This requires some further inputs, so we'll override the _async_fetch_measurement method.
        """
        # Get naive datetime objects for the period.
        # The get_measurement_value function will handle these Optional[datetime] parameters.
        from_dt_naive, to_dt_naive = _get_from_to_iso_timestamps()
        
        # get_measurement_value now returns Optional[float]
        val: Optional[float] = await get_measurement_value(
            self._node, # type: ignore[arg-type]
            measurement_type=self._measurement_type, # type: ignore[arg-type]
            from_dt=from_dt_naive, # Pass naive datetime
            to_dt=to_dt_naive,     # Pass naive datetime
            # invalidate_cache could be True if first_load is True, if desired.
            invalidate_cache=first_load 
        )
        
        if val is not None:
            return round(val, 1)
        return None

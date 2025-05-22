"""Ngenic Current Sensor.""" # Corrected docstring from "Power Sensor"

import logging # Added logging
from datetime import timedelta
from typing import Optional, Any # Added Optional, Any

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
from homeassistant.const import UnitOfElectricCurrent
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo

from . import get_measurement_value
from .base import NgenicSensor


class NgenicCurrentSensor(NgenicSensor):
    """Representation of an Ngenic Current Sensor."""

    device_class: SensorDeviceClass = SensorDeviceClass.CURRENT
    state_class: SensorStateClass = SensorStateClass.MEASUREMENT
    _attr_native_unit_of_measurement: str = UnitOfElectricCurrent.AMPERE # Set as attribute
    # _attr_icon: str = "mdi:current-ac" # Example icon

    def __init__(
        self,
        hass: HomeAssistant,
        ngenic: AsyncNgenic,
        room: Optional[Room], # room can be Optional
        node: Node,
        name: str, # Base name, NgenicSensor will append device_class if not overridden
        measurement_type: MeasurementType, # This is specific to current sensor (L1, L2, L3)
        device_info: DeviceInfo,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(
            hass,
            ngenic,
            room,
            node,
            name, # Pass base name
            timedelta(minutes=2),  # update_interval (SCAN_INTERVAL_TRACK)
            measurement_type,      # measurement_type
            device_info,
            True,  # should_update_on_startup
        )
        # The name property below will override the default name generation in NgenicSensor
        # to include the specific measurement type (L1, L2, L3).

    @property
    def name(self) -> str: # Typed return
        """Return the name of the sensor."""
        # Assuming _measurement_type is MeasurementType or Any (if import failed)
        # and has a 'name' attribute.
        measurement_type_name: str = "Current" # Default
        if hasattr(self._measurement_type, "name"):
            measurement_type_name = self._measurement_type.name.replace('_', ' ') # type: ignore
        
        # self._name is the base name passed in __init__ (e.g., "Ngenic Track")
        return f"{self._name} {measurement_type_name}".title()

    # unit_of_measurement property is now handled by _attr_native_unit_of_measurement

    async def _async_fetch_measurement(self, first_load: bool = False) -> Optional[float]: # Return Optional[float]
        """Fetch new electric current state data for the sensor."""
        # get_measurement_value now returns Optional[float] and handles logging/errors.
        val: Optional[float] = await get_measurement_value(
            self._node, # type: ignore[arg-type] # _node can be Any
            measurement_type=self._measurement_type, # type: ignore[arg-type] # _measurement_type can be Any
            invalidate_cache=True # Or based on first_load if needed
        )
        
        if val is not None:
            return round(val, 1)
        return None

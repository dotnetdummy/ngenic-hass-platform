"""Ngenic Temperature Sensor."""

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
from homeassistant.const import UnitOfTemperature
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo

from .base import NgenicSensor


class NgenicTemperatureSensor(NgenicSensor):
    """Representation of an Ngenic Temperature Sensor."""

    device_class: SensorDeviceClass = SensorDeviceClass.TEMPERATURE
    state_class: SensorStateClass = SensorStateClass.MEASUREMENT
    _attr_native_unit_of_measurement: str = UnitOfTemperature.CELSIUS # Set as attribute
    # _attr_icon: str = "mdi:thermometer" # Default icon is usually fine for temperature

    def __init__(
        self,
        hass: HomeAssistant,
        ngenic: AsyncNgenic,
        room: Optional[Room], # room can be Optional
        node: Node,
        name: str, # Base name
        measurement_type: MeasurementType, # e.g. MeasurementType.TEMPERATURE or MeasurementType.CONTROL_VALUE
        device_info: DeviceInfo,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(
            hass,
            ngenic,
            room,
            node,
            name, # Pass base name
            timedelta(minutes=5),  # update_interval (SCAN_INTERVAL_THERMOSTAT)
            measurement_type,      # measurement_type
            device_info,
            True,  # should_update_on_startup
        )
        # The name property in NgenicSensor base class will be used by default.
        # It appends the device_class, e.g., "My Node Temperature".
        # If specific naming for "Control Temperature" is needed (e.g. from SENSOR_CONFIG_MAP),
        # the `name` passed to __init__ should already include it.

    # unit_of_measurement property is now handled by _attr_native_unit_of_measurement
    # _async_fetch_measurement is inherited from NgenicSensor, which calls get_measurement_value.
    # No override needed if default behavior (fetch, round to 1 decimal) is fine.

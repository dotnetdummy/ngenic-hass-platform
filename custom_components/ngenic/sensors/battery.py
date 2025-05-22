"""Ngenic Battery Sensor."""

from datetime import timedelta
import logging
from typing import Optional, Any # Added Optional, Any

from ngenicpy import AsyncNgenic
try:
    from ngenicpy.models.node import Node, NodeStatus
except ImportError:
    _LOGGER_ref = logging.getLogger(__name__) # Logger needed for fallback
    _LOGGER_ref.warning("ngenicpy.models.node.Node or NodeStatus not found, using Any type instead.")
    Node = Any # type: ignore
    NodeStatus = Any # type: ignore
try:
    from ngenicpy.models.room import Room
except ImportError:
    _LOGGER_ref = logging.getLogger(__name__) # Logger needed for fallback
    _LOGGER_ref.warning("ngenicpy.models.room.Room not found, using Any type instead.")
    Room = Any # type: ignore


from homeassistant.components.sensor import SensorDeviceClass, SensorStateClass
from homeassistant.const import PERCENTAGE # Added PERCENTAGE
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo

from .base import NgenicSensor

_LOGGER = logging.getLogger(__name__)


class NgenicBatterySensor(NgenicSensor):
    """Representation of an Ngenic Battery Sensor."""

    device_class: SensorDeviceClass = SensorDeviceClass.BATTERY
    state_class: SensorStateClass = SensorStateClass.MEASUREMENT
    _attr_native_unit_of_measurement: str = PERCENTAGE # Set as attribute
    # _attr_icon: str = "mdi:battery" # Optional: if a specific icon is desired

    def __init__(
        self,
        hass: HomeAssistant,
        ngenic: AsyncNgenic,
        room: Optional[Room], # room can be Optional
        node: Node,
        name: str, # This is the base name, NgenicSensor will append device_class
        device_info: DeviceInfo,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(
            hass,
            ngenic,
            room,
            node,
            name, # Pass base name
            timedelta(minutes=5),  # update_interval
            "BATTERY",  # measurement_type (string for specific sensors like this)
            device_info,
            # should_update_on_startup can be True if needed, defaults to False in NgenicSensor
        )

    # unit_of_measurement property is now handled by _attr_native_unit_of_measurement

    async def _async_fetch_measurement(self, first_load: bool = False) -> Optional[int]: # Return Optional[int]
        status: Optional[NodeStatus] = None # Initialize status
        current: int = 100 # Default to 100 if status cannot be fetched or parsed

        try:
            # Check if _node is not Any and has async_status method
            if hasattr(self._node, "async_status"):
                status = await self._node.async_status() # type: ignore[union-attr]
            else:
                _LOGGER.debug("Node object does not support status fetching (type: %s)", type(self._node).__name__)
        except Exception as e:
            _LOGGER.error("Error fetching node status for %s: %s", self.unique_id, e)
            # Keep current = 100 (default), or set to None if unavailable is preferred
            return None # Or current if 100 default is okay on error

        if status and hasattr(status, "battery_percentage"):
            try:
                # Ensure battery_percentage returns int or can be cast
                battery_val = status.battery_percentage() # type: ignore[union-attr]
                if battery_val is not None:
                    current = int(battery_val)
                else:
                    _LOGGER.debug("Battery percentage is None for %s, defaulting to 100", self.unique_id)
            except (ValueError, TypeError) as e:
                _LOGGER.error("Error parsing battery percentage for %s: %s", self.unique_id, e)
                # Keep current = 100 or set to None
                return None # Or current
        else:
            _LOGGER.debug("Assume battery is full (100%%) as status or battery_percentage is unavailable for %s", self.unique_id)
            # current remains 100

        return current

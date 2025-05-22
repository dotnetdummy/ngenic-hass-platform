"""Ngenic Signal Strength Sensor."""

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
from homeassistant.const import PERCENTAGE # Using PERCENTAGE as it returns percentage
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo, EntityCategory # Added EntityCategory

from .base import NgenicSensor

_LOGGER = logging.getLogger(__name__)


class NgenicSignalStrengthSensor(NgenicSensor):
    """Representation of an Ngenic Signal Strength Sensor."""

    device_class: SensorDeviceClass = SensorDeviceClass.SIGNAL_STRENGTH
    state_class: SensorStateClass = SensorStateClass.MEASUREMENT
    _attr_native_unit_of_measurement: str = PERCENTAGE # Current implementation returns percentage
    _attr_entity_category: EntityCategory = EntityCategory.DIAGNOSTIC # Signal strength is diagnostic
    _attr_icon: str = "mdi:wifi" # Example icon, can also use SIGNAL_STRENGTH class default

    def __init__(
        self,
        hass: HomeAssistant,
        ngenic: AsyncNgenic,
        room: Optional[Room], # room can be Optional
        node: Node,
        name: str, # Base name
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
            "SIGNAL_STRENGTH",     # measurement_type string for specific sensors like this
                                   # Changed from "SIGNAL" to be more descriptive
            device_info,
            # should_update_on_startup can be True if needed
        )
        # The name property in NgenicSensor base class will be used by default.
        # It appends device_class, e.g. "My Node Signal Strength"
        # If a different naming is needed, override self.name property here.

    # unit_of_measurement property is now handled by _attr_native_unit_of_measurement

    async def _async_fetch_measurement(self, first_load: bool = False) -> Optional[int]: # Return Optional[int]
        status: Optional[NodeStatus] = None
        current: int = 100 # Default to 100% if status cannot be fetched or parsed

        try:
            if hasattr(self._node, "async_status"):
                status = await self._node.async_status() # type: ignore[union-attr]
            else:
                _LOGGER.debug("Node object does not support status fetching (type: %s)", type(self._node).__name__)
        except Exception as e:
            _LOGGER.error("Error fetching node status for %s: %s", self.unique_id, e)
            return None # Or current if 100 default is okay on error

        if status and hasattr(status, "radio_signal_percentage"):
            try:
                signal_val = status.radio_signal_percentage() # type: ignore[union-attr]
                if signal_val is not None:
                    current = int(signal_val)
                else:
                    _LOGGER.debug("Signal strength percentage is None for %s, defaulting to 100", self.unique_id)
            except (ValueError, TypeError) as e:
                _LOGGER.error("Error parsing signal strength for %s: %s", self.unique_id, e)
                return None # Or current
        else:
            _LOGGER.debug("Assume signal is full (100%%) as status or radio_signal_percentage is unavailable for %s", self.unique_id)
            # current remains 100

        return current

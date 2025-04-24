"""Ngenic Signal Strength Sensor."""

from datetime import timedelta
import logging

from ngenicpy import AsyncNgenic
from ngenicpy.models.node import Node, NodeStatus
from ngenicpy.models.room import Room

from homeassistant.components.sensor import SensorDeviceClass, SensorStateClass
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo

from .base import NgenicSensor

_LOGGER = logging.getLogger(__name__)


class NgenicSignalStrengthSensor(NgenicSensor):
    """Representation of an Ngenic Signal Strength Sensor."""

    device_class = SensorDeviceClass.SIGNAL_STRENGTH
    state_class = SensorStateClass.MEASUREMENT

    def __init__(
        self,
        hass: HomeAssistant,
        ngenic: AsyncNgenic,
        room: Room,
        node: Node,
        name: str,
        device_info: DeviceInfo,
    ) -> None:
        """Initialize the sensor."""

        super().__init__(
            hass,
            ngenic,
            room,
            node,
            name,
            timedelta(minutes=5),
            "SIGNAL",
            device_info,
        )

    @property
    def unit_of_measurement(self):
        """Return the unit of measurement."""
        return "%"

    async def _async_fetch_measurement(self, first_load: bool = False):
        if isinstance(self._node, Node):
            status = await self._node.async_status()

        if isinstance(status, NodeStatus):
            current = status.radio_signal_percentage()
        else:
            _LOGGER.debug("Assume signal is full if we can't get the status")
            current = 100

        return current

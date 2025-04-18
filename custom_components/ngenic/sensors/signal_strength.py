"""Ngenic Signal Strength Sensor."""

import logging

from ngenicpy.models.node import Node, NodeStatus  # noqa: TID252

from homeassistant.components.sensor import SensorDeviceClass, SensorStateClass

from .base import NgenicSensor

_LOGGER = logging.getLogger(__name__)


class NgenicSignalStrengthSensor(NgenicSensor):
    """Representation of an Ngenic Signal Strength Sensor."""

    device_class = SensorDeviceClass.SIGNAL_STRENGTH
    state_class = SensorStateClass.MEASUREMENT

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

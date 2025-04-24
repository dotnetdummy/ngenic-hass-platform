"""Ngenic Power Sensor."""

from datetime import timedelta

from ngenicpy import AsyncNgenic
from ngenicpy.models.measurement import MeasurementType
from ngenicpy.models.node import Node
from ngenicpy.models.room import Room

from homeassistant.components.sensor import SensorDeviceClass, SensorStateClass
from homeassistant.const import UnitOfElectricCurrent
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo

from . import get_measurement_value
from .base import NgenicSensor


class NgenicCurrentSensor(NgenicSensor):
    """Representation of an Ngenic Current Sensor."""

    device_class = SensorDeviceClass.CURRENT
    state_class = SensorStateClass.MEASUREMENT

    def __init__(
        self,
        hass: HomeAssistant,
        ngenic: AsyncNgenic,
        room: Room,
        node: Node,
        name: str,
        measurement_type: MeasurementType,
        device_info: DeviceInfo,
    ) -> None:
        """Initialize the sensor."""

        super().__init__(
            hass,
            ngenic,
            room,
            node,
            name,
            timedelta(minutes=2),
            measurement_type,
            device_info,
            True,
        )

    @property
    def name(self):
        """Return the name of the sensor."""
        return f"{self._name} {self._measurement_type.name.replace('_', ' ')}".title()

    @property
    def unit_of_measurement(self):
        """Return the unit of measurement."""
        return UnitOfElectricCurrent.AMPERE

    async def _async_fetch_measurement(self, first_load: bool = False):
        """Fetch new electric current state data for the sensor."""
        val = await get_measurement_value(
            self._node, measurement_type=self._measurement_type, invalidate_cache=True
        )
        return round(val, 1)

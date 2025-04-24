"""Ngenic Temperature Sensor."""

from datetime import timedelta

from ngenicpy import AsyncNgenic
from ngenicpy.models.measurement import MeasurementType
from ngenicpy.models.node import Node
from ngenicpy.models.room import Room

from homeassistant.components.sensor import SensorDeviceClass, SensorStateClass
from homeassistant.const import UnitOfTemperature
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo

from .base import NgenicSensor


class NgenicTemperatureSensor(NgenicSensor):
    """Representation of an Ngenic Temperature Sensor."""

    device_class = SensorDeviceClass.TEMPERATURE
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
            timedelta(minutes=5),
            measurement_type,
            device_info,
            True,
        )

    @property
    def unit_of_measurement(self):
        """Return the unit of measurement."""
        return UnitOfTemperature.CELSIUS

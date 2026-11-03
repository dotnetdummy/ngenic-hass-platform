"""Ngenic Humidity Sensor."""

from datetime import timedelta

from ngenicpy import AsyncNgenic
from ngenicpy.models.measurement import MeasurementType
from ngenicpy.models.node import Node
from ngenicpy.models.room import Room

from homeassistant.components.sensor import SensorDeviceClass, SensorStateClass
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo

from .base import NgenicSensor


class NgenicHumiditySensor(NgenicSensor):
    """Representation of an Ngenic Humidity Sensor."""

    device_class = SensorDeviceClass.HUMIDITY
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
        return "%"

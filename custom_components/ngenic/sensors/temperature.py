"""Ngenic Temperature Sensor."""

from datetime import timedelta

from ngenicpy import AsyncNgenic
from ngenicpy.models.measurement import MeasurementType
from ngenicpy.models.node import Node
from ngenicpy.models.room import Room

from homeassistant.components.sensor import SensorDeviceClass, SensorStateClass
from homeassistant.const import UnitOfTemperature
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo

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

    async def _async_fetch_measurement(self, first_load: bool = False):
        value = await super()._async_fetch_measurement(first_load)
        if value is None and self._measurement_type == MeasurementType.CONTROL_VALUE:
            # the gateway doesn't always report a control value, show 0 as before
            return 0
        return value

"""Ngenic Power Sensor."""

from homeassistant.components.sensor import SensorDeviceClass, SensorStateClass
from homeassistant.const import UnitOfPower

from . import get_measurement_value
from .base import NgenicSensor


class NgenicPowerSensor(NgenicSensor):
    """Representation of an Ngenic Power Sensor."""

    device_class = SensorDeviceClass.POWER
    state_class = SensorStateClass.MEASUREMENT

    @property
    def unit_of_measurement(self):
        """Return the unit of measurement."""
        return UnitOfPower.WATT

    async def _async_fetch_measurement(self, first_load: bool = False):
        """Fetch new power state data for the sensor.

        The NGenic API returns a float with kW but HA huses W so we need to multiply by 1000
        """
        current = await get_measurement_value(
            self._node, measurement_type=self._measurement_type
        )
        return round(current * 1000.0, 1)

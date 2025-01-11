"""Ngenic Energy Sensor."""

from datetime import datetime, timedelta

from homeassistant.components.sensor import SensorDeviceClass, SensorStateClass
from homeassistant.const import UnitOfEnergy

from . import TIME_ZONE, get_measurement_value
from .base import NgenicSensor


def _get_from_to_datetime(days=1):
    """Get a period.

    This will return two dates in ISO 8601:2004 format
    The first date will be at 00:00 today, and the second
    date will be at 00:00 n days ahead of now.

    Both dates include the time zone name, or `Z` in case of UTC.
    Including these will allow the API to handle DST correctly.

    When asking for measurements, the `from` datetime is inclusive
    and the `to` datetime is exclusive.
    """
    from_dt = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    to_dt = from_dt + timedelta(days=days)

    return (from_dt.isoformat() + " " + TIME_ZONE, to_dt.isoformat() + " " + TIME_ZONE)


class NgenicEnergySensor(NgenicSensor):
    """Representation of an Ngenic Energy Sensor."""

    device_class = SensorDeviceClass.ENERGY
    state_class = SensorStateClass.TOTAL_INCREASING

    @property
    def unit_of_measurement(self):
        """Return the unit of measurement."""
        return UnitOfEnergy.KILO_WATT_HOUR

    async def _async_fetch_measurement(self, first_load: bool = False):
        """Ask for measurements for a duration.

        This requires some further inputs, so we'll override the _async_fetch_measurement method.
        """
        from_dt, to_dt = _get_from_to_datetime()
        # using datetime will return a list of measurements
        # we'll use the last item in that list
        current = await get_measurement_value(
            self._node,
            measurement_type=self._measurement_type,
            from_dt=from_dt,
            to_dt=to_dt,
        )
        return round(current, 1)

    @property
    def name(self):
        """Return the name of the sensor."""
        return f"{self._name} energy"

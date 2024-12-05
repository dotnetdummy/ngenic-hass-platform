"""Ngenic Energy Sensor (last month)."""

from datetime import datetime, timedelta

from homeassistant.components.sensor import SensorDeviceClass
from homeassistant.const import UnitOfEnergy

from . import TIME_ZONE, get_measurement_value
from .base import NgenicSensor


def _get_from_to_datetime_last_month() -> tuple[str, str]:
    """Get a period for last month.

    This will return two dates in ISO 8601:2004 format
    The first date will be at 00:00 in the first of last month, and the second
    date will be at 00:00 in the first day in this month.

    Both dates include the time zone name, or `Z` in case of UTC.
    Including these will allow the API to handle DST correctly.

    When asking for measurements, the `from` datetime is inclusive
    and the `to` datetime is exclusive.
    """
    to_dt = datetime.now().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    from_dt = (to_dt + timedelta(days=-1)).replace(day=1)
    return (from_dt.isoformat() + " " + TIME_ZONE, to_dt.isoformat() + " " + TIME_ZONE)


class NgenicEnergyLastMonthSensor(NgenicSensor):
    """Representation of an Ngenic Energy Sensor (last month)."""

    device_class = SensorDeviceClass.ENERGY

    @property
    def unit_of_measurement(self):
        """Return the unit of measurement."""
        return UnitOfEnergy.KILO_WATT_HOUR

    async def _async_fetch_measurement(self):
        """Ask for measurements for a duration.

        This requires some further inputs, so we'll override the _async_fetch_measurement method.
        """
        from_dt, to_dt = _get_from_to_datetime_last_month()
        current = await get_measurement_value(
            self._node,
            measurement_type=self._measurement_type,
            from_dt=from_dt,
            to_dt=to_dt,
        )
        return round(current, 1)

    @property
    def name(self) -> str:
        """Return the name of the sensor."""
        return f"{self._name} last month energy"

    @property
    def unique_id(self) -> str:
        """Return a unique ID for the sensor."""
        return f"{self._node.uuid()}-{self._measurement_type.name}-sensor-last-month"

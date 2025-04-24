"""Ngenic Energy Sensor (this month)."""

from datetime import datetime, timedelta

from ngenicpy import AsyncNgenic
from ngenicpy.models.measurement import MeasurementType
from ngenicpy.models.node import Node
from ngenicpy.models.room import Room

from homeassistant.components.sensor import SensorDeviceClass
from homeassistant.const import UnitOfEnergy
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo

from . import TIME_ZONE, get_measurement_value
from .base import NgenicSensor


def _get_from_to_datetime_month():
    """Get a period for this month.

    This will return two dates in ISO 8601:2004 format
    The first date will be at 00:00 in the first of this month, and the second
    date will be at 00:00 in the first day in the following month, as we are measuring historic
    data a month back and forward to todays date its not
    an issue that the we have a future end date.

    Both dates include the time zone name, or `Z` in case of UTC.
    Including these will allow the API to handle DST correctly.

    When asking for measurements, the `from` datetime is inclusive
    and the `to` datetime is exclusive.
    """
    from_dt = datetime.now().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    to_dt = (from_dt + timedelta(days=31)).replace(day=1)
    return (from_dt.isoformat() + " " + TIME_ZONE, to_dt.isoformat() + " " + TIME_ZONE)


class NgenicEnergyThisMonthSensor(NgenicSensor):
    """Representation of an Ngenic Energy Sensor (this month)."""

    device_class = SensorDeviceClass.ENERGY

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
            timedelta(minutes=20),
            measurement_type,
            device_info,
        )

    @property
    def unit_of_measurement(self):
        """Return the unit of measurement."""
        return UnitOfEnergy.KILO_WATT_HOUR

    @property
    def name(self):
        """Return the name of the sensor."""
        return f"{self._name} monthly {self._measurement_type.name.replace('_', ' ')}".title()

    @property
    def unique_id(self) -> str:
        """Return a unique ID for the sensor."""
        return f"{self._node.uuid()}-{self._measurement_type.name}-sensor-month"

    async def _async_fetch_measurement(self, first_load: bool = False):
        """Ask for measurements for a duration.

        This requires some further inputs, so we'll override the _async_fetch_measurement method.
        """
        from_dt, to_dt = _get_from_to_datetime_month()
        # using datetime will return a list of measurements
        # we'll use the last item in that list
        # dont send any period so the response includes the whole timespan
        current = await get_measurement_value(
            self._node,
            measurement_type=self._measurement_type,
            from_dt=from_dt,
            to_dt=to_dt,
        )
        return round(current, 1)

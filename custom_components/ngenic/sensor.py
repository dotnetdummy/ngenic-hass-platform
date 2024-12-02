"""Sensor platform for Ngenic integration."""

from datetime import datetime, timedelta
import logging

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)
from homeassistant.const import UnitOfEnergy, UnitOfPower, UnitOfTemperature
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.event import async_track_time_interval
import homeassistant.util.dt as dt_util

from .const import BRAND, DATA_CLIENT, DOMAIN
from .ngenicpy.models.measurement import MeasurementType
from .ngenicpy.models.node import Node, NodeType
from .ngenicpy.models.node_status import NodeStatus

_LOGGER = logging.getLogger(__name__)

TIME_ZONE = (
    "Z" if str(dt_util.DEFAULT_TIME_ZONE) == "UTC" else str(dt_util.DEFAULT_TIME_ZONE)
)


def get_from_to_datetime_month():
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


def get_from_to_datetime_last_month():
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


def get_from_to_datetime(days=1):
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


async def get_measurement_value(node, **kwargs):
    """Get measurement.

    This is a wrapper around the measurement API to gather
    parsing and error handling in a single place.
    """
    measurement = await node.async_measurement(**kwargs)
    if not measurement:
        # measurement API will return None if no measurements were found for the period
        _LOGGER.info(
            "Measurement not found for period, this is expected when data have not been gathered for the period (type=%(measurement_type)s, from=%(from_dt)s, to=%(to_dt)s)",
            kwargs.get("measurement_type", "unknown"),
            kwargs.get("from_dt", "None"),
            kwargs.get("to_dt", "None"),
        )
        measurement_val = 0
    elif isinstance(measurement, list):
        # using datetime will return a list of measurements
        # we'll use the last item in that list
        measurement_val = measurement[-1]["value"]
    else:
        measurement_val = measurement["value"]

    return measurement_val


async def async_setup_entry(hass: HomeAssistant, _, async_add_entities):
    """Set up the sensor platform."""
    ngenic = hass.data[DOMAIN][DATA_CLIENT]

    devices = []

    for tune in await ngenic.async_tunes():
        rooms = await tune.async_rooms()

        for node in await tune.async_nodes():
            node_name = f"Ngenic {node.get_type().name.lower()}"

            if node.get_type() == NodeType.SENSOR:
                # If this sensor is connected to a room
                # we'll use the room name as the sensor name
                for room in rooms:
                    if room["nodeUuid"] == node.uuid():
                        node_name = f"{node_name} {room["name"]}"

            device_info = DeviceInfo(
                identifiers={(DOMAIN, node.uuid())},
                manufacturer=BRAND,
                model=node.get_type().name.capitalize(),
                name=node_name,
            )
            measurement_types = await node.async_measurement_types()
            if MeasurementType.TEMPERATURE in measurement_types:
                devices.append(
                    NgenicTempSensor(
                        hass,
                        ngenic,
                        node,
                        node_name,
                        timedelta(minutes=5),
                        MeasurementType.TEMPERATURE,
                        device_info,
                    )
                )
                devices.append(
                    NgenicBatterySensor(
                        hass,
                        ngenic,
                        node,
                        node_name,
                        timedelta(minutes=5),
                        "BATTERY",
                        device_info,
                    )
                )
                devices.append(
                    NgenicSignalSensor(
                        hass,
                        ngenic,
                        node,
                        node_name,
                        timedelta(minutes=5),
                        "SIGNAL",
                        device_info,
                    )
                )

            if MeasurementType.CONTROL_VALUE in measurement_types:
                # append "control" so it doesn't collide with control temperature
                # this will become "Ngenic controller control temperature"
                node_name = f"{node_name} control"
                devices.append(
                    NgenicTempSensor(
                        hass,
                        ngenic,
                        node,
                        node_name,
                        timedelta(minutes=5),
                        MeasurementType.CONTROL_VALUE,
                        device_info,
                    )
                )

            if MeasurementType.HUMIDITY in measurement_types:
                devices.append(
                    NgenicHumiditySensor(
                        hass,
                        ngenic,
                        node,
                        node_name,
                        timedelta(minutes=5),
                        MeasurementType.HUMIDITY,
                        device_info,
                    )
                )

            if MeasurementType.POWER_KW in measurement_types:
                devices.append(
                    NgenicPowerSensor(
                        hass,
                        ngenic,
                        node,
                        node_name,
                        timedelta(minutes=1),
                        MeasurementType.POWER_KW,
                        device_info,
                    )
                )

            if MeasurementType.ENERGY_KWH in measurement_types:
                devices.append(
                    NgenicEnergySensor(
                        hass,
                        ngenic,
                        node,
                        node_name,
                        timedelta(minutes=10),
                        MeasurementType.ENERGY_KWH,
                        device_info,
                    )
                )
                devices.append(
                    NgenicEnergySensorMonth(
                        hass,
                        ngenic,
                        node,
                        node_name,
                        timedelta(minutes=20),
                        MeasurementType.ENERGY_KWH,
                        device_info,
                    )
                )
                devices.append(
                    NgenicEnergySensorLastMonth(
                        hass,
                        ngenic,
                        node,
                        node_name,
                        timedelta(minutes=60),
                        MeasurementType.ENERGY_KWH,
                        device_info,
                    )
                )

    for device in devices:
        # Initial update (will not update hass state)
        await device.async_update()

        # Setup update timer
        device.setup_updater()

    # Add entities to hass (and trigger a state update)
    async_add_entities(devices, update_before_add=True)


class NgenicSensor(SensorEntity):
    """Representation of an Ngenic Sensor."""

    def __init__(
        self,
        hass: HomeAssistant,
        ngenic,
        node,
        name,
        update_interval,
        measurement_type,
        device_info,
    ) -> None:
        """Initialize the sensor."""

        self._hass = hass
        self._state = None
        self._available = False
        self._ngenic = ngenic
        self._name = name
        self._node = node
        self._update_interval = update_interval
        self._measurement_type = measurement_type
        self._updater = None
        self._attr_device_info = device_info

    @property
    def name(self):
        """Return the name of the sensor."""
        return f"{self._name} {self.device_class}"

    @property
    def available(self):
        """Return if the sensor is available."""
        return self._available

    @property
    def state(self):
        """Return the state of the sensor."""
        return self._state

    @property
    def unique_id(self):
        """Return a unique ID for the sensor."""
        part = (
            self._measurement_type.name
            if isinstance(self._measurement_type, MeasurementType)
            else self._measurement_type
        )
        return f"{self._node.uuid()}-{part}-sensor"

    @property
    def should_poll(self):
        """An update is pushed when device is updated."""
        return False

    async def async_will_remove_from_hass(self):
        """Remove updater when sensor is removed."""
        if self._updater:
            self._updater()
            self._updater = None

    def setup_updater(self):
        """Configure a timer that will execute an update every update interval."""
        # async_track_time_interval returns a function that, when executed, will remove the timer
        self._updater = async_track_time_interval(
            self._hass, self.async_update, self._update_interval
        )

    async def _async_fetch_measurement(self):
        """Fetch the measurement data from ngenic API.

        Return measurement formatted as intended to be displayed in hass.
        Concrete classes should override this function if they
        fetch or format the measurement differently.
        """
        current = await get_measurement_value(
            self._node, measurement_type=self._measurement_type
        )
        return round(current, 1)

    async def async_update(self, event_time=None):
        """Fetch new state data for the sensor.

        This is the only method that should fetch new data for Home Assistant.
        """
        _LOGGER.debug(
            "Fetch measurement (name=%(name)s, type=%(measurement_type)s)",
            self._name,
            self._measurement_type,
        )
        try:
            new_state = await self._async_fetch_measurement()
            self._available = True
        except Exception:
            # Don't throw an exception if a sensor fails to update.
            # Instead, make the sensor unavailable.
            _LOGGER.exception("Failed to update sensor '%(unique_id)s'", self.unique_id)
            self._available = False
            return

        if self._state != new_state:
            self._state = new_state
            _LOGGER.debug(
                "New measurement: %(state)f (name=%(name)s, type=%(measurement_type)s)",
                new_state,
                self._name,
                self._measurement_type,
            )

            # self.hass is loaded once the entity have been setup.
            # Since this method is executed before adding the entity
            # the hass object might not have been loaded yet.
            if self.hass:
                # Tell hass that an update is available
                self.schedule_update_ha_state()
        else:
            _LOGGER.debug(
                "No new measurement: %(state)f (name=%(name)s, type=%(measurement_type)s)",
                self._state,
                self._name,
                self._measurement_type,
            )


class NgenicTempSensor(NgenicSensor):
    """Representation of an Ngenic Temperature Sensor."""

    device_class = SensorDeviceClass.TEMPERATURE
    state_class = SensorStateClass.MEASUREMENT

    @property
    def unit_of_measurement(self):
        """Return the unit of measurement."""
        return UnitOfTemperature.CELSIUS


class NgenicHumiditySensor(NgenicSensor):
    """Representation of an Ngenic Humidity Sensor."""

    device_class = SensorDeviceClass.HUMIDITY
    state_class = SensorStateClass.MEASUREMENT

    @property
    def unit_of_measurement(self):
        """Return the unit of measurement."""
        return "%"


class NgenicBatterySensor(NgenicSensor):
    """Representation of an Ngenic Battery Sensor."""

    device_class = SensorDeviceClass.BATTERY
    state_class = SensorStateClass.MEASUREMENT

    @property
    def unit_of_measurement(self):
        """Return the unit of measurement."""
        return "%"

    async def _async_fetch_measurement(self):
        if isinstance(self._node, Node):
            status = await self._node.async_status()

        if isinstance(status, NodeStatus):
            current = status.battery_percentage()
        else:
            _LOGGER.debug("Assume battery is full if we can't get the status")
            current = 100

        return round(current, 1)


class NgenicSignalSensor(NgenicSensor):
    """Representation of an Ngenic Signal Sensor."""

    device_class = SensorDeviceClass.SIGNAL_STRENGTH
    state_class = SensorStateClass.MEASUREMENT

    @property
    def unit_of_measurement(self):
        """Return the unit of measurement."""
        return "%"

    async def _async_fetch_measurement(self):
        if isinstance(self._node, Node):
            status = await self._node.async_status()

        if isinstance(status, NodeStatus):
            current = status.radio_signal_percentage()
        else:
            _LOGGER.debug("Assume signal is full if we can't get the status")
            current = 100

        return round(current, 1)


class NgenicPowerSensor(NgenicSensor):
    """Representation of an Ngenic Power Sensor."""

    device_class = SensorDeviceClass.POWER
    state_class = SensorStateClass.MEASUREMENT

    @property
    def unit_of_measurement(self):
        """Return the unit of measurement."""
        return UnitOfPower.WATT

    async def _async_fetch_measurement(self):
        """Fetch new power state data for the sensor.

        The NGenic API returns a float with kW but HA huses W so we need to multiply by 1000
        """
        current = await get_measurement_value(
            self._node, measurement_type=self._measurement_type
        )
        return round(current * 1000.0, 1)


class NgenicEnergySensor(NgenicSensor):
    """Representation of an Ngenic Energy Sensor."""

    device_class = SensorDeviceClass.ENERGY
    state_class = SensorStateClass.TOTAL_INCREASING

    @property
    def unit_of_measurement(self):
        """Return the unit of measurement."""
        return UnitOfEnergy.KILO_WATT_HOUR

    async def _async_fetch_measurement(self):
        """Ask for measurements for a duration.

        This requires some further inputs, so we'll override the _async_fetch_measurement method.
        """
        from_dt, to_dt = get_from_to_datetime()
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


class NgenicEnergySensorMonth(NgenicSensor):
    """Representation of an Ngenic Energy Sensor (monthly)."""

    device_class = SensorDeviceClass.ENERGY

    @property
    def unit_of_measurement(self):
        """Return the unit of measurement."""
        return UnitOfEnergy.KILO_WATT_HOUR

    async def _async_fetch_measurement(self):
        """Ask for measurements for a duration.

        This requires some further inputs, so we'll override the _async_fetch_measurement method.
        """
        from_dt, to_dt = get_from_to_datetime_month()
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

    @property
    def name(self):
        """Return the name of the sensor."""
        return f"{self._name} monthly energy"

    @property
    def unique_id(self):
        """Return a unique ID for the sensor."""
        return f"{self._node.uuid()}-{self._measurement_type.name}-sensor-month"


class NgenicEnergySensorLastMonth(NgenicSensor):
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
        from_dt, to_dt = get_from_to_datetime_last_month()
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
        return f"{self._name} last month energy"

    @property
    def unique_id(self):
        """Return a unique ID for the sensor."""
        return f"{self._node.uuid()}-{self._measurement_type.name}-sensor-last-month"

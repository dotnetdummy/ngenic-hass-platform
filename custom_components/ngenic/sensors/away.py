"""Ngenic Away Sensors."""

from datetime import timedelta
import logging

from homeassistant.components.sensor import SensorDeviceClass, SensorStateClass
from homeassistant.core import HomeAssistant
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.helpers.entity import DeviceInfo, slugify

from ..const import BRAND, DOMAIN, UPDATE_SCHEDULE_TOPIC  # noqa: TID252
from ..ngenicpy import AsyncNgenic  # noqa: TID252
from ..ngenicpy.models.tune import Tune  # noqa: TID252
from .base import SlimNgenicSensor

_LOGGER = logging.getLogger(__name__)


class NgenicBaseAwaySensor(SlimNgenicSensor):
    """Base representation of a Ngenic Away Sensor."""

    def __init__(
        self,
        hass: HomeAssistant,
        ngenic: AsyncNgenic,
        update_interval: timedelta,
        tune: Tune,
        name: str,
    ) -> None:
        """Initialize the sensor."""

        device_info_name = f"Ngenic Tune {tune["tuneName"]}"

        super().__init__(
            hass,
            ngenic,
            slugify(f"{tune.uuid()} {name} sensor"),
            f"{device_info_name} {name}",
            update_interval,
            DeviceInfo(
                identifiers={(DOMAIN, f"tune_{tune["tuneUuid"]}")},
                manufacturer=BRAND,
                name=device_info_name,
                model="Tune",
            ),
        )

        self._tune = tune

    async def async_added_to_hass(self) -> None:
        """Register callbacks."""
        _LOGGER.debug("Registering callbacks for %s", self.unique_id)
        self.async_on_remove(
            async_dispatcher_connect(
                self.hass, UPDATE_SCHEDULE_TOPIC, self._force_update
            )
        )


class NgenicAwayModeSensor(NgenicBaseAwaySensor):
    """Representation of a Ngenic Away Mode Sensor."""

    device_class = SensorDeviceClass.ENUM
    state_class = SensorStateClass.MEASUREMENT
    _attr_icon = "mdi:home-off"

    def __init__(
        self,
        hass: HomeAssistant,
        ngenic: AsyncNgenic,
        update_interval: timedelta,
        tune: Tune,
    ) -> None:
        """Initialize the sensor."""

        super().__init__(hass, ngenic, update_interval, tune, "Away mode")

    async def _async_fetch_measurement(self, first_load: bool = False):
        if isinstance(self._tune, Tune):
            schedule = await self._tune.async_setpoint_schedule(not first_load)
            return "Active" if schedule.active() else "Inactive"
        return None


class NgenicAwayScheduledFromSensor(NgenicBaseAwaySensor):
    """Representation of a Ngenic AwayScheduled From Sensor."""

    device_class = SensorDeviceClass.TIMESTAMP
    state_class = SensorStateClass.MEASUREMENT

    def __init__(
        self,
        hass: HomeAssistant,
        ngenic: AsyncNgenic,
        update_interval: timedelta,
        tune: Tune,
    ) -> None:
        """Initialize the sensor."""

        super().__init__(hass, ngenic, update_interval, tune, "Away scheduled from")

    async def _async_fetch_measurement(self, first_load: bool = False):
        val: str | None = None
        if isinstance(self._tune, Tune):
            schedule = await self._tune.async_setpoint_schedule(not first_load)
            try:
                val = schedule.start_time().isoformat()
            except:  # noqa: E722
                val = None
        return val


class NgenicAwayScheduledToSensor(NgenicBaseAwaySensor):
    """Representation of a Ngenic Away Scheduled To Sensor."""

    device_class = SensorDeviceClass.TIMESTAMP
    state_class = SensorStateClass.MEASUREMENT

    def __init__(
        self,
        hass: HomeAssistant,
        ngenic: AsyncNgenic,
        update_interval: timedelta,
        tune: Tune,
    ) -> None:
        """Initialize the sensor."""

        super().__init__(hass, ngenic, update_interval, tune, "Away scheduled to")

    async def _async_fetch_measurement(self, first_load: bool = False):
        val: str | None = None
        if isinstance(self._tune, Tune):
            schedule = await self._tune.async_setpoint_schedule(not first_load)
            try:
                val = schedule.end_time().isoformat()
            except:  # noqa: E722
                val = None
        return val

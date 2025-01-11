"""Switch for Ngenic integration."""

import logging

from homeassistant.components.switch import SwitchDeviceClass, SwitchEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.dispatcher import (
    async_dispatcher_connect,
    async_dispatcher_send,
)
from homeassistant.helpers.entity import Callable, DeviceInfo, HomeAssistant
from homeassistant.util import slugify

from .const import BRAND, DATA_CLIENT, DOMAIN, UPDATE_SCHEDULE_TOPIC
from .ngenicpy import AsyncNgenic
from .ngenicpy.models.setpoint_schedule import SetpointSchedule
from .ngenicpy.models.tune import Tune

_LOGGER = logging.getLogger(__package__)


async def async_setup_entry(
    hass: HomeAssistant, _: ConfigEntry, async_add_entities: Callable[[list], None]
) -> None:
    """Seting up Ngenic switches."""

    ngenic: AsyncNgenic = hass.data[DOMAIN][DATA_CLIENT]
    devices = [NgenicAwayModeSwitch(tune) for tune in await ngenic.async_tunes()]

    for device in devices:
        # Initial update (will not update hass state)
        await device.async_update(True)

    # Add entities to hass (and trigger a state update)
    async_add_entities(devices, update_before_add=True)


class NgenicAwayModeSwitch(SwitchEntity):
    """Representation of a Ngenic away mode switch."""

    def __init__(self, tune: Tune) -> None:
        """Initialize the switch."""

        device_info_name = f"Ngenic Tune {tune["tuneName"]}"

        self._attr_name = f"{device_info_name} Away toggle"
        self._attr_unique_id = slugify(f"{tune.uuid()} {self._attr_name}")
        self._attr_icon = "mdi:home-off"
        self._attr_is_on = False
        self._attr_should_poll = False
        self._attr_device_class = SwitchDeviceClass.SWITCH
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, f"tune_{tune["tuneUuid"]}")},
            manufacturer=BRAND,
            name=device_info_name,
            model="Tune",
        )
        self._tune = tune
        self._schedule: SetpointSchedule = None
        _LOGGER.debug("Init done for %s", self.unique_id)

    async def _toggle_away(self, active: bool) -> None:
        """Toggle away mode."""
        if active:
            self._schedule.activate_away()
        else:
            self._schedule.deactivate_away()
        await self._schedule.async_update()
        async_dispatcher_send(self.hass, UPDATE_SCHEDULE_TOPIC)

    async def async_turn_on(self):
        """Turn the switch on."""
        await self._toggle_away(True)

    async def async_turn_off(self):
        """Turn the switch off."""
        await self._toggle_away(False)

    async def async_added_to_hass(self) -> None:
        """Register callbacks."""
        _LOGGER.debug("Registering callbacks for %s", self.unique_id)
        self.async_on_remove(
            async_dispatcher_connect(
                self.hass, UPDATE_SCHEDULE_TOPIC, self.async_update
            )
        )

    async def async_update(self, first_load: bool = False) -> None:
        """Fetch new state data for the switch."""

        try:
            self._schedule = await self._tune.async_setpoint_schedule(not first_load)
        except Exception:
            # Don't throw an exception if a sensor fails to update.
            _LOGGER.exception("Failed to update (switch=%s)", self.unique_id)
            return

        if self._attr_is_on != self._schedule.active():
            self._attr_is_on = self._schedule.active()
            _LOGGER.debug(
                "New state: %s (switch=%s)",
                self._attr_is_on,
                self.unique_id,
            )

            if self.hass:
                # Tell hass that an update is available
                self.schedule_update_ha_state()
        else:
            _LOGGER.debug(
                "No new state: %s (switch=%s)",
                self._attr_is_on,
                self.unique_id,
            )

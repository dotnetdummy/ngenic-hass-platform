"""Switch for Ngenic integration."""

import logging
from typing import List, Optional, Any # Added List, Optional, Any

from ngenicpy import AsyncNgenic
try:
    from ngenicpy.models.setpoint_schedule import SetpointSchedule
except ImportError:
    logging.getLogger(__name__).warning("ngenicpy.models.setpoint_schedule.SetpointSchedule not found, using Any type instead.")
    SetpointSchedule = Any # type: ignore
try:
    from ngenicpy.models.tune import Tune
except ImportError:
    logging.getLogger(__name__).warning("ngenicpy.models.tune.Tune not found, using Any type instead.")
    Tune = Any # type: ignore

from homeassistant.components.switch import SwitchDeviceClass, SwitchEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.dispatcher import (
    async_dispatcher_connect,
    async_dispatcher_send,
)
from homeassistant.helpers.entity import DeviceInfo # Removed HomeAssistant, Callable as not directly used in signatures here
from homeassistant.helpers.entity_platform import AddEntitiesCallback # Added AddEntitiesCallback
from homeassistant.core import HomeAssistant # Added HomeAssistant for hass type hint
from homeassistant.util import slugify

from .const import (
    BRAND,
    DATA_CLIENT,
    DOMAIN,
    SETPONT_SCHEDULE_NAME, # Note: Typo in constant name (SETPONT vs SETPOINT)
    UPDATE_SCHEDULE_TOPIC,
)

_LOGGER = logging.getLogger(__name__) # Changed from __package__ to __name__ for standard practice


async def async_setup_entry(
    hass: HomeAssistant, 
    config_entry: ConfigEntry, # Added config_entry type, named unused param
    async_add_entities: AddEntitiesCallback
) -> None: # Typed signature
    """Setting up Ngenic switches."""

    ngenic: AsyncNgenic = hass.data[DOMAIN][DATA_CLIENT]
    # Assuming ngenic.async_tunes() returns List[Tune] or List[Any] if import failed
    tune_list: List[Tune] = await ngenic.async_tunes() # type: ignore[assignment]
    
    devices: List[NgenicAwayModeSwitch] = [
        NgenicAwayModeSwitch(tune_item) for tune_item in tune_list # type: ignore[arg-type] # tune_item can be Any
    ]

    for device in devices:
        # Initial update (will not update hass state)
        await device.async_update(True) # Pass first_load=True

    # Add entities to hass (and trigger a state update)
    async_add_entities(devices, update_before_add=True)


class NgenicAwayModeSwitch(SwitchEntity):
    """Representation of a Ngenic away mode switch."""

    def __init__(self, tune: Tune) -> None: # Typed tune and return
        """Initialize the switch."""

        # Assuming tune is a Tune object or Any (if import failed)
        # Dictionary access like tune['tuneName'] suggests it might be a dict or supports __getitem__
        # If Tune is a class, prefer tune.tune_name() or tune.name attribute if available.
        # For now, using type: ignore for these accesses.
        device_info_name: str = f"Ngenic Tune {tune['tuneName']}" # type: ignore[index]

        self._attr_name: str = f"{device_info_name} Away toggle"
        self._attr_unique_id: str = slugify(f"{tune.uuid()} {self._attr_name}") # type: ignore[union-attr]
        self._attr_icon: str = "mdi:home-off"
        # _attr_is_on is set in async_update
        self._attr_should_poll: bool = False # Switches that update via dispatcher should not poll
        self._attr_device_class: SwitchDeviceClass = SwitchDeviceClass.SWITCH
        self._attr_device_info: DeviceInfo = DeviceInfo(
            identifiers={(DOMAIN, f"tune_{tune['tuneUuid']}")}, # type: ignore[index]
            manufacturer=BRAND,
            name=device_info_name,
            model="Tune",
        )
        self._tune: Tune = tune
        self._schedule: Optional[SetpointSchedule] = None # Typed and initialized to None
        _LOGGER.debug("Init done for %s", self.unique_id)

    async def _toggle_away(self, active: bool) -> None:
        """Toggle away mode."""
        if self._schedule is None:
            _LOGGER.warning("Schedule not loaded for %s, cannot toggle away mode", self.unique_id)
            return
        
        if active:
            self._schedule.activate_away() # type: ignore[union-attr] # _schedule can be Any
        else:
            self._schedule.deactivate_away() # type: ignore[union-attr] # _schedule can be Any
        await self._schedule.async_update() # type: ignore[union-attr]
        async_dispatcher_send(self.hass, UPDATE_SCHEDULE_TOPIC)

    async def async_turn_on(self, **kwargs: Any) -> None: # Added **kwargs and return type
        """Turn the switch on."""
        await self._toggle_away(True)

    async def async_turn_off(self, **kwargs: Any) -> None: # Added **kwargs and return type
        """Turn the switch off."""
        await self._toggle_away(False)

    async def async_added_to_hass(self) -> None:
        """Register callbacks."""
        _LOGGER.debug("Registering callbacks for %s", self.unique_id)
        self.async_on_remove(
            async_dispatcher_connect(
                self.hass, UPDATE_SCHEDULE_TOPIC, self.async_update # type: ignore[arg-type] # async_update has first_load
            )
        )

    async def async_update(self, first_load: bool = False) -> None: # Added first_load default
        """Fetch new state data for the switch."""
        _LOGGER.debug("Updating state for %s (first_load=%s)", self.unique_id, first_load)
        try:
            # Assuming self._tune is Tune or Any
            self._schedule = await self._tune.async_setpoint_schedule( # type: ignore[union-attr]
                SETPONT_SCHEDULE_NAME, not first_load # type: ignore[arg-type] # if _tune is Any
            )
        except Exception:
            # Don't throw an exception if a sensor fails to update.
            _LOGGER.exception("Failed to update schedule data for switch %s", self.unique_id)
            # Consider setting self._attr_available = False here if appropriate
            return

        if self._schedule is None:
            _LOGGER.warning("No schedule data loaded for %s", self.unique_id)
            # Consider setting self._attr_available = False here
            return

        current_is_on_state = self._schedule.active() # type: ignore[union-attr] # _schedule can be Any
        if self._attr_is_on != current_is_on_state:
            self._attr_is_on = current_is_on_state
            _LOGGER.debug(
                "New state: %s (switch=%s)",
                self._attr_is_on,
                self.unique_id,
            )

            if self.hass: # Check if hass is available (it should be post added_to_hass)
                # Tell hass that an update is available
                self.async_write_ha_state() # Use async_write_ha_state for modern HA
        else:
            _LOGGER.debug(
                "No new state: %s (switch=%s)",
                self._attr_is_on,
                self.unique_id,
            )

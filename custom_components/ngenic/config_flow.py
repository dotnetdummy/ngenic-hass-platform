"""Config flow component for Ngenic integration."""

import logging
from typing import Any, Dict, Optional, Set # Added Dict, Optional, Set

from ngenicpy import AsyncNgenic
from ngenicpy.exceptions import ClientException
import voluptuous as vol

from homeassistant import config_entries
from homeassistant.const import CONF_TOKEN
from homeassistant.core import HomeAssistant, callback # callback is already here
# ConfigEntry is not directly used but good for context if needed later
# from homeassistant.config_entries import ConfigEntry 

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)


@callback
def configured_instances(hass: HomeAssistant) -> Set[str]: # Changed set to Set[str]
    """Return a set of configured Ngenic instances."""

    return {
        entry.data[CONF_TOKEN] for entry in hass.config_entries.async_entries(DOMAIN)
    }


@config_entries.HANDLERS.register(DOMAIN)
class FlowHandler(config_entries.ConfigFlow): # ConfigFlow is already the base
    """Handle a config flow for Ngenic integration."""

    VERSION = 1
    CONNECTION_CLASS = config_entries.CONN_CLASS_CLOUD_PUSH

    def _show_form(self, error: Optional[str] = None) -> Dict[str, Any]: # Typed signature
        """Show the form to the user."""
        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema({vol.Required(CONF_TOKEN): str}),
            errors={"base": error} if error is not None else {},
        )

    async def async_step_import(
        self, user_input: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]: # Typed signature (user_input changed from import_config)
        """Import a config entry from configuration.yaml."""
        # user_input here is expected to be the data part of a config entry,
        # typically Dict[str, Any]
        return await self.async_step_user(user_input)

    async def async_step_user(
        self, user_input: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]: # Typed signature
        """Handle the start of the config flow."""
        errors: Dict[str, str] = {} # Initialize errors dictionary

        if user_input is not None:
            token: Optional[str] = user_input.get(CONF_TOKEN)

            if not token:
                errors["base"] = "missing_token" # Or some other error code
                return self.async_show_form(
                    step_id="user",
                    data_schema=vol.Schema({vol.Required(CONF_TOKEN): str}),
                    errors=errors,
                )

            try:
                if token in configured_instances(self.hass):
                    return self._show_form("already_configured")

                ngenic = AsyncNgenic(token=token) # Use validated token

                tune_name: Optional[str] = None
                # Assuming async_tunes returns a list of dict-like objects
                # that have a "tuneName" key.
                tunes_data = await ngenic.async_tunes()
                if tunes_data: # Check if list is not empty
                    # Try to get tuneName from the first tune, assuming it exists
                    # This part might need more robust handling if tune structure varies
                    first_tune = tunes_data[0]
                    if isinstance(first_tune, dict) and "tuneName" in first_tune:
                         tune_name = first_tune["tuneName"]
                    elif hasattr(first_tune, "name"): # If it's an object with a name attribute
                         tune_name = first_tune.name() # Or first_tune.name if it's a property

                if tune_name is None: # If no tunes or no name found
                    # Keep previous behavior, but show_form now takes error string
                    return self._show_form("no_tunes")


                await self.async_set_unique_id(token) # Set unique_id to prevent re-configuration
                self._abort_if_unique_id_configured()

                return self.async_create_entry(title=tune_name, data=user_input)

            except ClientException:
                # Show form with bad_token error
                return self._show_form("bad_token")
            except Exception as e: # Catch other potential errors during API call
                _LOGGER.exception("Unexpected exception in Ngenic config flow: %s", e)
                errors["base"] = "unknown_error" # Generic error for unknown issues
                return self.async_show_form(
                    step_id="user",
                    data_schema=vol.Schema({vol.Required(CONF_TOKEN): str}),
                    errors=errors,
                )
        
        # Show the initial form or re-show form if no user_input (e.g. initial step)
        return self._show_form()

"""Config flow component for Ngenic integration."""

import logging
from typing import Any

from ngenicpy import AsyncNgenic
from ngenicpy.exceptions import ClientException
import voluptuous as vol

from homeassistant import config_entries
from homeassistant.const import CONF_TOKEN
from homeassistant.core import HomeAssistant, callback

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)


@callback
def configured_instances(hass: HomeAssistant) -> set:
    """Return a set of configured Ngenic instances."""

    return {
        entry.data[CONF_TOKEN] for entry in hass.config_entries.async_entries(DOMAIN)
    }


@config_entries.HANDLERS.register(DOMAIN)
class FlowHandler(config_entries.ConfigFlow):
    """Handle a config flow for Ngenic integration."""

    VERSION = 1
    CONNECTION_CLASS = config_entries.CONN_CLASS_CLOUD_PUSH

    def _show_form(self, error: str | None = None):
        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema({vol.Required(CONF_TOKEN): str}),
            errors={"base": error} if error is not None else {},
        )

    async def async_step_import(self, import_config: dict[str, str]):
        """Import a config entry from configuration.yaml."""
        return await self.async_step_user(import_config)

    async def async_step_user(self, user_input: dict[str, Any] | None = None):
        """Handle the start of the config flow."""

        if user_input is not None:
            try:
                if user_input[CONF_TOKEN] in configured_instances(self.hass):
                    return self._show_form("already_configured")

                ngenic = AsyncNgenic(token=user_input[CONF_TOKEN])

                tune_name = None

                for tune in await ngenic.async_tunes():
                    tune_name = tune["tuneName"]

                if tune_name is None:
                    return self._show_form("no_tunes")

                return self.async_create_entry(title=tune_name, data=user_input)

            except ClientException:
                return self._show_form("bad_token")

        return self._show_form()

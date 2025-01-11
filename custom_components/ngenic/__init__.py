"""Support for Ngenic Tune."""

import voluptuous as vol

from homeassistant.config_entries import SOURCE_IMPORT, ConfigEntry
from homeassistant.const import CONF_TOKEN, Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers import config_validation as cv

from .config_flow import configured_instances
from .const import DATA_CLIENT, DATA_CONFIG, DOMAIN, SERVICE_SET_ACTIVE_CONTROL
from .ngenicpy import AsyncNgenic
from .services import async_register_services

CONFIG_SCHEMA = vol.Schema(
    {
        DOMAIN: vol.Schema(
            {
                vol.Required(CONF_TOKEN): cv.string,
            }
        )
    },
    extra=vol.ALLOW_EXTRA,
)

NGENIC_PLATFORMS = [Platform.CLIMATE, Platform.SENSOR, Platform.SWITCH]


async def async_setup(hass: HomeAssistant, config: dict):
    """Init and configuration of the Ngenic component."""
    hass.data[DOMAIN] = {}
    hass.data[DOMAIN][DATA_CLIENT] = {}

    if DOMAIN not in config:
        return True

    conf = config[DOMAIN]

    # Store config for use during entry setup
    hass.data[DOMAIN][DATA_CONFIG] = conf

    # Check if already configured
    if conf[CONF_TOKEN] in configured_instances(hass):
        return True

    # Create a config flow
    hass.async_create_task(
        hass.config_entries.flow.async_init(
            DOMAIN,
            context={"source": SOURCE_IMPORT},
            data={CONF_TOKEN: conf[CONF_TOKEN]},
        )
    )

    return True


async def async_setup_entry(hass: HomeAssistant, config_entry: ConfigEntry):
    """Init and configuration of the Ngenic component."""

    hass.data[DOMAIN][DATA_CLIENT] = AsyncNgenic(token=config_entry.data[CONF_TOKEN])

    # Register Ngenic services
    async_register_services(hass)

    await hass.config_entries.async_forward_entry_setups(config_entry, NGENIC_PLATFORMS)

    return True


async def async_unload_entry(hass: HomeAssistant, config_entry: ConfigEntry):
    """Unload of the Ngenic component."""

    await hass.config_entries.async_unload_platforms(config_entry, NGENIC_PLATFORMS)
    await hass.data[DOMAIN][DATA_CLIENT].async_close()

    # Remove Ngenic services
    hass.services.async_remove(DOMAIN, SERVICE_SET_ACTIVE_CONTROL)

    return True

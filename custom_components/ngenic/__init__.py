"""Support for Ngenic Tune."""

from typing import Dict, Any # Added Dict, Any
from ngenicpy import AsyncNgenic
import voluptuous as vol

from homeassistant.config_entries import SOURCE_IMPORT, ConfigEntry
from homeassistant.const import CONF_TOKEN, Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.typing import ConfigType # Added ConfigType

from .config_flow import configured_instances
from .const import DATA_CLIENT, DATA_CONFIG, DOMAIN, SERVICE_SET_ACTIVE_CONTROL
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

NGENIC_PLATFORMS: List[Platform] = [Platform.CLIMATE, Platform.SENSOR, Platform.SWITCH] # Typed NGENIC_PLATFORMS


async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool: # Typed signature
    """Init and configuration of the Ngenic component."""
    # Initialize domain data structure
    domain_data: Dict[str, Any] = {
        DATA_CLIENT: {}, # Will store AsyncNgenic instances per config entry
        DATA_CONFIG: {}, # Stores initial config from YAML if provided
    }
    hass.data[DOMAIN] = domain_data

    if DOMAIN not in config:
        return True

    conf: Dict[str, Any] = config[DOMAIN] # Type conf

    # Store config for use during entry setup (primarily for import flow)
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


async def async_setup_entry(hass: HomeAssistant, config_entry: ConfigEntry) -> bool: # Typed signature
    """Init and configuration of the Ngenic component."""

    # Ensure DATA_CLIENT exists, though it should have been set up by async_setup
    if DATA_CLIENT not in hass.data[DOMAIN]:
        hass.data[DOMAIN][DATA_CLIENT] = {}

    # Store the AsyncNgenic client instance, keyed by config_entry.entry_id for clarity
    # or directly if only one instance is expected per domain.
    # The original code overwrites, implying one main client instance.
    client = AsyncNgenic(token=config_entry.data[CONF_TOKEN])
    hass.data[DOMAIN][DATA_CLIENT] = client # Storing AsyncNgenic instance

    # Register Ngenic services
    async_register_services(hass)

    await hass.config_entries.async_forward_entry_setups(config_entry, NGENIC_PLATFORMS)

    return True


async def async_unload_entry(hass: HomeAssistant, config_entry: ConfigEntry) -> bool: # Typed signature
    """Unload of the Ngenic component."""

    # Retrieve the client instance to close it.
    # Assuming DATA_CLIENT holds the main AsyncNgenic instance as per async_setup_entry.
    client: Optional[AsyncNgenic] = hass.data[DOMAIN].get(DATA_CLIENT) # type: ignore[assignment]
    
    unload_ok = await hass.config_entries.async_unload_platforms(config_entry, NGENIC_PLATFORMS)

    if client:
        await client.async_close()

    if unload_ok:
        # Potentially remove client from hass.data if it was stored per entry_id
        # If it's a single shared client, it's already closed.
        # hass.data[DOMAIN][DATA_CLIENT].pop(config_entry.entry_id, None)
        # For now, assuming DATA_CLIENT holds one main instance as per current setup.
        pass


    # Remove Ngenic services
    hass.services.async_remove(DOMAIN, SERVICE_SET_ACTIVE_CONTROL)

    return unload_ok

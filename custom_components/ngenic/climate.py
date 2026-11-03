"""Climate platform for Ngenic Tune."""

from datetime import timedelta
import logging

from ngenicpy import AsyncNgenic
from ngenicpy.models.measurement import MeasurementType
from ngenicpy.models.tune import Tune

from homeassistant.components.climate import (
    DOMAIN as CLIMATE_DOMAIN,
    ClimateEntity,
    ClimateEntityFeature,
    HVACMode,
)
from homeassistant.const import ATTR_TEMPERATURE, UnitOfTemperature
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers import device_registry as dr, entity_registry as er
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import BRAND, DATA_CLIENT, DOMAIN

_LOGGER = logging.getLogger(__name__)

# Tune system Nodes report data in intervals of five minutes
SCAN_INTERVAL = timedelta(minutes=5)


async def async_setup_entry(
    hass: HomeAssistant, _, async_add_entities: AddEntitiesCallback
):
    """Set up the climate platform."""

    ngenic: AsyncNgenic = hass.data[DOMAIN][DATA_CLIENT]

    devices = []

    for tmp_tune in await ngenic.async_tunes():
        # listing tunes contain less information than when querying a single tune
        tune = await ngenic.async_tune(tmp_tune.uuid())

        if not _get_control_room_uuid(tune):
            _LOGGER.warning("No control room found for Tune '%s'", tune["name"])
            continue

        device = NgenicTune(ngenic, tune)

        _async_migrate_unique_id(hass, tune.uuid(), device.unique_id)

        # Initial update
        await device.async_update()

        devices.append(device)

    async_add_entities(devices)


def _get_control_room_uuid(tune: Tune) -> str | None:
    """Return the uuid of the room that is used as input to the Tune control system.

    The room can be found either directly on the tune, or by looking at the activeControl property on the room
    object. if roomToControlUuid is set, it takes precedence and the activeControl attribute will not be used
    """
    if tune["roomToControlUuid"]:
        return tune["roomToControlUuid"]
    return next(
        (room["uuid"] for room in tune["rooms"] if room["activeControl"] is True),
        None,
    )


@callback
def _async_migrate_unique_id(hass: HomeAssistant, tune_uuid: str, unique_id: str):
    """Move climate entities of a Tune to a unique id that doesn't depend on the control room.

    Older versions used the control room node uuid, which changes whenever the control room
    or its sensor changes, and Home Assistant would then create a new entity with a new entity id.
    The oldest climate entity on the Tune device is kept so the original entity id is restored,
    and duplicates created by earlier unique id changes are removed.
    """
    ent_reg = er.async_get(hass)
    if ent_reg.async_get_entity_id(CLIMATE_DOMAIN, DOMAIN, unique_id):
        return

    device = dr.async_get(hass).async_get_device(
        identifiers={(DOMAIN, f"tune_{tune_uuid}")}
    )
    if device is None:
        return

    entries = [
        entry
        for entry in er.async_entries_for_device(
            ent_reg, device.id, include_disabled_entities=True
        )
        if entry.domain == CLIMATE_DOMAIN and entry.platform == DOMAIN
    ]
    if not entries:
        return

    entries.sort(key=lambda entry: entry.created_at)
    keep, *duplicates = entries
    for entry in duplicates:
        _LOGGER.info("Removing duplicate climate entity %s", entry.entity_id)
        ent_reg.async_remove(entry.entity_id)

    _LOGGER.info(
        "Migrating %s unique id from %s to %s",
        keep.entity_id,
        keep.unique_id,
        unique_id,
    )
    ent_reg.async_update_entity(keep.entity_id, new_unique_id=unique_id)


class NgenicTune(ClimateEntity):
    """Representation of an Ngenic Thermostat."""

    def __init__(self, ngenic: AsyncNgenic, tune: Tune) -> None:
        """Initialize the thermostat."""
        self._available = False
        self._ngenic = ngenic
        self._name = f"Ngenic Tune {tune['name']}"
        self._tune = tune
        self._room = None
        self._current_temperature = None
        self._target_temperature = None
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, f"tune_{self._tune.uuid()}")},
            manufacturer=BRAND,
            name=self._name,
            model="Tune",
        )

    @property
    def supported_features(self):
        """Return the list of supported features."""
        return ClimateEntityFeature.TARGET_TEMPERATURE

    @property
    def name(self):
        """Return the name of the Tune."""
        return self._name

    @property
    def available(self):
        """Return if the Tune is available."""
        return self._available

    @property
    def unique_id(self):
        """Return a unique ID for this Tune."""
        return f"{self._tune.uuid()}-climate"

    @property
    def native_temperature_unit(self):
        """Return the unit of measurement which this thermostat uses."""
        return UnitOfTemperature.CELSIUS

    @property
    def native_current_temperature(self):
        """Return the current temperature."""
        return self._current_temperature

    @property
    def native_target_temperature(self):
        """Return the temperature we try to reach."""
        return self._target_temperature

    @property
    def hvac_mode(self):
        """Must be implemented."""
        return HVACMode.HEAT

    @property
    def hvac_modes(self):
        """Must be implemented."""
        return [HVACMode.HEAT]

    async def async_set_temperature(self, **kwargs):
        """Set new target temperature."""
        temperature = kwargs.get(ATTR_TEMPERATURE)
        if temperature is None:
            return

        # fetch the room again so we don't overwrite changes made since the last update
        room = await self._tune.async_room(self._room.uuid(), invalidate_cache=True)
        room["targetTemperature"] = temperature
        await room.async_update()
        self._room = room
        self._target_temperature = temperature

    async def async_update(self):
        """Fetch new state data from the sensor.

        This is the only method that should fetch new data for Home Assistant.
        """
        try:
            # fetch the tune on each update since the control room can be changed in the Ngenic app
            tune = await self._ngenic.async_tune(
                self._tune.uuid(), invalidate_cache=True
            )
            control_room_uuid = _get_control_room_uuid(tune)
            if not control_room_uuid:
                _LOGGER.warning("No control room found for '%s'", self.unique_id)
                self._available = False
                return
            target_room = await tune.async_room(control_room_uuid)
            node = await tune.async_node(target_room["nodeUuid"])
            current = await node.async_measurement(MeasurementType.TEMPERATURE)
            self._tune = tune
            self._room = target_room
            self._available = True
        except Exception:
            # Don't throw an exception if a sensor fails to update.
            # Instead, make the sensor unavailable.
            _LOGGER.exception("Failed to update climate '%s'", self.unique_id)
            self._available = False
            return

        try:
            self._current_temperature = round(current["value"], 1)
            self._target_temperature = round(target_room["targetTemperature"], 1)
        except (AttributeError, KeyError, TypeError):
            # A successful call can still come back without the field we
            # need (a data gap upstream). NgenicBase.__getitem__ raises
            # AttributeError for a missing key, not KeyError or None, and
            # round() would TypeError on a None value -- handle any of
            # these the same as a fetch failure instead of crashing.
            _LOGGER.warning(
                "Ngenic returned incomplete data for '%s'; marking unavailable",
                self.unique_id,
            )
            self._available = False
            return

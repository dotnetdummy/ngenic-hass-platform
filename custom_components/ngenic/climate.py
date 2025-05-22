"""Climate platform for Ngenic Tune."""

from datetime import timedelta
import logging
from typing import List, Optional, Any, Callable # Added List, Optional, Any, Callable

from ngenicpy import AsyncNgenic
# Assuming ngenicpy.models.room.Room and ngenicpy.models.node.Node exist
# If not, these will need to be Any or a more generic type from ngenicpy
try:
    from ngenicpy.models.room import Room
except ImportError:
    _LOGGER.warning("ngenicpy.models.room.Room not found, using Any type instead.")
    Room = Any # type: ignore
try:
    from ngenicpy.models.node import Node
except ImportError:
    _LOGGER.warning("ngenicpy.models.node.Node not found, using Any type instead.")
    Node = Any # type: ignore
from ngenicpy.models.measurement import MeasurementType
from ngenicpy.models.tune import Tune

from homeassistant.components.climate import (
    ClimateEntity,
    ClimateEntityFeature,
    HVACMode,
)
from homeassistant.const import ATTR_TEMPERATURE, UnitOfTemperature
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.event import async_track_time_interval

from .const import BRAND, DATA_CLIENT, DOMAIN
from .models import RoomTypedDict, MeasurementTypedDict # Added .models imports

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant, _, async_add_entities: AddEntitiesCallback
) -> None: # Added return type
    """Set up the climate platform."""

    ngenic: AsyncNgenic = hass.data[DOMAIN][DATA_CLIENT]

    devices: List[NgenicTune] = [] # Typed devices list

    tmp_tunes: List[Tune] = await ngenic.async_tunes() # Typed tmp_tunes
    for tmp_tune in tmp_tunes:
        # listing tunes contain less information than when querying a single tune
        tune: Tune = await ngenic.async_tune(tmp_tune.uuid())

        # rooms with control sensors can be found either directly on the tune, or by looking at the activeControl
        # property on the room object. if roomToControlUuid is set, it takes precedence and the activeControl
        # attribute will not be used
        control_room_uuids: List[str] = []
        # Assuming tune object (Tune class instance) supports __getitem__
        if tune["roomToControlUuid"]: # type: ignore
            control_room_uuids.append(tune["roomToControlUuid"]) # type: ignore
        else:
            # Assuming tune["rooms"] returns List[RoomTypedDict] or similar
            # and that RoomTypedDict contains "activeControl" and "uuid"
            room_list_from_tune: List[RoomTypedDict] = tune["rooms"] # type: ignore
            for room_data: RoomTypedDict in room_list_from_tune:
                if room_data["activeControl"] is True:
                    control_room_uuids.append(room_data["uuid"])

        for control_room_uuid in control_room_uuids:
            # get the room whose sensor data and target temperature should be used as inputs to the Tune control system
            # Assuming tune.async_room returns a Room object from ngenicpy.models
            control_room: Room = await tune.async_room(control_room_uuid)

            # get the room node
            # Assuming control_room (Room object) supports __getitem__ for "nodeUuid"
            # Assuming tune.async_node returns a Node object from ngenicpy.models
            control_node: Node = await tune.async_node(control_room["nodeUuid"]) # type: ignore

            device: NgenicTune = NgenicTune(hass, ngenic, tune, control_room, control_node)

            # Initial update
            await device.async_update()

            # Setup update timer
            device.setup_updater()

            devices.append(device)

    async_add_entities(devices)


class NgenicTune(ClimateEntity):
    """Representation of an Ngenic Thermostat."""

    def __init__(
        self,
        hass: HomeAssistant,
        ngenic: AsyncNgenic,
        tune: Tune,
        control_room: Room, # Typed control_room
        control_node: Node, # Typed control_node
    ) -> None:
        """Initialize the thermostat."""
        self._hass: HomeAssistant = hass
        self._available: bool = False
        self._ngenic: AsyncNgenic = ngenic
        # Assuming tune object (Tune class instance) supports __getitem__ for "name"
        self._name: str = f"Ngenic Tune {tune['name']}" # type: ignore
        self._tune: Tune = tune
        self._room: Room = control_room
        self._node: Node = control_node
        self._current_temperature: Optional[float] = None
        self._target_temperature: Optional[float] = None
        self._updater: Optional[Callable[[], None]] = None # Typed updater
        # Assuming self._tune.uuid() is valid
        self._attr_unique_id: str = f"{self._node.uuid()}-climate" # Set directly
        self._attr_name: str = self._name # Set directly
        self._attr_temperature_unit: str = UnitOfTemperature.CELSIUS
        self._attr_supported_features: ClimateEntityFeature = ClimateEntityFeature.TARGET_TEMPERATURE
        self._attr_hvac_modes: List[HVACMode] = [HVACMode.HEAT]
        self._attr_hvac_mode: HVACMode = HVACMode.HEAT
        self._attr_device_info: DeviceInfo = DeviceInfo(
            identifiers={(DOMAIN, f"tune_{self._tune.uuid()}")}, # type: ignore
            manufacturer=BRAND,
            name=self._name,
            model="Tune",
        )

    @property
    def supported_features(self) -> ClimateEntityFeature: # Added return type
        """Return the list of supported features."""
        return self._attr_supported_features

    @property
    def name(self) -> str: # Added return type
        """Return the name of the Tune."""
        return self._attr_name

    @property
    def available(self) -> bool: # Added return type
        """Return if the Tune is available."""
        return self._available

    @property
    def unique_id(self) -> str: # Added return type
        """Return a unique ID for this Tune."""
        return self._attr_unique_id

    @property
    def temperature_unit(self) -> str: # Added return type
        """Return the unit of measurement which this thermostat uses."""
        return self._attr_temperature_unit

    @property
    def current_temperature(self) -> Optional[float]: # Added return type
        """Return the current temperature."""
        return self._current_temperature

    @property
    def target_temperature(self) -> Optional[float]: # Added return type
        """Return the temperature we try to reach."""
        return self._target_temperature

    @property
    def hvac_mode(self) -> HVACMode: # Added return type
        """Return the current HVAC mode."""
        return self._attr_hvac_mode

    @property
    def hvac_modes(self) -> List[HVACMode]: # Added return type
        """Return the list of available HVAC modes."""
        return self._attr_hvac_modes

    async def async_will_remove_from_hass(self) -> None: # Added return type
        """Remove updater when sensor is removed."""
        if self._updater:
            self._updater()
            self._updater = None

    def setup_updater(self) -> None: # Added return type
        """Configure a timer that will execute an update every update interval."""
        # async_track_time_interval returns a function that, when executed, will remove the timer
        self._updater = async_track_time_interval(
            self._hass, self.async_update, timedelta(minutes=5)
        )

    async def async_set_temperature(self, **kwargs: Any) -> None: # Typed kwargs, added return type
        """Set new target temperature."""
        temperature: Optional[float] = kwargs.get(ATTR_TEMPERATURE)
        if temperature is None:
            return

        # Assuming self._room (Room object) supports __setitem__ for "targetTemperature"
        # and its async_update method
        self._room["targetTemperature"] = temperature # type: ignore
        await self._room.async_update() # type: ignore
        self._target_temperature = temperature

    async def async_update(self, event_time: Optional[Any] = None) -> None: # Typed event_time, added return type
        """Fetch new state data from the sensor.

        This is the only method that should fetch new data for Home Assistant.
        """
        try:
            # Assuming self._node.async_measurement returns MeasurementTypedDict
            current: MeasurementTypedDict = await self._node.async_measurement(MeasurementType.TEMPERATURE) # type: ignore
            # Assuming self._tune.async_room returns RoomTypedDict here
            target_room: RoomTypedDict = await self._tune.async_room(self._room.uuid()) # type: ignore
            self._available = True
        except Exception:
            # Don't throw an exception if a sensor fails to update.
            # Instead, make the sensor unavailable.
            _LOGGER.exception("Failed to update climate '%s'", self.unique_id)
            self._available = False
            return

        self._current_temperature = round(current["value"], 1)
        self._target_temperature = round(target_room["targetTemperature"], 1)

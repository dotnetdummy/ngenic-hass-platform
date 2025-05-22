"""Sensor platform for Ngenic integration."""

import asyncio
from dataclasses import dataclass, field # Added dataclass and field
from datetime import timedelta
import logging # Added logging for import fallbacks
from typing import List, Optional, Any, Type # Added typing imports, including Type

from ngenicpy import AsyncNgenic
from ngenicpy.models.measurement import MeasurementType
from ngenicpy.models.node import NodeType

# Graceful imports for ngenicpy models
try:
    from ngenicpy.models.tune import Tune
except ImportError:
    logging.getLogger(__name__).warning("ngenicpy.models.tune.Tune not found, using Any type instead.")
    Tune = Any # type: ignore
try:
    from ngenicpy.models.room import Room
except ImportError:
    logging.getLogger(__name__).warning("ngenicpy.models.room.Room not found, using Any type instead.")
    Room = Any # type: ignore
try:
    from ngenicpy.models.node import Node
except ImportError:
    logging.getLogger(__name__).warning("ngenicpy.models.node.Node not found, using Any type instead.")
    Node = Any # type: ignore

from homeassistant.config_entries import ConfigEntry # Added ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.event import async_call_later

from .const import BRAND, DATA_CLIENT, DOMAIN
# RoomTypedDict is imported as per task, but might not be used if Room class instances are used.
from .models import RoomTypedDict # Imported RoomTypedDict
from .sensors.away import (
    NgenicAwayModeSensor,
    NgenicAwayScheduledFromSensor,
    NgenicAwayScheduledToSensor,
)
from .sensors.base import NgenicSensor # Base sensor class for type hinting
from .sensors.battery import NgenicBatterySensor
from .sensors.current import NgenicCurrentSensor
from .sensors.energy import NgenicEnergySensor
from .sensors.energy_last_month import NgenicEnergyLastMonthSensor
from .sensors.energy_this_month import NgenicEnergyThisMonthSensor
from .sensors.humidity import NgenicHumiditySensor
from .sensors.power import NgenicPowerSensor
from .sensors.signal_strength import NgenicSignalStrengthSensor
from .sensors.temperature import NgenicTemperatureSensor
from .sensors.voltage import NgenicVoltageSensor

_LOGGER = logging.getLogger(__name__) # Logger for general use

@dataclass
class SensorConfig:
    """Configuration for creating a sensor entity."""
    measurement_type: MeasurementType
    main_sensor_class: Type[NgenicSensor]
    name_suffix: Optional[str] = None
    associated_sensor_classes: List[Type[NgenicSensor]] = field(default_factory=list)
    has_energy_variants: bool = False

# Sensor configuration mapping
# This list will be iterated to create sensors based on available MeasurementTypes
SENSOR_CONFIG_MAP: List[SensorConfig] = [
    SensorConfig(
        measurement_type=MeasurementType.TEMPERATURE,
        main_sensor_class=NgenicTemperatureSensor,
        associated_sensor_classes=[NgenicBatterySensor, NgenicSignalStrengthSensor],
    ),
    SensorConfig(
        measurement_type=MeasurementType.CONTROL_VALUE,
        main_sensor_class=NgenicTemperatureSensor,
        name_suffix=" control",
    ),
    SensorConfig(
        measurement_type=MeasurementType.HUMIDITY,
        main_sensor_class=NgenicHumiditySensor,
    ),
    SensorConfig(
        measurement_type=MeasurementType.POWER,
        main_sensor_class=NgenicPowerSensor,
    ),
    SensorConfig(
        measurement_type=MeasurementType.PRODUCED_POWER,
        main_sensor_class=NgenicPowerSensor,
    ),
    SensorConfig(
        measurement_type=MeasurementType.L1_CURRENT,
        main_sensor_class=NgenicCurrentSensor,
    ),
    SensorConfig(
        measurement_type=MeasurementType.L2_CURRENT,
        main_sensor_class=NgenicCurrentSensor,
    ),
    SensorConfig(
        measurement_type=MeasurementType.L3_CURRENT,
        main_sensor_class=NgenicCurrentSensor,
    ),
    SensorConfig(
        measurement_type=MeasurementType.L1_VOLTAGE,
        main_sensor_class=NgenicVoltageSensor,
    ),
    SensorConfig(
        measurement_type=MeasurementType.L2_VOLTAGE,
        main_sensor_class=NgenicVoltageSensor,
    ),
    SensorConfig(
        measurement_type=MeasurementType.L3_VOLTAGE,
        main_sensor_class=NgenicVoltageSensor,
    ),
    SensorConfig(
        measurement_type=MeasurementType.ENERGY,
        main_sensor_class=NgenicEnergySensor,
        has_energy_variants=True,
    ),
    SensorConfig(
        measurement_type=MeasurementType.PRODUCED_ENERGY,
        main_sensor_class=NgenicEnergySensor,
        has_energy_variants=True,
    ),
]

async def async_setup_entry(
    hass: HomeAssistant, config_entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None: # Typed arguments and return
    """Set up the sensor platform."""

    ngenic: AsyncNgenic = hass.data[DOMAIN][DATA_CLIENT]
    entities: List[NgenicSensor] = []

    tune_list: List[Tune] = await ngenic.async_tunes()
    for tune_item: Tune in tune_list:
        rooms: List[Room] = await tune_item.async_rooms()

        # Create tune-specific sensors (Away mode)
        entities.extend([
            NgenicAwayModeSensor(hass, ngenic, timedelta(minutes=5), tune_item),
            NgenicAwayScheduledFromSensor(hass, ngenic, timedelta(minutes=5), tune_item),
            NgenicAwayScheduledToSensor(hass, ngenic, timedelta(minutes=5), tune_item),
        ])

        nodes_in_tune: List[Node] = await tune_item.async_nodes()
        for node_item: Node in nodes_in_tune:
            initial_node_name: str = f"Ngenic {node_item.get_type().name}".title() # type: ignore
            node_room: Optional[Room] = None
            initial_device_model: str = node_item.get_type().name.capitalize() # type: ignore

            if node_item.get_type() == NodeType.SENSOR: # type: ignore
                for room_instance: Room in rooms:
                    if room_instance["nodeUuid"] == node_item.uuid(): # type: ignore
                        initial_node_name = f"{initial_node_name} {room_instance['name']}" # type: ignore
                        node_room = room_instance
                        break
            
            measurement_types: List[MeasurementType] = await node_item.async_measurement_types() # type: ignore

            # Determine current_node_name and current_device_model based on track logic
            # This name/model will be used for the DeviceInfo and default sensor names
            current_node_name = initial_node_name
            current_device_model = initial_device_model
            if (MeasurementType.ENERGY in measurement_types or
                MeasurementType.POWER in measurement_types or
                MeasurementType.PRODUCED_ENERGY in measurement_types): # Added PRODUCED_ENERGY for Track naming
                current_node_name = "Ngenic Track"
                current_device_model = "Track"

            device_info = DeviceInfo(
                identifiers={(DOMAIN, str(node_item.uuid()))}, # type: ignore
                manufacturer=BRAND,
                model=current_device_model,
                name=current_node_name,
            )

            for config in SENSOR_CONFIG_MAP:
                if config.measurement_type in measurement_types:
                    sensor_name = current_node_name # Default name for the sensor
                    if config.name_suffix:
                        sensor_name += config.name_suffix
                    
                    # Instantiate the main sensor
                    entities.append(config.main_sensor_class(
                        hass,
                        ngenic,
                        node_room,
                        node_item,
                        sensor_name, # Use potentially suffixed name
                        config.measurement_type,
                        device_info,
                    ))

                    # Instantiate associated sensors
                    # These use the `current_node_name` (which could be "Ngenic Track")
                    # and don't take measurement_type in their constructor.
                    for associated_class in config.associated_sensor_classes:
                        entities.append(associated_class(
                            hass,
                            ngenic,
                            node_room,
                            node_item,
                            current_node_name, # Use non-suffixed name for associated sensors
                            device_info,
                        ))

                    # Instantiate energy variants if applicable
                    if config.has_energy_variants:
                        # These use the `sensor_name` (which is `current_node_name` here as energy sensors don't have suffix)
                        # and take measurement_type in their constructor.
                        entities.append(NgenicEnergyThisMonthSensor(
                            hass,
                            ngenic,
                            node_room,
                            node_item,
                            sensor_name, # Name is same as main energy sensor
                            config.measurement_type,
                            device_info,
                        ))
                        entities.append(NgenicEnergyLastMonthSensor(
                            hass,
                            ngenic,
                            node_room,
                            node_item,
                            sensor_name, # Name is same as main energy sensor
                            config.measurement_type,
                            device_info,
                        ))

    async_add_entities(entities)

    for entity_item in entities:
        if entity_item.should_update_on_startup:
            # Update the device state at startup
            await entity_item.async_update()
            await asyncio.sleep(0.3) # Consider if this sleep is essential or can be removed/adjusted
        else:
            # Otherwise wait 1 minute before updating the device state
            # This is to ensure the Ngenic API not responds with "429 Too Many Requests" error
            async_call_later(
                hass,
                timedelta(minutes=1),
                entity_item.async_update, # type: ignore # async_update might not be recognized on NgenicSensor base without stubs
            )

        # Setup update timer
        entity_item.setup_updater() # type: ignore # setup_updater might not be recognized on NgenicSensor base

"""Sensor platform for Ngenic integration."""

import asyncio
from datetime import timedelta

from ngenicpy import AsyncNgenic
from ngenicpy.models.measurement import MeasurementType
from ngenicpy.models.node import NodeType
from ngenicpy.models.room import Room

from homeassistant.components.sensor import DOMAIN as SENSOR_DOMAIN
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers import device_registry as dr, entity_registry as er
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.event import async_call_later

from .const import BRAND, DATA_CLIENT, DOMAIN
from .sensors.away import (
    NgenicAwayModeSensor,
    NgenicAwayScheduledFromSensor,
    NgenicAwayScheduledToSensor,
)
from .sensors.base import NgenicSensor
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


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
):
    """Set up the sensor platform."""

    ngenic: AsyncNgenic = hass.data[DOMAIN][DATA_CLIENT]
    devices: list[NgenicSensor] = []

    for tune in await ngenic.async_tunes():
        rooms = await tune.async_rooms()

        devices.append(
            NgenicAwayModeSensor(
                hass,
                ngenic,
                timedelta(minutes=5),
                tune,
            )
        )
        devices.append(
            NgenicAwayScheduledFromSensor(
                hass,
                ngenic,
                timedelta(minutes=5),
                tune,
            )
        )
        devices.append(
            NgenicAwayScheduledToSensor(
                hass,
                ngenic,
                timedelta(minutes=5),
                tune,
            )
        )

        for node in await tune.async_nodes():
            node_name = f"Ngenic {node.get_type().name}".title()
            node_room: Room = None
            device_model = node.get_type().name.capitalize()

            if node.get_type() == NodeType.SENSOR:
                # If this sensor is connected to a room
                # we'll use the room name as the sensor name
                for room in rooms:
                    if room["nodeUuid"] == node.uuid():
                        node_name = f"{node_name} {room['name']}"
                        node_room = room
                        break

            measurement_types = await node.async_measurement_types()

            # if measurement_types contains ENERGY or POWER then the node_name should be Ngenic Track
            if (
                MeasurementType.ENERGY in measurement_types
                or MeasurementType.POWER in measurement_types
            ):
                node_name = "Ngenic Track"
                device_model = "Track"

            device_info = DeviceInfo(
                identifiers={(DOMAIN, node.uuid())},
                manufacturer=BRAND,
                model=device_model,
                name=node_name,
            )

            if MeasurementType.TEMPERATURE in measurement_types:
                devices.append(
                    NgenicTemperatureSensor(
                        hass,
                        ngenic,
                        node_room,
                        node,
                        node_name,
                        MeasurementType.TEMPERATURE,
                        device_info,
                    )
                )
                devices.append(
                    NgenicBatterySensor(
                        hass,
                        ngenic,
                        node_room,
                        node,
                        node_name,
                        device_info,
                    )
                )
                devices.append(
                    NgenicSignalStrengthSensor(
                        hass,
                        ngenic,
                        node_room,
                        node,
                        node_name,
                        device_info,
                    )
                )

            if node.get_type() != NodeType.CONTROLLER:
                _async_remove_control_value_sensor(hass, config_entry, node.uuid())
            elif MeasurementType.CONTROL_VALUE in measurement_types:
                # only the controller has data for the control value, even though
                # other nodes (like the gateway) may list it as a measurement type
                # append "control" so it doesn't collide with control temperature
                # this will become "Ngenic controller control temperature"
                node_name = f"{node_name} control"
                devices.append(
                    NgenicTemperatureSensor(
                        hass,
                        ngenic,
                        node_room,
                        node,
                        node_name,
                        MeasurementType.CONTROL_VALUE,
                        device_info,
                    )
                )

            if MeasurementType.HUMIDITY in measurement_types:
                devices.append(
                    NgenicHumiditySensor(
                        hass,
                        ngenic,
                        node_room,
                        node,
                        node_name,
                        MeasurementType.HUMIDITY,
                        device_info,
                    )
                )

            if MeasurementType.POWER in measurement_types:
                devices.append(
                    NgenicPowerSensor(
                        hass,
                        ngenic,
                        node_room,
                        node,
                        node_name,
                        MeasurementType.POWER,
                        device_info,
                    )
                )

            if MeasurementType.PRODUCED_POWER in measurement_types:
                devices.append(
                    NgenicPowerSensor(
                        hass,
                        ngenic,
                        node_room,
                        node,
                        node_name,
                        MeasurementType.PRODUCED_POWER,
                        device_info,
                    )
                )

            if MeasurementType.L1_CURRENT in measurement_types:
                devices.append(
                    NgenicCurrentSensor(
                        hass,
                        ngenic,
                        node_room,
                        node,
                        node_name,
                        MeasurementType.L1_CURRENT,
                        device_info,
                    )
                )

            if MeasurementType.L1_VOLTAGE in measurement_types:
                devices.append(
                    NgenicVoltageSensor(
                        hass,
                        ngenic,
                        node_room,
                        node,
                        node_name,
                        MeasurementType.L1_VOLTAGE,
                        device_info,
                    )
                )

            if MeasurementType.L2_CURRENT in measurement_types:
                devices.append(
                    NgenicCurrentSensor(
                        hass,
                        ngenic,
                        node_room,
                        node,
                        node_name,
                        MeasurementType.L2_CURRENT,
                        device_info,
                    )
                )

            if MeasurementType.L2_VOLTAGE in measurement_types:
                devices.append(
                    NgenicVoltageSensor(
                        hass,
                        ngenic,
                        node_room,
                        node,
                        node_name,
                        MeasurementType.L2_VOLTAGE,
                        device_info,
                    )
                )

            if MeasurementType.L3_CURRENT in measurement_types:
                devices.append(
                    NgenicCurrentSensor(
                        hass,
                        ngenic,
                        node_room,
                        node,
                        node_name,
                        MeasurementType.L3_CURRENT,
                        device_info,
                    )
                )

            if MeasurementType.L3_VOLTAGE in measurement_types:
                devices.append(
                    NgenicVoltageSensor(
                        hass,
                        ngenic,
                        node_room,
                        node,
                        node_name,
                        MeasurementType.L3_VOLTAGE,
                        device_info,
                    )
                )

            if MeasurementType.PRODUCED_ENERGY in measurement_types:
                devices.append(
                    NgenicEnergySensor(
                        hass,
                        ngenic,
                        node_room,
                        node,
                        node_name,
                        MeasurementType.PRODUCED_ENERGY,
                        device_info,
                    )
                )
                devices.append(
                    NgenicEnergyThisMonthSensor(
                        hass,
                        ngenic,
                        node_room,
                        node,
                        node_name,
                        MeasurementType.PRODUCED_ENERGY,
                        device_info,
                    )
                )
                devices.append(
                    NgenicEnergyLastMonthSensor(
                        hass,
                        ngenic,
                        node_room,
                        node,
                        node_name,
                        MeasurementType.PRODUCED_ENERGY,
                        device_info,
                    )
                )

            if MeasurementType.ENERGY in measurement_types:
                devices.append(
                    NgenicEnergySensor(
                        hass,
                        ngenic,
                        node_room,
                        node,
                        node_name,
                        MeasurementType.ENERGY,
                        device_info,
                    )
                )
                devices.append(
                    NgenicEnergyThisMonthSensor(
                        hass,
                        ngenic,
                        node_room,
                        node,
                        node_name,
                        MeasurementType.ENERGY,
                        device_info,
                    )
                )
                devices.append(
                    NgenicEnergyLastMonthSensor(
                        hass,
                        ngenic,
                        node_room,
                        node,
                        node_name,
                        MeasurementType.ENERGY,
                        device_info,
                    )
                )

    # Add entities to hass
    async_add_entities(devices)

    for device in devices:
        if device.should_update_on_startup:
            # Update the device state at startup
            await device.async_update()
            await asyncio.sleep(0.3)
        else:
            # Otherwise wait 1 minute before updating the device state
            # This is to ensure the Ngenic API not responds with "429 Too Many Requests" error
            config_entry.async_on_unload(
                async_call_later(
                    hass,
                    timedelta(minutes=1),
                    device.async_update,
                )
            )

        # Setup update timer
        device.setup_updater()


@callback
def _async_remove_control_value_sensor(
    hass: HomeAssistant, config_entry: ConfigEntry, node_uuid: str
) -> None:
    """Remove control value sensors created for nodes other than the controller.

    Older versions created it for every node listing the measurement type, but only the
    controller has data for it. The device is removed as well if it has no entities left.
    """
    ent_reg = er.async_get(hass)
    entity_id = ent_reg.async_get_entity_id(
        SENSOR_DOMAIN,
        DOMAIN,
        f"{node_uuid}-{MeasurementType.CONTROL_VALUE.name}-sensor",
    )
    if entity_id is None:
        return

    device_id = ent_reg.async_get(entity_id).device_id
    ent_reg.async_remove(entity_id)

    if device_id and not er.async_entries_for_device(
        ent_reg, device_id, include_disabled_entities=True
    ):
        dr.async_get(hass).async_update_device(
            device_id, remove_config_entry_id=config_entry.entry_id
        )

"""Sensor platform for Ngenic integration."""

from datetime import timedelta

from ngenicpy import AsyncNgenic
from ngenicpy.models.measurement import MeasurementType
from ngenicpy.models.node import NodeType
from ngenicpy.models.room import Room

from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import BRAND, DATA_CLIENT, DOMAIN
from .sensors.away import (
    NgenicAwayModeSensor,
    NgenicAwayScheduledFromSensor,
    NgenicAwayScheduledToSensor,
)
from .sensors.battery import NgenicBatterySensor
from .sensors.energy import NgenicEnergySensor
from .sensors.energy_last_month import NgenicEnergyLastMonthSensor
from .sensors.energy_this_month import NgenicEnergyThisMonthSensor
from .sensors.humidity import NgenicHumiditySensor
from .sensors.power import NgenicPowerSensor
from .sensors.signal_strength import NgenicSignalStrengthSensor
from .sensors.temperature import NgenicTemperatureSensor


async def async_setup_entry(
    hass: HomeAssistant, _, async_add_entities: AddEntitiesCallback
):
    """Set up the sensor platform."""

    ngenic: AsyncNgenic = hass.data[DOMAIN][DATA_CLIENT]
    devices = []

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
            node_name = f"Ngenic {node.get_type().name.lower()}"
            node_room: Room = None

            if node.get_type() == NodeType.SENSOR:
                # If this sensor is connected to a room
                # we'll use the room name as the sensor name
                for room in rooms:
                    if room["nodeUuid"] == node.uuid():
                        node_name = f"{node_name} {room['name']}"
                        node_room = room
                        break

            device_info = DeviceInfo(
                identifiers={(DOMAIN, node.uuid())},
                manufacturer=BRAND,
                model=node.get_type().name.capitalize(),
                name=node_name,
            )

            measurement_types = await node.async_measurement_types()
            if MeasurementType.TEMPERATURE in measurement_types:
                devices.append(
                    NgenicTemperatureSensor(
                        hass,
                        ngenic,
                        node_room,
                        node,
                        node_name,
                        timedelta(minutes=5),
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
                        timedelta(minutes=5),
                        "BATTERY",
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
                        timedelta(minutes=5),
                        "SIGNAL",
                        device_info,
                    )
                )

            if MeasurementType.CONTROL_VALUE in measurement_types:
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
                        timedelta(minutes=5),
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
                        timedelta(minutes=5),
                        MeasurementType.HUMIDITY,
                        device_info,
                    )
                )

            if MeasurementType.POWER_KW in measurement_types:
                devices.append(
                    NgenicPowerSensor(
                        hass,
                        ngenic,
                        node_room,
                        node,
                        node_name,
                        timedelta(minutes=1),
                        MeasurementType.POWER_KW,
                        device_info,
                    )
                )

            if MeasurementType.ENERGY_KWH in measurement_types:
                devices.append(
                    NgenicEnergySensor(
                        hass,
                        ngenic,
                        node_room,
                        node,
                        node_name,
                        timedelta(minutes=10),
                        MeasurementType.ENERGY_KWH,
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
                        timedelta(minutes=20),
                        MeasurementType.ENERGY_KWH,
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
                        timedelta(minutes=60),
                        MeasurementType.ENERGY_KWH,
                        device_info,
                    )
                )

    for device in devices:
        # Initial update (will not update hass state)
        await device.async_update(True)

        # Setup update timer
        device.setup_updater()

    # Add entities to hass (and trigger a state update)
    async_add_entities(devices, update_before_add=True)

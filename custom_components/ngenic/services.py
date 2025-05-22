"""Set active control service for Ngenic integration."""

import logging # Added logging
from datetime import datetime
from typing import List, Any # Added List, Any

from ngenicpy import AsyncNgenic
# Assuming ngenicpy.models.tune.Tune.async_setpoint_schedule returns a specific Schedule object type
# For now, its methods like activate_away, set_schedule, async_update are used directly.
# If a Schedule class exists, it should be imported.
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

import voluptuous as vol

from homeassistant.core import HomeAssistant, ServiceCall # Added ServiceCall
import homeassistant.helpers.config_validation as cv
from homeassistant.helpers.dispatcher import async_dispatcher_send
from homeassistant.helpers.service import verify_domain_control
import homeassistant.util.dt as dt_util

from .const import (
    DATA_CLIENT,
    DOMAIN,
    SERVICE_ACTIVATE_AWAY,
    SERVICE_DEACTIVATE_AWAY,
    SERVICE_SET_ACTIVE_CONTROL,
    SERVICE_SET_AWAY_SCHEDULE,
    SETPONT_SCHEDULE_NAME, # Note: Typo in constant name (SETPONT vs SETPOINT)
    UPDATE_SCHEDULE_TOPIC,
)

_LOGGER = logging.getLogger(__name__) # Added logger


def async_register_services(hass: HomeAssistant) -> None: # Typed signature
    """Register services for Ngenic integration."""

    async def set_active_control(call: ServiceCall) -> None: # Typed signature
        """Set active control."""
        room_uuid: str = call.data["room_uuid"]
        active: bool = call.data.get("active", False)
        # Assuming hass.data[DOMAIN][DATA_CLIENT] is correctly populated with AsyncNgenic instance
        ngenic: AsyncNgenic = hass.data[DOMAIN][DATA_CLIENT]
        
        try:
            tune_list: List[Tune] = await ngenic.async_tunes() # type: ignore[assignment] # ngenic can be Any
            for tune_item: Tune in tune_list:
                rooms: List[Room] = await tune_item.async_rooms() # type: ignore[union-attr] # tune_item can be Any
                for room_item: Room in rooms:
                    if room_item.uuid() == room_uuid: # type: ignore[union-attr] # room_item can be Any
                        # Assuming Room object supports __setitem__ or has a specific method
                        room_item["activeControl"] = active # type: ignore[index, union-attr]
                        await room_item.async_update() # type: ignore[union-attr]
                        # Assuming only one room matches, or we update all that match
        except Exception as e:
            _LOGGER.error("Error setting active control for room %s: %s", room_uuid, e)

    async def set_away_schedule(call: ServiceCall) -> None: # Typed signature
        """Set away schedule."""
        start_time: datetime = call.data["start_time"]
        end_time: datetime = call.data["end_time"]
        # Ensure timezone awareness as per HA standards if not already handled by cv.datetime
        start_time_tz = dt_util.as_utc(start_time) if start_time.tzinfo is None else start_time
        end_time_tz = dt_util.as_utc(end_time) if end_time.tzinfo is None else end_time
        
        ngenic: AsyncNgenic = hass.data[DOMAIN][DATA_CLIENT]
        tune_list: List[Tune] = await ngenic.async_tunes() # type: ignore[assignment]
        for tune_item: Tune in tune_list:
            try:
                # Assuming async_setpoint_schedule exists and returns an object with expected methods
                schedule = await tune_item.async_setpoint_schedule(SETPONT_SCHEDULE_NAME) # type: ignore[union-attr]
                schedule.set_schedule(start_time_tz, end_time_tz)
                await schedule.async_update()
                # Revalidate cache
                await tune_item.async_setpoint_schedule(SETPONT_SCHEDULE_NAME, True) # type: ignore[union-attr]
                async_dispatcher_send(hass, UPDATE_SCHEDULE_TOPIC)
            except Exception as e:
                _LOGGER.error("Error setting away schedule for tune %s: %s", tune_item.uuid() if hasattr(tune_item, "uuid") else "unknown", e) # type: ignore[union-attr]


    async def activate_away(call: ServiceCall) -> None: # Typed signature
        """Activate away."""
        ngenic: AsyncNgenic = hass.data[DOMAIN][DATA_CLIENT]
        tune_list: List[Tune] = await ngenic.async_tunes() # type: ignore[assignment]
        for tune_item: Tune in tune_list:
            try:
                schedule = await tune_item.async_setpoint_schedule(SETPONT_SCHEDULE_NAME) # type: ignore[union-attr]
                schedule.activate_away()
                await schedule.async_update()
                await tune_item.async_setpoint_schedule(SETPONT_SCHEDULE_NAME, True) # type: ignore[union-attr]
                async_dispatcher_send(hass, UPDATE_SCHEDULE_TOPIC)
            except Exception as e:
                _LOGGER.error("Error activating away mode for tune %s: %s", tune_item.uuid() if hasattr(tune_item, "uuid") else "unknown", e) # type: ignore[union-attr]

    async def deactivate_away(call: ServiceCall) -> None: # Typed signature
        """Deactivate away."""
        ngenic: AsyncNgenic = hass.data[DOMAIN][DATA_CLIENT]
        tune_list: List[Tune] = await ngenic.async_tunes() # type: ignore[assignment]
        for tune_item: Tune in tune_list:
            try:
                schedule = await tune_item.async_setpoint_schedule(SETPONT_SCHEDULE_NAME) # type: ignore[union-attr]
                schedule.deactivate_away()
                await schedule.async_update()
                await tune_item.async_setpoint_schedule(SETPONT_SCHEDULE_NAME, True) # type: ignore[union-attr]
                # Dispatcher send should be inside the loop if tunes can have independent schedules
                # or outside if it's a general notification. Current code has it outside the try-catch.
            async_dispatcher_send(hass, UPDATE_SCHEDULE_TOPIC) # This was outside try in previous code.
        except Exception as e:
            _LOGGER.error("Error deactivating away mode: %s", e)


    # Register services

    if not hass.services.has_service(DOMAIN, SERVICE_SET_ACTIVE_CONTROL):
        hass.services.async_register(
            DOMAIN,
            SERVICE_SET_ACTIVE_CONTROL,
            verify_domain_control(hass, DOMAIN)(set_active_control),
            schema=vol.Schema(
                {
                    vol.Required("room_uuid"): cv.string,
                    vol.Required("active"): cv.boolean,
                }
            ),
        )

    if not hass.services.has_service(DOMAIN, SERVICE_SET_AWAY_SCHEDULE):
        hass.services.async_register(
            DOMAIN,
            SERVICE_SET_AWAY_SCHEDULE,
            verify_domain_control(hass, DOMAIN)(set_away_schedule),
            schema=vol.Schema(
                {
                    vol.Required("start_time"): cv.datetime,
                    vol.Required("end_time"): cv.datetime,
                }
            ),
        )

    if not hass.services.has_service(DOMAIN, SERVICE_ACTIVATE_AWAY):
        hass.services.async_register(
            DOMAIN,
            SERVICE_ACTIVATE_AWAY,
            verify_domain_control(hass, DOMAIN)(activate_away),
        )

    if not hass.services.has_service(DOMAIN, SERVICE_DEACTIVATE_AWAY):
        hass.services.async_register(
            DOMAIN,
            SERVICE_DEACTIVATE_AWAY,
            verify_domain_control(hass, DOMAIN)(deactivate_away),
        )

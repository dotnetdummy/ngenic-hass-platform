"""Set active control service for Ngenic integration."""

from datetime import datetime

from ngenicpy import AsyncNgenic
import voluptuous as vol

from homeassistant.core import HomeAssistant
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
    SETPONT_SCHEDULE_NAME,
    UPDATE_SCHEDULE_TOPIC,
)


def async_register_services(hass: HomeAssistant):
    """Register services for Ngenic integration."""

    async def set_active_control(service) -> None:
        """Set active control."""
        room_uuid = service.data["room_uuid"]
        active = service.data.get("active", False)
        ngenic: AsyncNgenic = hass.data[DOMAIN][DATA_CLIENT]
        for tune in await ngenic.async_tunes():
            rooms = await tune.async_rooms()
            for room in rooms:
                if room.uuid() == room_uuid:
                    room["activeControl"] = active
                    await room.async_update()

    async def set_away_schedule(service) -> None:
        """Set away schedule."""
        start_time: datetime = service.data["start_time"]
        end_time: datetime = service.data["end_time"]
        start_time_tz = start_time.replace(tzinfo=dt_util.DEFAULT_TIME_ZONE)
        end_time_tz = end_time.replace(tzinfo=dt_util.DEFAULT_TIME_ZONE)
        ngenic: AsyncNgenic = hass.data[DOMAIN][DATA_CLIENT]
        for tune in await ngenic.async_tunes():
            schedule = await tune.async_setpoint_schedule(SETPONT_SCHEDULE_NAME)
            schedule.set_schedule(start_time_tz, end_time_tz)
            await schedule.async_update()
            schedule = await tune.async_setpoint_schedule(
                SETPONT_SCHEDULE_NAME, True
            )  # revalidate cache
            async_dispatcher_send(hass, UPDATE_SCHEDULE_TOPIC)

    async def activate_away(service) -> None:
        """Activate away."""
        ngenic: AsyncNgenic = hass.data[DOMAIN][DATA_CLIENT]
        for tune in await ngenic.async_tunes():
            schedule = await tune.async_setpoint_schedule(SETPONT_SCHEDULE_NAME)
            schedule.activate_away()
            await schedule.async_update()
            schedule = await tune.async_setpoint_schedule(
                SETPONT_SCHEDULE_NAME, True
            )  # revalidate cache
            async_dispatcher_send(hass, UPDATE_SCHEDULE_TOPIC)

    async def deactivate_away(service) -> None:
        """Deactivate away."""
        ngenic: AsyncNgenic = hass.data[DOMAIN][DATA_CLIENT]
        for tune in await ngenic.async_tunes():
            schedule = await tune.async_setpoint_schedule(SETPONT_SCHEDULE_NAME)
            schedule.deactivate_away()
            await schedule.async_update()
            schedule = await tune.async_setpoint_schedule(
                SETPONT_SCHEDULE_NAME, True
            )  # revalidate cache
            async_dispatcher_send(hass, UPDATE_SCHEDULE_TOPIC)

    # Register services

    if not hass.services.has_service(DOMAIN, SERVICE_SET_ACTIVE_CONTROL):
        hass.services.async_register(
            DOMAIN,
            SERVICE_SET_ACTIVE_CONTROL,
            verify_domain_control(DOMAIN)(set_active_control),
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
            verify_domain_control(DOMAIN)(set_away_schedule),
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
            verify_domain_control(DOMAIN)(activate_away),
        )

    if not hass.services.has_service(DOMAIN, SERVICE_DEACTIVATE_AWAY):
        hass.services.async_register(
            DOMAIN,
            SERVICE_DEACTIVATE_AWAY,
            verify_domain_control(DOMAIN)(deactivate_away),
        )

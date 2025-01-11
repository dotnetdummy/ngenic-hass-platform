"""Tune model."""

from typing import Any

import httpx

from ..const import API_PATH, SETPONT_SCHEDULE_NAME  # noqa: TID252
from .base import NgenicBase
from .node import Node
from .room import Room
from .setpoint_schedule import SetpointSchedule


class Tune(NgenicBase):
    """Ngenic API Tune model."""

    def __init__(self, session: httpx.AsyncClient, json_data: dict[str, Any]) -> None:
        """Initialize the tune model."""
        super().__init__(session=session, json_data=json_data)

    def uuid(self) -> str:
        """Get the tune UUID."""

        # If a tune was fetched with the list API, it contains "tuneUuid"
        # If it was fetched directly (with UUID), it contains "uuid"
        try:
            return self["tuneUuid"]
        except AttributeError:
            return super().uuid()

    async def async_rooms(self) -> list[Room]:
        """List all Rooms associated with a Tune (async). A Room contains an indoor sensor.

        :return:
            a list of rooms
        :rtype:
            `list(~ngenic.models.room.Room)`
        """
        url = API_PATH["rooms"].format(tuneUuid=self.uuid(), roomUuid="")
        return await self._async_parse_new_instance(url, Room, tuneUuid=self.uuid())

    async def async_room(self, roomUuid: str) -> Room:
        """Get data about a Room (async). A Room contains an indoor sensor.

        :param str roomUuid:
            (required) room UUID
        :return:
            the room
        :rtype:
            `~ngenic.models.room.Room`
        """
        url = API_PATH["rooms"].format(tuneUuid=self.uuid(), roomUuid=roomUuid)
        return await self._async_parse_new_instance(url, Room, tuneUuid=self.uuid())

    async def async_nodes(self) -> list[Node]:
        """List all Nodes associated with a Tune (async). A Node is a logical network entity.

        :return:
            a list of nodes
        :rtype:
            `list(~ngenic.models.node.Node)`
        """
        url = API_PATH["nodes"].format(tuneUuid=self.uuid(), nodeUuid="")
        return await self._async_parse_new_instance(url, Node, tuneUuid=self.uuid())

    async def async_node(self, nodeUuid: str) -> Node:
        """Get data about a Node (async). A Node is a logical network entity.

        :param str nodeUuid:
            (required) node UUID
        :return:
            the node
        :rtype:
            `~ngenic.models.node.Node`
        """
        url = API_PATH["nodes"].format(tuneUuid=self.uuid(), nodeUuid=nodeUuid)
        return await self._async_parse_new_instance(url, Node, tuneUuid=self.uuid())

    async def async_setpoint_schedule(
        self, invalidate_cache: bool = False
    ) -> SetpointSchedule:
        """Fetch the setpoint schedule for Home Assistant.

        :param bool invalidate_cache:
            if the cache should be invalidated or not (default: False)
        :return:
            the setpoint schedule
        :rtype:
            `~ngenic.models.setpoint_schedule.SetPointSchedule`
        """

        url = API_PATH["setpoint_schedules"].format(tuneUuid=self.uuid())
        rsp_json = self._parse(await self._async_get(url, invalidate_cache))

        for obj in rsp_json:
            if obj["name"] == SETPONT_SCHEDULE_NAME:
                return self._new_instance(SetpointSchedule, obj, tuneUuid=self.uuid())

        new_json = {
            "name": SETPONT_SCHEDULE_NAME,
            "autoTune": True,
            "lowestSetpoint": 12,
        }
        return self._new_instance(SetpointSchedule, new_json, tuneUuid=self.uuid())

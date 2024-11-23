import json
from .base import NgenicBase
from ..const import API_PATH

class Room(NgenicBase):
    def __init__(self, session, json, tune):
        self._parentTune = tune

        super(Room, self).__init__(session=session, json=json)

    def update(self):
        """Update this room with its current values"""
        roomUuid = self["uuid"]

        url = API_PATH["rooms"].format(tuneUuid=self._parentTune.uuid(), roomUuid=roomUuid)
        self._put(url, data=self.json())

    async def async_update(self):
        """Update this room with its current values (async)"""
        roomUuid = self["uuid"]

        url = API_PATH["rooms"].format(tuneUuid=self._parentTune.uuid(), roomUuid=roomUuid)
        await self._async_put(url, data=self.json())

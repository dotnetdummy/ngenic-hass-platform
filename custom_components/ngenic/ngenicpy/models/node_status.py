import logging
from .base import NgenicBase
from ..const import API_PATH

_LOGGER = logging.getLogger(__name__)


class NodeStatus(NgenicBase):
    def __init__(self, session, json, node):
        self._parentNode = node

        super(NodeStatus, self).__init__(session=session, json=json)

    def battery_percentage(self):
        if self["maxBattery"] == 0:
            # not using batteries
            _LOGGER.debug("Node %s is not using batteries",
                          self._parentNode.uuid())
            return 100

        return int((self["battery"] / self["maxBattery"]) * 100)

    def radio_signal_percentage(self):
        if self["maxRadioStatus"] == 0:
            # shouldn't happen as of now (always maxRadioStatus is always 4)
            return 100

        return int((self["radioStatus"] / self["maxRadioStatus"]) * 100)

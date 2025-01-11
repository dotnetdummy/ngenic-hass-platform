"""Node model."""

import asyncio
from enum import Enum
from typing import Any

import httpx

from ..const import API_PATH  # noqa: TID252
from .base import NgenicBase
from .measurement import Measurement, MeasurementType
from .node_status import NodeStatus


class NodeType(Enum):
    """Node type enumeration."""

    UNKNOWN = -1
    SENSOR = 0
    CONTROLLER = 1
    GATEWAY = 2
    INTERNAL = 3
    ROUTER = 4

    @classmethod
    def _missing_(cls, value):
        return cls.UNKNOWN


class Node(NgenicBase):
    """Ngenic API node model."""

    def __init__(
        self, session: httpx.AsyncClient, json_data: dict[str, Any], tuneUuid: str
    ) -> None:
        """Initialize the node model."""
        self._parentTuneUuid = tuneUuid

        # A cache for measurement types
        self._measurementTypes = None

        super().__init__(session=session, json_data=json_data)

    def get_type(self):
        """Get the node type."""
        return NodeType(self["type"])

    async def async_measurement_types(self) -> list[MeasurementType]:
        """Get types of available measurements for this node (async).

        :return:
            a list of measurement type enums
        :rtype:
            `list(~ngenic.models.measurement.MeasurementType)
        """
        if not self._measurementTypes:
            url = API_PATH["measurements_types"].format(
                tuneUuid=self._parentTuneUuid, nodeUuid=self.uuid()
            )
            measurements = self._parse(await self._async_get(url))
            self._measurementTypes = [MeasurementType(m) for m in measurements]

        return self._measurementTypes

    async def async_measurements(self) -> list[Measurement]:
        """Get latest measurements for a Node (async).

        Usually, you can get measurements from a `NodeType.SENSOR` or `NodeType.CONTROLLER`.

        :return:
            a list of measurements (if supported by the node)
        :rtype:
            `list(~ngenic.models.measurement.Measurement)`
        """
        # get available measurement types for this node
        measurement_types = await self.async_measurement_types()

        # remove types that doesn't support reading from latest API
        if MeasurementType.ENERGY_KWH in measurement_types:
            measurement_types.remove(MeasurementType.ENERGY_KWH)

        if len(measurement_types) == 0:
            return []

        # retrieve latest measurement for each type
        return list(
            await asyncio.gather(
                *[self.async_measurement(t) for t in measurement_types]
            )
        )

    async def async_measurement(
        self,
        measurement_type: MeasurementType,
        from_dt: str | None = None,
        to_dt: str | None = None,
        period=None,
    ) -> Measurement | list[Measurement] | None:
        """Get measurement for a specific period (async).

        :param MeasurementType measurement_type:
            (required) type of measurement
        :param from_dt:
            (optional) from datetime (ISO 8601:2004)
        :param to_dt:
            (optional) to datetime (ISO 8601:2004)
        :param period:
            Divides measurement interval into periods, default is a single period over entire interval.
            (ISO 8601:2004 duration format)
        :return:
            the measurement.
            if no data is available for the period, None will be returned.
        :rtype:
            `list(~ngenic.models.measurement.Measurement)`
        """
        if from_dt is None:
            url = API_PATH["measurements_latest"].format(
                tuneUuid=self._parentTuneUuid, nodeUuid=self.uuid()
            )
            url += f"?type={measurement_type.value}"
            return await self._async_parse_new_instance(
                url, Measurement, measurement_type=measurement_type
            )
        url = API_PATH["measurements"].format(
            tuneUuid=self._parentTuneUuid, nodeUuid=self.uuid()
        )
        url += f"?type={measurement_type.value}&from={from_dt}&to={to_dt}"
        if period:
            url += f"&period={period}"
        return await self._async_parse_new_instance(
            url, Measurement, measurement_type=measurement_type
        )

    async def async_status(self) -> NodeStatus | None:
        """Get status about this Node.

        There are no API for getting the status for a single node, so we
        will use the list API and find our node in there.

        :return:
            a status object or None if Node doesn't support status
        :rtype:
            `~ngenic.models.node_status.NodeStatus`
        """
        url = API_PATH["node_status"].format(tuneUuid=self._parentTuneUuid)
        rsp_json = self._parse(await self._async_get(url))

        for status_obj in rsp_json:
            if status_obj["nodeUuid"] == self.uuid():
                return self._new_instance(NodeStatus, status_obj, nodeUuid=self.uuid())
        return None

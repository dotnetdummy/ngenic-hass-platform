"""The sensors package."""

import logging

from ngenicpy.models.measurement import Measurement
from ngenicpy.models.node import Node

import homeassistant.util.dt as dt_util

TIME_ZONE = (
    "Z" if str(dt_util.DEFAULT_TIME_ZONE) == "UTC" else str(dt_util.DEFAULT_TIME_ZONE)
)

_LOGGER = logging.getLogger(__name__)


async def get_measurement_value(node: Node, **kwargs) -> float | None:
    """Get measurement.

    This is a wrapper around the measurement API to gather
    parsing and error handling in a single place.
    """

    measurement = await node.async_measurement(**kwargs)

    if not measurement:
        # measurement API will return None if no measurements were found for the period
        _LOGGER.info(
            "Measurement not found for period, this is expected when data have not been gathered for the period (type=%s, from=%s, to=%s, invalidate_cache=%s)",
            kwargs.get("measurement_type", "unknown"),
            kwargs.get("from_dt", "None"),
            kwargs.get("to_dt", "None"),
            kwargs.get("invalidate_cache", "False"),
        )
        measurement_val = None
    else:
        # using datetime will return a list of measurements
        # we'll use the last item in that list
        if isinstance(measurement, list):
            measurement = measurement[-1]

        if not _has_value(measurement):
            _LOGGER.info(
                "Measurement has no value for period (type=%s, from=%s, to=%s)",
                kwargs.get("measurement_type", "unknown"),
                kwargs.get("from_dt", "None"),
                kwargs.get("to_dt", "None"),
            )
            measurement_val = None
        else:
            measurement_val = measurement["value"]

    return measurement_val


def _has_value(measurement: Measurement) -> bool:
    """Return if a value is present in the measurement period."""
    try:
        return measurement["hasValue"] is not False
    except AttributeError:
        # older responses may not include hasValue, assume the value is present
        return True

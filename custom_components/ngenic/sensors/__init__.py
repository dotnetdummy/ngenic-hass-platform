"""The sensors package."""

import logging
from typing import Any, Optional, Union, Dict, List # Added Optional, Union, Dict, List
from datetime import datetime # Added datetime

# ngenicpy models with try-except for graceful fallback
try:
    from ngenicpy.models.node import Node
except ImportError:
    _LOGGER = logging.getLogger(__name__) # Ensure logger is defined before use
    _LOGGER.warning("ngenicpy.models.node.Node not found, using Any type instead.")
    Node = Any # type: ignore
try:
    from ngenicpy.models.measurement import MeasurementType
except ImportError:
    _LOGGER = logging.getLogger(__name__) # Ensure logger is defined before use
    _LOGGER.warning("ngenicpy.models.measurement.MeasurementType not found, using Any type instead.")
    MeasurementType = Any # type: ignore


import homeassistant.util.dt as dt_util

TIME_ZONE: str = ( # Typed TIME_ZONE
    "Z" if str(dt_util.DEFAULT_TIME_ZONE) == "UTC" else str(dt_util.DEFAULT_TIME_ZONE)
)

_LOGGER = logging.getLogger(__name__)


async def get_measurement_value(
    node: Node,
    measurement_type: Union[MeasurementType, str],
    from_dt: Optional[datetime] = None,
    to_dt: Optional[datetime] = None,
    invalidate_cache: bool = False,
) -> Optional[float]: # Changed return type to Optional[float]
    """Get measurement.

    This is a wrapper around the measurement API to gather
    parsing and error handling in a single place.
    Returns the measurement value, or None if not found or error.
    """
    # Prepare kwargs for node.async_measurement, filtering out None values for from_dt/to_dt
    api_kwargs: Dict[str, Any] = {"measurement_type": measurement_type, "invalidate_cache": invalidate_cache}
    if from_dt:
        api_kwargs["from_dt"] = from_dt
    if to_dt:
        api_kwargs["to_dt"] = to_dt

    try:
        # Assuming node can be Any if import failed
        measurement_data = await node.async_measurement(**api_kwargs) # type: ignore[union-attr]
    except Exception as e:
        _LOGGER.error(
            "Error fetching measurement (type=%s, node_uuid=%s): %s",
            measurement_type,
            node.uuid() if hasattr(node, "uuid") else "unknown", # type: ignore[union-attr]
            e
        )
        return None


    if not measurement_data:
        # measurement API will return None if no measurements were found for the period
        _LOGGER.info(
            "Measurement not found for period (type=%s, node_uuid=%s, from=%s, to=%s, invalidate_cache=%s)",
            measurement_type,
            node.uuid() if hasattr(node, "uuid") else "unknown", # type: ignore[union-attr]
            from_dt,
            to_dt,
            invalidate_cache,
        )
        return None # Return None instead of 0 for clarity
    
    measurement_val: Optional[float] = None
    try:
        if isinstance(measurement_data, list):
            # using datetime will return a list of measurements
            # we'll use the last item in that list if it exists
            if measurement_data:
                # Assuming value is float or can be cast to float
                measurement_val = float(measurement_data[-1]["value"])
            else:
                _LOGGER.info("Measurement data list is empty (type=%s, node_uuid=%s)", measurement_type, node.uuid() if hasattr(node, "uuid") else "unknown") # type: ignore[union-attr]
        else: # Assuming it's a single measurement dictionary
            # Assuming value is float or can be cast to float
            measurement_val = float(measurement_data["value"])
    except (TypeError, ValueError, KeyError) as e:
        _LOGGER.error(
            "Error parsing measurement value (type=%s, node_uuid=%s, data=%s): %s",
            measurement_type,
            node.uuid() if hasattr(node, "uuid") else "unknown", # type: ignore[union-attr]
            measurement_data,
            e
        )
        return None


    return measurement_val

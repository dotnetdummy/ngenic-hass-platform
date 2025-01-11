"""Constants for the NgenicPy library."""

from typing import Final

API_URL: Final[str] = "https://app.ngenic.se/api/v3"

API_PATH: Final[dict[str, str]] = {
    "tunes": "tunes/{tuneUuid}",
    "rooms": "tunes/{tuneUuid}/rooms/{roomUuid}",
    "nodes": "tunes/{tuneUuid}/gateway/nodes/{nodeUuid}",
    "node_status": "tunes/{tuneUuid}/nodestatus",
    "measurements": "tunes/{tuneUuid}/measurements/{nodeUuid}",
    "measurements_types": "tunes/{tuneUuid}/measurements/{nodeUuid}/types",
    "measurements_latest": "tunes/{tuneUuid}/measurements/{nodeUuid}/latest",
    "setpoint_schedules": "tunes/{tuneUuid}/setpointschedules",
}

SETPONT_SCHEDULE_NAME: Final[str] = "Home Assistant away schedule"

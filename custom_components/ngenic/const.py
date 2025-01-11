"""Constants for the Ngenic integration."""

from datetime import timedelta
from typing import Final

DOMAIN: Final[str] = "ngenic"
BRAND: Final[str] = "Ngenic"
DATA_CLIENT: Final[str] = "data_client"
DATA_CONFIG: Final[str] = "config"
UPDATE_SCHEDULE_TOPIC: Final = f"{DOMAIN}_schedule_update"
SERVICE_SET_ACTIVE_CONTROL: Final[str] = "set_active_control"
SERVICE_SET_AWAY_SCHEDULE: Final[str] = "set_away_schedule"
SERVICE_ACTIVATE_AWAY: Final[str] = "activate_away"
SERVICE_DEACTIVATE_AWAY: Final[str] = "deactivate_away"


"""
How often to re-scan sensor information.
From API doc: Tune system Nodes generally report data in intervals of five
minutes, so there is no point in polling the API for new data at a higher rate.
"""
SCAN_INTERVAL: Final[timedelta] = timedelta(minutes=5)

# AppLimiter/src/applimiter/constants.py


"""
Store all constants
"""

CONFIG_FILE_PATH = "/etc/AppLimiter/config.json"
USAGE_DATA_PATH = "/var/lib/AppLimiter/usage_data.json"
GRACE_PERIOD_SECONDS = 5 * 60
PROCESS_TERMINATING_PATIENCE = 5
DAEMON_CHECK_INTERVAL_SECONDS = 60


DEFAULT_CONFIG_FILE = {
    "applications": [],
    "enable_config_modification_delay": False,
    "config_modification_delay_seconds": 0,
    "pending_modifications": [],

}

DEFAULT_USAGE_DATA_FILE = {}

INITIAL_USAGE_DATA_STRUCTURE = {
    "daily_seconds_today": 0,
    "weekly_seconds_this_week": 0,
    "last_daily_reset_date": "1970-01-01",
    "last_weekly_reset_date": "1970-01-01",
    "notif_daily_5_sent": False,
    "notif_daily_limit_reached_sent": False,
    "notif_weekly_5_sent": False,
    "notif_weekly_limit_reached_sent": False,
    "first_limit_breach_type": None,
    "first_limit_breach_timestamp": None,
}

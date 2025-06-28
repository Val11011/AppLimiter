# AppLimiter/src/applimiter/daemon.py

"""
Contains the core run_daemon function for background monitoring.
"""

import os
import sys
import time
import datetime
import logging
import traceback


from applimiter.constants import (
    CONFIG_FILE_PATH,
    USAGE_DATA_PATH,
    GRACE_PERIOD_SECONDS,
    DAEMON_CHECK_INTERVAL_SECONDS,
    DEFAULT_CONFIG_FILE,
    DEFAULT_USAGE_DATA_FILE,
    INITIAL_USAGE_DATA_STRUCTURE,
)
from applimiter.utils import load_json, save_json, check_dependencies
from applimiter.process_handler import get_process_pids, terminate_process
from applimiter.notification_manager import (
    get_desktop_users_with_display_info,
    send_desktop_notification_zenity,
)

# get a logger
logger = logging.getLogger(__name__)


def run_daemon(check_interval=DAEMON_CHECK_INTERVAL_SECONDS):
    """
    The main daemon loop to monitor application usage
    :param check_interval: the interval between checks in seconds
    :return: None
    """
    # exit if not running in root
    if os.getuid() != 0:
        logger.error("Daemon mode requires root privileges to run.")
        sys.exit(1)

    # configure logger
    root_logger = logging.getLogger()
    if not root_logger.hasHandlers():
        daemon_stream_handler = logging.StreamHandler(sys.stderr)
        formatter = logging.Formatter(
            "%(asctime)s - %(levelname)s - %(module)s - %(funcName)s - %(message)s"
        )
        daemon_stream_handler.setFormatter(formatter)
        root_logger.addHandler(daemon_stream_handler)
        root_logger.setLevel(logging.INFO)

    # check dependencies
    if not check_dependencies():
        logger.error("Dependencies not satisfied, exiting.")
        sys.exit(1)

    # show daemon info
    logger.info(
        f"AppLimiter daemon started (PID: {os.getpid()})"
        f"Check interval: {check_interval}"
    )

    try:
        while True:
            # load config amd usage data
            config = load_json(CONFIG_FILE_PATH, DEFAULT_CONFIG_FILE)
            usage_data_all_apps = load_json(USAGE_DATA_PATH, DEFAULT_USAGE_DATA_FILE)

            # record if need to save usage data file
            apps_data_changed_this_cycle = False

            # --- time logic ---
            now = datetime.datetime.now()
            # get current date and weekday
            today_str = now.strftime("%Y-%m-%d")
            day_of_week_today = now.weekday()  # 0 is Monday, 6 is Sunday
            # get the start date of current week
            days_since_week_start = (day_of_week_today - 0) % 7
            current_week_start_date = now - datetime.timedelta(
                days=days_since_week_start
            )
            current_week_start_date_str = current_week_start_date.strftime("%Y-%m-%d")

            # get desktop user info
            current_desktop_users = get_desktop_users_with_display_info()
            # iterate through each configured application
            for app_config in config.get("applications", []):
                app_name = app_config["name"]
                keywords = app_config.get("process_keywords", [])

                # ... (limit calculation logic) ...
                daily_limits_by_day_config = app_config.get("daily_limits_by_day")
                todays_daily_limit_min = float("inf")
                if daily_limits_by_day_config:
                    if 0 <= day_of_week_today <= 4:
                        todays_daily_limit_min = float(
                            daily_limits_by_day_config.get("weekdays", float("inf"))
                        )
                    else:
                        todays_daily_limit_min = float(
                            daily_limits_by_day_config.get("weekends", float("inf"))
                        )
                daily_limit_sec = (
                    todays_daily_limit_min * 60
                    if todays_daily_limit_min != float("inf")
                    else float("inf")
                )
                weekly_limit_sec_val = app_config.get(
                    "weekly_limit_minutes", float("inf")
                )
                weekly_limit_sec = (
                    float(weekly_limit_sec_val) * 60
                    if weekly_limit_sec_val != float("inf")
                    else float("inf")
                )

                if not keywords:
                    continue

                app_usage = usage_data_all_apps.get(
                    app_name, INITIAL_USAGE_DATA_STRUCTURE.copy()
                )
                for key, default_value in INITIAL_USAGE_DATA_STRUCTURE.items():
                    app_usage.setdefault(key, default_value)

                # check if we need to reset daily usage data
                daily_reset_needed = app_usage.get("last_daily_reset_date") != today_str
                if daily_reset_needed:
                    logger.info(f"Performing daily reset for app: {app_name}")
                    app_usage.update(
                        {
                            "daily_seconds_today": 0,
                            "last_daily_reset_date": today_str,
                            "notif_daily_5_sent": False,
                            "notif_daily_limit_reached_sent": False,
                        }
                    )
                    apps_data_changed_this_cycle = True

                # check if we need to reset weekly usage data
                weekly_reset_needed = (
                    app_usage.get("last_weekly_reset_date")
                    != current_week_start_date_str
                )
                if weekly_reset_needed:
                    logger.info(f"Performing weekly reset for app: {app_name}")
                    app_usage.update(
                        {
                            "weekly_seconds_this_week": 0,
                            "last_weekly_reset_date": current_week_start_date_str,
                            "notif_weekly_5_sent": False,
                            "notif_weekly_limit_reached_sent": False,
                        }
                    )
                    apps_data_changed_this_cycle = True

                # ... (rest of the loop, including process check and notification logic) ...
                if (
                    daily_reset_needed
                    and app_usage.get("first_limit_breach_type") == "daily"
                ) or (
                    weekly_reset_needed
                    and app_usage.get("first_limit_breach_type") == "weekly"
                ):
                    logger.info(
                        f"Resetting limit breach state for app {app_name} due to daily/weekly reset."
                    )
                    app_usage["first_limit_breach_timestamp"] = None
                    app_usage["first_limit_breach_type"] = None

                pids = get_process_pids(keywords)
                # ... (process running check, trigger_zenity function definition) ...
                if bool(pids):
                    app_usage["daily_seconds_today"] += check_interval
                    app_usage["weekly_seconds_this_week"] += check_interval
                    apps_data_changed_this_cycle = True

                def trigger_zenity_for_all_users(
                    title_suffix, message_body, dialog_type="--warning"
                ):
                    if not current_desktop_users:
                        logger.info(
                            f"No desktop users to notify for {app_name} - {title_suffix}."
                        )
                        return
                    for user_info_item in current_desktop_users:
                        send_desktop_notification_zenity(
                            f"{app_name}: {title_suffix}",
                            message_body,
                            user_info_item,
                            dialog_type=dialog_type,
                        )

                if app_usage.get("first_limit_breach_timestamp") is not None:
                    if (
                        time.time()
                        >= app_usage["first_limit_breach_timestamp"]
                        + GRACE_PERIOD_SECONDS
                    ):
                        if bool(pids):
                            limit_type_str = app_usage.get(
                                "first_limit_breach_type", "Time"
                            ).capitalize()
                            logger.info(
                                f"Grace period expired for app {app_name}. Terminating."
                            )
                            trigger_zenity_for_all_users(
                                f"{limit_type_str} Limit: Terminated",
                                f"The grace period has ended.\nApplication '{app_name}' has been closed.",
                                "--error",
                            )
                            for pid in pids:
                                terminate_process(pid, app_name)

                # --- MODIFIED NOTIFICATION LOGIC ---
                if app_usage.get("first_limit_breach_timestamp") is None:
                    limit_min_str_daily = (
                        f"{todays_daily_limit_min:.0f}"
                        if todays_daily_limit_min != float("inf")
                        else "unlimited"
                    )
                    if daily_limit_sec != float("inf"):
                        if app_usage[
                            "daily_seconds_today"
                        ] >= daily_limit_sec and not app_usage.get(
                            "notif_daily_limit_reached_sent"
                        ):
                            logger.info(
                                f"App {app_name} has reached its daily limit ({limit_min_str_daily} min)."
                            )
                            trigger_zenity_for_all_users(
                                "Daily Limit Reached",
                                f"'{app_name}' has used its daily minutes.\nIt will close in {GRACE_PERIOD_SECONDS / 60:.0f} minutes.",
                                "--warning",
                            )
                            app_usage["notif_daily_limit_reached_sent"] = True
                            app_usage["first_limit_breach_timestamp"] = time.time()
                            app_usage["first_limit_breach_type"] = "daily"
                            apps_data_changed_this_cycle = True
                        elif daily_limit_sec - (5 * 60) < app_usage[
                            "daily_seconds_today"
                        ] < daily_limit_sec and not app_usage.get("notif_daily_5_sent"):
                            logger.info(
                                f"App {app_name} approaching daily limit - 5 minute warning."
                            )
                            trigger_zenity_for_all_users(
                                "Daily Time Warning",
                                f"'{app_name}' has approximately 5 minutes of daily time remaining.",
                                "--info",
                            )
                            app_usage["notif_daily_5_sent"] = True
                            apps_data_changed_this_cycle = True

                    if app_usage.get(
                        "first_limit_breach_timestamp"
                    ) is None and weekly_limit_sec != float("inf"):
                        weekly_limit_min_config = app_config.get(
                            "weekly_limit_minutes", float("inf")
                        )
                        limit_min_str_weekly = (
                            f"{weekly_limit_min_config:.0f}"
                            if weekly_limit_min_config != float("inf")
                            else "unlimited"
                        )
                        if app_usage[
                            "weekly_seconds_this_week"
                        ] >= weekly_limit_sec and not app_usage.get(
                            "notif_weekly_limit_reached_sent"
                        ):
                            logger.info(
                                f"App {app_name} has reached its weekly limit ({limit_min_str_weekly} min)."
                            )
                            trigger_zenity_for_all_users(
                                "Weekly Limit Reached",
                                f"'{app_name}' has used its weekly minutes.\nIt will close in {GRACE_PERIOD_SECONDS / 60:.0f} minutes.",
                                "--warning",
                            )
                            app_usage["notif_weekly_limit_reached_sent"] = True
                            app_usage["first_limit_breach_timestamp"] = time.time()
                            app_usage["first_limit_breach_type"] = "weekly"
                            apps_data_changed_this_cycle = True
                        elif weekly_limit_sec - (5 * 60) < app_usage[
                            "weekly_seconds_this_week"
                        ] < weekly_limit_sec and not app_usage.get(
                            "notif_weekly_5_sent"
                        ):
                            logger.info(
                                f"App {app_name} approaching weekly limit - 5 minute warning."
                            )
                            trigger_zenity_for_all_users(
                                "Weekly Time Warning",
                                f"'{app_name}' has approximately 5 minutes of weekly time remaining.",
                                "--info",
                            )
                            app_usage["notif_weekly_5_sent"] = True
                            apps_data_changed_this_cycle = True

                usage_data_all_apps[app_name] = app_usage

            if apps_data_changed_this_cycle:
                save_json(USAGE_DATA_PATH, usage_data_all_apps)

            time.sleep(check_interval)

    except KeyboardInterrupt:
        logger.info("App Limiter daemon stopped by user (KeyboardInterrupt).")
    except Exception as e:
        logger.critical(f"A critical error occurred in the main daemon loop: {e}")
        logger.error(traceback.format_exc())
    finally:
        logger.info("App Limiter daemon is shutting down.")

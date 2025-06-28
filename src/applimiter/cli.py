# AppLimiter/src/applimiter/cli.py

"""
Store all functions used to deal with cli input
"""

import sys
import time
import datetime
import argparse
import logging
from copy import deepcopy

from applimiter.constants import (
    CONFIG_FILE_PATH,
    USAGE_DATA_PATH,
    INITIAL_USAGE_DATA_STRUCTURE,
    GRACE_PERIOD_SECONDS,
)
from applimiter.utils import load_json, save_json, check_exists_app, check_privilege
from applimiter.process_handler import get_process_pids

logger = logging.getLogger(__name__)


def setup_logging():
    """
    Configure the basic logging for cli output
    :return: None
    """
    logging.basicConfig(
        level=logging.INFO,
        format="%(levelname)s: %(message)s",
        handlers=[logging.StreamHandler(sys.stdout)],
    )


def parse_arguments():
    """
    Defines and parses command-line arguments for the application.
    :return: argparse.Namespace
    """

    # to get a better output
    PROGRAM_NAME = "applimiter"

    parser = argparse.ArgumentParser(
        prog=PROGRAM_NAME,
        description="AppLimiter: Your personal application usage manager.",
        epilog=f"Example usage:\n"
               f'  sudo {PROGRAM_NAME} add Steam --keywords "steam.sh" ...\n'
               f"  {PROGRAM_NAME} status",
        formatter_class=argparse.RawTextHelpFormatter,
    )
    # --- add subparsers to deal with all subcommands ---
    subparsers = parser.add_subparsers(
        dest="command", required=True, title="Available commands", metavar="COMMAND"
    )

    # daemon
    parser_daemon = subparsers.add_parser(
        "daemon", help="Run the limiter daemon (requires root)."
    )
    parser_daemon.add_argument(
        "-i",
        "--interval",
        type=int,
        default=60,
        help="Check interval in seconds (default: 60).",
    )
    # add
    parser_add = subparsers.add_parser(
        "add", help="Add a new application to monitor (requires root)."
    )
    parser_add.add_argument(
        "name", help="A unique name for the application (e.g., 'Steam')."
    )
    parser_add.add_argument(
        "-k",
        "--keywords",
        nargs="+",
        required=True,
        help="One or more keywords to identify the process.",
    )
    parser_add.add_argument(
        "-dw",
        "--daily-weekdays",
        type=int,
        required=True,
        help="Daily usage limit in minutes for weekdays.",
    )
    parser_add.add_argument(
        "-dW",
        "--daily-weekends",
        type=int,
        required=True,
        help="Daily usage limit in minutes for weekends.",
    )
    parser_add.add_argument(
        "-w",
        "--weekly",
        type=int,
        required=True,
        help="Total weekly usage limit in minutes.",
    )

    # remove
    parser_remove = subparsers.add_parser(
        "remove", help="Remove a monitored application (requires root)."
    )
    parser_remove.add_argument("name", help="The name of the application to remove.")

    # update
    parser_update = subparsers.add_parser(
        "update", help="Update an existing application's limits (requires root)."
    )
    parser_update.add_argument("name", help="The name of the application to update.")
    parser_update.add_argument(
        "-k", "--keywords", nargs="+", help="A new list of process keywords."
    )
    parser_update.add_argument(
        "-d-w", "--daily-weekdays", type=int, help="New daily limit for weekdays."
    )
    parser_update.add_argument(
        "-d-W", "--daily-weekends", type=int, help="New daily limit for weekends."
    )
    parser_update.add_argument(
        "-w", "--weekly", type=int, help="New weekly limit in minutes."
    )

    # update usage
    parser_update_usage = subparsers.add_parser(
        "update-usage",
        help="Manually update extra usage time for an app (requires root).",
    )
    parser_update_usage.add_argument("name", help="The name of the application.")
    parser_update_usage.add_argument(
        "minutes", type=int, help="The number of minutes to add or remove."
    )

    # status
    subparsers.add_parser(
        "status", help="Display the current usage status of all apps."
    )

    # list
    subparsers.add_parser(
        "list", help="List all configured applications and their limits."
    )

    # config delay
    parser_config_delay = subparsers.add_parser(
        "config-delay", help="Enable or disable the modification delay (requires root)."
    )
    config_delay_subparsers = parser_config_delay.add_subparsers(
        dest="config_delay_action", required=True
    )
    parser_config_delay_enable = config_delay_subparsers.add_parser(
        "enable", help="Enable the modification delay."
    )
    parser_config_delay_enable.add_argument(
        "-m",
        "--minutes",
        type=int,
        default=5,
        metavar="MINUTES",
        help="Set the delay duration in minutes (default: 5).",
    )
    config_delay_subparsers.add_parser(
        "disable", help="Disable the modification delay."
    )

    # pending
    parser_pending = subparsers.add_parser(
        "pending", help="Manage pending configuration changes."
    )
    pending_subparsers = parser_pending.add_subparsers(
        dest="pending_action", required=True, help="Action for pending modifications."
    )
    pending_subparsers.add_parser("list", help="List all pending modifications.")
    parser_pending_clear = pending_subparsers.add_parser(
        "clear", help="Clear pending modifications (requires root)."
    )
    parser_pending_clear.add_argument(
        "item_number_or_all",
        nargs="?",
        default="all",
        type=str,
        help="The index number to clear, or 'all'.",
    )
    parser_pending_apply = pending_subparsers.add_parser(
        "apply", help="Apply pending modifications (requires root)."
    )
    parser_pending_apply.add_argument(
        "item_number_or_all",
        nargs="?",
        default="all",
        type=str,
        help="The index number to apply, or 'all'.",
    )

    return parser.parse_args()


def handle_cli_command(args, script_call_example="applimiter"):
    """
    Handles all CLI commands and output to stdout/stderr.
    :param args: argparse.Namespace that contains the CLI input.
    :param script_call_example:.....
    :return: None
    """
    # exit if the permission is not satisfied
    if not check_privilege(args):
        print(
            f""
            f"Error: Command '{args.command}' requires root privileges. Please use sudo.",
            file=sys.stderr,
        )
        sys.exit(1)

    # load config dict and create a copy
    config = load_json(
        CONFIG_FILE_PATH, read_only=False
    )  # Load with write access for most commands
    config_copy = deepcopy(config)

    # Command Dispatcher
    if args.command in ["add", "update", "config-delay"]:
        _handle_add_update_config_delay_commands(args, config_copy)

    elif args.command == "remove":
        _handle_remove_command(args, config_copy)

    elif args.command == "pending":
        _handle_pending_command(args, config_copy)

    elif args.command == "status":
        _handle_status_command(args, config_copy)

    elif args.command == "list":
        _handle_list_command(args, config_copy)

    elif args.command == "update-usage":
        _handle_update_usage_command(args, config_copy)


def _handle_add_update_config_delay_commands(args, config):
    """
    handle add, update, config-delay
    :param args: argparse.Namespace
    :param config: the config dict read from config file
    :return: None
    """
    action_payload = None

    # add
    if args.command == "add":
        action_payload = {
            "action": "add_app",
            "payload": {
                "name": args.name,
                "process_keywords": args.keywords,
                "daily_limits_by_day": {
                    "weekdays": args.daily_weekdays,
                    "weekends": args.daily_weekends,
                },
                "weekly_limits": args.weekly,
            },
        }

    # update
    elif args.command == "update":
        payload = {"name": args.name}
        if (args.daily_weekdays is not None) != (args.daily_weekends is not None):
            print(
                "Error: For daily limits, --daily-weekdays and --daily-weekends must be used together.",
                file=sys.stderr,
            )
            return
        if args.daily_weekdays is not None:
            payload["daily_limits_by_day"] = {
                "weekdays": args.daily_weekdays,
                "weekends": args.daily_weekends,
            }
        if args.weekly is not None:
            payload["weekly_limit_minutes"] = args.weekly
        if args.keywords is not None:
            payload["process_keywords"] = args.keywords
        if len(payload) > 1:
            action_payload = {"action": "update_app", "payload": payload}
        else:
            print(
                "Error: Update command requires at least one field to change.",
                file=sys.stderr,
            )
            return

    # config delay
    elif args.command == "config-delay":
        if args.config_delay_action == "enable":
            action_payload = {
                "action": "set_config_delay",
                "payload": {"enable": True, "delay_seconds": args.minutes * 60},
            }
        elif args.config_delay_action == "disable":
            action_payload = {
                "action": "set_config_delay",
                "payload": {
                    "enable": False, "delay_seconds": 0,
                },
            }

    if action_payload:
        needs_delay = False
        if config.get("enable_config_modification_delay", False):
            if action_payload["action"] == "update_app":
                app_to_update = next(
                    (
                        app
                        for app in config.get("applications", [])
                        if app["name"] == action_payload["payload"]["name"]
                    ),
                    None,
                )
                if app_to_update:
                    if "daily_limits_by_day" in action_payload["payload"] and (
                            float(
                                action_payload["payload"]["daily_limits_by_day"][
                                    "weekdays"
                                ]
                            )
                            > float(
                        app_to_update.get("daily_limits_by_day", {}).get(
                            "weekdays", 0
                        )
                    )
                            or float(
                        action_payload["payload"]["daily_limits_by_day"][
                            "weekends"
                        ]
                    )
                            > float(
                        app_to_update.get("daily_limits_by_day", {}).get(
                            "weekends", 0
                        )
                    )
                    ):
                        needs_delay = True
                    if (
                            not needs_delay
                            and "weekly_limit_minutes" in action_payload["payload"]
                            and float(action_payload["payload"]["weekly_limit_minutes"])
                            > float(app_to_update.get("weekly_limit_minutes", 0))
                    ):
                        needs_delay = True

        if needs_delay:

            pending_item = {
                **action_payload,
                "unlock_timestamp": time.time() + config.get(
                    "config_modification_delay_seconds", 0
                ),
                "id": f"{datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%S%f')}_{action_payload['action']}",
            }
            config.setdefault("pending_modifications", []).append(
                pending_item
            )
            save_json(CONFIG_FILE_PATH, config)
            unlock_time_str = datetime.datetime.fromtimestamp(
                pending_item["unlock_timestamp"]
            ).strftime("%Y-%m-%d %H:%M:%S")
            print(
                f"Action added to pending queue. Apply after {unlock_time_str}."
            )
        else:
            if _apply_config_modification(config, action_payload):
                save_json(CONFIG_FILE_PATH, config)
                print(f"Action '{args.command}' applied successfully.")


def _handle_update_usage_command(args, config):
    """
    Handle update-usage command
    :param args: the argparse namespace
    :param config: the config dict read from config file
    :return: None
    """
    app_name = args.name
    # check if the app exists
    if not check_exists_app(app_name, config):
        print(f"Error: Application '{app_name}' not found.", file=sys.stderr)
        return
    # load usage, do some changes, save it
    usage_data = load_json(USAGE_DATA_PATH, {})
    app_usage = usage_data.setdefault(app_name, INITIAL_USAGE_DATA_STRUCTURE.copy())
    app_usage["daily_seconds_today"] += args.minutes * 60
    app_usage["daily_seconds_today"] = max(app_usage["daily_seconds_today"], 0)
    app_usage["weekly_seconds_this_week"] += args.minutes * 60
    app_usage["weekly_seconds_this_week"] = max(
        app_usage["weekly_seconds_this_week"], 0
    )
    save_json(USAGE_DATA_PATH, usage_data)
    # print the result
    add_or_remove = "added" if args.minutes >= 0 else "removed"
    print(
        f"Successfully {add_or_remove} an extra {abs(args.minutes)} minutes for '{app_name}'."
    )


def _handle_list_command(args, config):
    """
    Handle list command
    :param args: the argparse namespace
    :param config: the config dict read from config file
    :return: None
    """
    print("--- Configured Applications ---")
    if not config.get("applications"):
        print("No applications configured.")
    for app_conf in config.get("applications", []):
        daily_limits = app_conf.get("daily_limits_by_day", {})
        wd_limit = daily_limits.get("weekdays", "Unlimited")
        we_limit = daily_limits.get("weekends", "Unlimited")
        weekly_limit = app_conf.get("weekly_limit_minutes", "Unlimited")
        print(
            f"- Name: {app_conf['name']}\n"
            f"  Keywords: {', '.join(app_conf.get('process_keywords', []))}\n"
            f"  Daily Limit: Weekdays {wd_limit} min, Weekends {we_limit} min\n"
            f"  Weekly Limit: {weekly_limit} min\n" + "-" * 10
        )


def _handle_status_command(args, config):
    """
    handle status command
    :param args: the argparse namespace
    :param config: the config dict read from config file
    :return: None
    """

    usage_data = load_json(USAGE_DATA_PATH, {}, read_only=True)
    print("--- Application Status ---")
    # applications
    if not config.get("applications"):
        print("No applications configured.")
    for app_conf in config.get("applications", []):
        name = app_conf["name"]
        app_usage = usage_data.get(name, INITIAL_USAGE_DATA_STRUCTURE.copy())
        daily_used_s = app_usage.get("daily_seconds_today", 0)
        weekly_used_s = app_usage.get("weekly_seconds_this_week", 0)
        is_weekday = 0 <= datetime.datetime.now().weekday() <= 4
        day_type_str = (
            "(Weekday)" if is_weekday else "(Weekend)"
        )
        todays_daily_limit_m = app_conf.get("daily_limits_by_day", {}).get(
            "weekdays" if day_type_str == "(Weekday)" else "weekends", float("inf")
        )
        weekly_limit_m = app_conf.get("weekly_limit_minutes", float("inf"))
        pids = get_process_pids(app_conf.get("process_keywords", []))
        running_status = f"Running (PIDs: {pids})" if pids else "Not Running"
        print(f"\nApp: {name} ({running_status})")
        print(
            f"  Today {day_type_str}: {daily_used_s / 60:.1f} /"
            f" {todays_daily_limit_m if todays_daily_limit_m != float('inf') else 'Unlimited'} min"
        )
        print(
            f"  This Week: {weekly_used_s / 60:.1f} / "
            f"{weekly_limit_m if weekly_limit_m != float('inf') else 'Unlimited'} min"
        )
        if app_usage.get("first_limit_breach_timestamp"):
            breach_time = app_usage["first_limit_breach_timestamp"]
            grace_ends = breach_time + GRACE_PERIOD_SECONDS
            if time.time() < grace_ends:
                print(
                    f"  Status: In grace period ({int(grace_ends - time.time())}s remaining)"
                )
            else:
                print("  Status: Grace period expired")
    print("\n--- Global Configuration ---")
    # modification delay
    modification_delay_enabled = config.get('enable_config_modification_delay', False)
    modification_delay_str = f"Modification Delay: {'Enabled' if modification_delay_enabled else 'Disabled'}"
    if modification_delay_enabled:
        modification_delay_str += f" {config.get('config_modification_delay_seconds', 0)} s"
    print(modification_delay_str)
    # pending modifications
    if config.get("pending_modifications"):
        print(
            f"There are {len(config.get('pending_modifications', []))} pending modifications."
        )
    else:
        print("No pending modifications.")


def _handle_pending_command(args, config):
    """
    Handle pending command
    :param args: the argparse namespace
    :param config: the config dict read from config file
    :return: None
    """
    if args.pending_action == "list":
        current_pending_list = config.get("pending_modifications", [])
        if not current_pending_list:
            print("No pending modifications.")
            return
        print("--- Pending Modifications (in order) ---")
        for idx, item in enumerate(current_pending_list):
            unlock_time_unix = item.get("unlock_timestamp")
            time_left_str = " (Applicable)"
            if time.time() < unlock_time_unix:
                time_left = unlock_time_unix - time.time()
                time_left_str = f" ({int(time_left // 60)}m {int(time_left % 60)}s until applicable)"
            print(
                f"\n[{idx + 1}] ID: {item.get('id', 'No ID')}\n"
                f"  Action: {item.get('action')}\n"
                f"  Unlocks at: {datetime.datetime.fromtimestamp(unlock_time_unix).strftime('%Y-%m-%d %H:%M:%S')}{time_left_str}"
            )
        print("-" * 20 + f"\nTotal of {len(current_pending_list)} pending items.")

    elif args.pending_action == "clear":
        if not config.get("pending_modifications"):
            print("No pending modifications to clear.")
            return
        if args.item_number_or_all.lower() == "all":
            cleared_count = len(config["pending_modifications"])
            config["pending_modifications"] = []
            print(f"Cleared all {cleared_count} pending modifications.")
        else:
            try:
                item_index = int(args.item_number_or_all) - 1
                if 0 <= item_index < len(config["pending_modifications"]):
                    removed_item = config["pending_modifications"].pop(
                        item_index
                    )
                    print(
                        f"Cleared pending modification (ID: {removed_item.get('id', 'N/A')})."
                    )
                else:
                    print("Error: Invalid index.")
                    return
            except ValueError:
                print("Error: Invalid input.")
                return
        save_json(CONFIG_FILE_PATH, config)

    elif args.pending_action == "apply":
        _apply_pending_modifications_logic(
            args, config
        )


def _handle_remove_command(args, config):
    """
    Handle remove command
    :param args: argparse namespace
    :param config: the config dict read from config file
    :return: None
    """
    app_name = args.name
    # check if the app exists
    if not check_exists_app(app_name, config):
        print(f"Error: Application '{app_name}' not found.", file=sys.stderr)
        return

    if config.get("enable_config_modification_delay", False):
        action_payload = {"action": "remove_app", "payload": {"name": app_name}}
        pending_item = {
            **action_payload,
            "unlock_timestamp": time.time() + config.get("config_modification_delay_seconds", 0),
            "id": f"{datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%S%f')}_remove_{app_name}",
        }
        config.setdefault("pending_modifications", []).append(
            pending_item
        )
        save_json(CONFIG_FILE_PATH, config)
        unlock_time_str = datetime.datetime.fromtimestamp(
            pending_item["unlock_timestamp"]
        ).strftime("%Y-%m-%d %H:%M:%S")
        print(
            f"Action 'remove {app_name}' added to pending queue. Apply after {unlock_time_str}."
        )
    else:
        config["applications"] = [
            app for app in config.get("applications", []) if app["name"] != app_name
        ]
        save_json(CONFIG_FILE_PATH, config)
        print(f"Application '{app_name}' removed from configuration.")
        usage_data = load_json(USAGE_DATA_PATH, read_only=False)
        if app_name in usage_data:
            usage_data.pop(app_name)
            save_json(USAGE_DATA_PATH, usage_data)
            print(f"Usage data for '{app_name}' cleaned up.")


def _apply_pending_modifications_logic(args, config):
    """
    Apply the pending modifications based on item number or all.
    :param args: argparse.Namespace that contains the CLI input.
    :param config: the config dict read from config file
    :return: None
    """
    pending_mod_list = config.get("pending_modifications", [])
    # exit if no pending modifications
    if not pending_mod_list:
        print("No pending modifications to apply.")
        return

    # handle modifications
    item_number_or_all_str = args.item_number_or_all
    items_to_process = []
    if item_number_or_all_str.lower() == "all":
        items_to_process = [
            (idx, item)
            for idx, item in enumerate(pending_mod_list)
            if time.time() >= item.get("unlock_timestamp", 0)
        ]
        if not items_to_process:
            print("No pending modifications are ready to be applied.")
            return
    else:
        try:
            item_index = int(item_number_or_all_str) - 1
            if not (0 <= item_index < len(pending_mod_list)):
                print("Error: Invalid index.",
                      file=sys.stderr)
                return
            if time.time() < pending_mod_list[item_index].get("unlock_timestamp", 0):
                print("Error: This modification is not yet unlocked.",
                      file=sys.stderr)
                return
            items_to_process = [(item_index, pending_mod_list[item_index])]
        except ValueError:
            print("Error: Invalid input.",
                  file=sys.stderr)
            return

    changes_applied_count = 0
    indices_to_remove = []

    for idx, pending_item in items_to_process:
        logger.info(f"Applying pending modification (ID: {pending_item.get('id')})...")
        if _apply_config_modification(config, pending_item):
            print(
                f"Successfully applied pending modification: {pending_item.get('action')} for {pending_item.get('payload', {}).get('name')}"
            )
            changes_applied_count += 1
            indices_to_remove.append(idx)

            if pending_item.get("action") == "remove_app":
                app_name = pending_item.get("payload", {}).get("name")
                if app_name:
                    usage_data = load_json(USAGE_DATA_PATH, read_only=False)
                    if app_name in usage_data:
                        usage_data.pop(app_name)
                        save_json(USAGE_DATA_PATH, usage_data)
                        print(f"Cleaned up usage data for '{app_name}'.")
        else:
            logger.error(
                f"Failed to apply pending modification (ID: {pending_item.get('id')})."
            )
            print(
                f"Error: Failed to apply pending modification (ID: {pending_item.get('id')})."
            )

    if changes_applied_count > 0:
        for item_idx in sorted(indices_to_remove, reverse=True):
            config["pending_modifications"].pop(item_idx)
        save_json(CONFIG_FILE_PATH, config)
        print(
            f"\nSuccessfully applied and removed {changes_applied_count} item(s) from the pending queue."
        )


def _apply_config_modification(config, modification_to_apply):
    """
    Applies a configuration modification to the config dictionary in memory.
    :param config: the config dict read from config file
    :param modification_to_apply: the modification to apply
    :return: True if the modification is applied, False otherwise
    """
    action = modification_to_apply["action"]
    payload = modification_to_apply["payload"]
    apps = config.get("applications", [])

    exists_app = check_exists_app(payload["name"], config)
    # add
    if action == "add_app":
        if exists_app:
            print(
                f"Error: Application '{payload['name']}' already exists.",
                file=sys.stderr,
            )
            return False
        apps.append(payload)

    # remove
    elif action == "remove_app":
        if not exists_app:
            print(
                f"Error: Application '{payload['name']}' not found in config.",
                file=sys.stderr,
            )
            return False
        config["applications"] = [
            app for app in apps if app["name"] != payload["name"]
        ]

    # update
    elif action == "update_app":
        if not exists_app:
            print(
                f"Error: Application '{payload['name']}' not found for update.",
                file=sys.stderr,
            )
            return False

        for app in apps:
            if app["name"] == payload["name"]:
                app.update({k: v for k, v in payload.items() if v is not None})
                break

    # config delay
    elif action == "set_config_delay":
        config["enable_config_modification_delay"] = payload.get("enable", False)
        config["config_modification_delay_seconds"] = payload.get("delay_seconds", 0)


    else:
        print(f"Error: Unknown action '{action}'.", file=sys.stderr)
        return False

    return True

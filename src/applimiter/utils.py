# AppLimiter/src/applimiter/utils.py


"""
Store JSON processing functions and some check functions
"""

import logging
import json
import os
import time
import subprocess

logger = logging.getLogger(__name__)


def save_json(pathname, data):
    """
    Save data to a json file and change the permissions if current user is the root user
    :param pathname: the pathname to save json file to

    :param data: the data to save
    :return: None
    """
    try:
        # mkdir if needed
        os.makedirs(os.path.dirname(pathname), exist_ok=True)
        tmp_pathname = pathname + ".tmp"

        # dump json file
        with open(tmp_pathname, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4, ensure_ascii=False)

        # change permissions if the user is root
        if os.getuid() == 0:
            try:
                os.chmod(tmp_pathname, 0o644)
            except OSError as e_chmod:
                logger.warning(
                    f"Could not change permissions to {tmp_pathname}: {e_chmod}"
                )

        # rename the file
        os.rename(tmp_pathname, pathname)
        logger.debug(f"JSON data successfully saved to {pathname}")
    except IOError as io_err:
        logger.error(f"Failed to save JSON data to {pathname}: {io_err}")
    except Exception as global_err:
        logger.error(
            f"An unexpected error occurred while saving JSON data to {pathname}: {global_err}"
        )


def load_json(pathname, default_data=None, read_only=False):
    """
    Load data from a JSON file, creating from the default data if it doesn't exist.

    :param pathname: the pathname to load json data
    :param default_data: the default data to load if the file doesn't exist
    :param read_only: create a new json file with default data if False
    :return: the loaded data or default_data
    """
    if default_data is None:
        default_data = {}

    try:
        # if file not exists, create json file and use default data
        if not os.path.exists(pathname):
            if read_only:
                logger.info(f"File {pathname} not found, returning default data.")
                return default_data

            logger.info(f"File {pathname} not found, creating a default one.")
            save_json(pathname, default_data)
            return default_data
        # if file exists, load data
        with open(pathname, "r", encoding="utf-8") as f:
            return json.load(f)
    except (IOError, json.JSONDecodeError) as e:
        # try to load the data again
        logger.warning(f"Failed to read JSON file {pathname} (retrying): {e}")
        time.sleep(0.1)
        if os.path.exists(pathname) and os.path.getsize(pathname) > 0:
            try:
                with open(pathname, "r", encoding="utf-8") as f:
                    return json.load(f)
            except (IOError, json.JSONDecodeError) as e2:
                logger.error(f"Failed to read JSON file {pathname} again: {e2}")
        # if fails again, use the default data
        if read_only:
            logger.warning("Returning default data")
            return default_data
        logger.warning("Create and use default data.")
        save_json(pathname, default_data)
        return default_data


def check_dependencies():
    """
    check all dependencies needed

    :return: True if all dependencies are installed, False otherwise
    """
    dependencies = ["zenity"]
    missing_dependencies = []
    # check dependencies
    for dependency in dependencies:
        try:
            # use which to check if the dependency is met
            subprocess.run(
                ["which", dependency], check=True, capture_output=True, text=True
            )
        except subprocess.CalledProcessError:
            missing_dependencies.append(dependency)
    # record a log if some dependency is missing
    if missing_dependencies:
        logger.error(
            f"Missing dependencies: {', '.join(missing_dependencies)}\n"
            f"Please install dependencies."
        )
        return False

    return True


def check_exists_app(app_name: str, config: dict) -> bool:
    """
    Check if an application exists in the configuration
    :param app_name: the application name
    :param config: config dict read from config file
    :return: True if the app exists, False otherwise
    """
    return any(app["name"] == app_name for app in config.get("applications", []))


def check_privilege(args):
    """
    Check if has the permission to execute the command
    :param args: argparse namespace
    :return: True if the permission is satisfied, False otherwise
    """
    is_root = os.getuid() == 0
    # check if needs root
    needs_root = args.command in [
        "add",
        "remove",
        "update",
        "config-delay",
        "update-usage",
    ] or (args.command == "pending" and args.pending_action in ["clear", "apply"])
    if needs_root and not is_root:
        return False
    return True
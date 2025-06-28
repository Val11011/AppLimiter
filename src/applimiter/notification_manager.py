# AppLimiter/src/applimiter/notification_manager.py

"""
Store functions used to send notifications to users
"""

import os
import pwd
import logging
import subprocess

import psutil

# get a logger
logger = logging.getLogger(__name__)


def get_desktop_users_with_display_info():
    """
    Find all active desktop users and their display information
    Tries to find DISPLAY and XAUTHORITY to allow notifications from a root process.
    :return: None
    """

    def get_active_users():
        """
        trying to find all active users using command 'users' and 'who'
        :return: list of active users
        """
        # define active users set
        active_users = set()

        # Try to get active users from the 'users' command, with 'who' as a fallback.
        try:
            users_output = subprocess.run(
                ["users"], capture_output=True, text=True, check=True
            )
            active_users.update(users_output.stdout.strip().split())
        except (subprocess.CalledProcessError, FileNotFoundError):
            logger.warning(
                "Could not execute 'users' command to get active desktop users, trying 'who'. "
            )
            try:
                who_output = subprocess.run(
                    ["who"], capture_output=True, text=True, check=True
                )
                for line in who_output.stdout.strip().split("\n"):
                    if line.strip():
                        active_users.add(line.split()[0])
            except (subprocess.CalledProcessError, FileNotFoundError):
                logger.error(
                    "Could not execute 'who' command to get active desktop users. "
                )
                return []

        if not active_users:
            logger.warning("No active desktop users found.")
            return []

        return list(active_users)

    active_users = get_active_users()
    desktop_users_info = []
    logger.debug(f"Detected initial active usernames: {active_users}")

    for username in active_users:
        try:
            pwnam = pwd.getpwnam(username)
            uid = pwnam.pw_uid
            user_home = pwnam.pw_dir

            # Only process regular users (UID >= 1000)
            if uid < 1000:
                logger.debug(
                    f"Skipping system user {username} (UID: {uid}) for having uid less than 1000"
                )
                continue

            display = None
            xauthority = None

            # iterate through this list of common session process to find display and xauthority
            session_processes_to_check = [
                "gnome-shell",
                "cinnamon-session-binary",
                "kwin_x11",
                "plasma_session",
                "xfce4-session",
                "lxsession",
            ]
            try:
                for process in psutil.process_iter(
                    ["pid", "name", "username", "environ"]
                ):
                    info = process.info
                    # Check if the process belongs to our target user and is a known session process
                    if (
                        info["username"] == username
                        and info["name"] in session_processes_to_check
                    ):
                        # Successfully found a desktop session process, read its environment
                        logger.debug(
                            f"Found session process '{info['name']}' (PID: {info['pid']}) for user {username}"
                        )

                        # Directly get DISPLAY and XAUTHORITY from the process's actual environment
                        display = info["environ"].get("DISPLAY")
                        xauthority = info["environ"].get("XAUTHORITY")

                        # If we found the display, we can stop searching
                        if display:
                            logger.info(
                                f"Dynamically found DISPLAY='{display}' for user {username}."
                            )
                            break

            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                # This might happen if a process terminates while we are iterating
                logger.warning(
                    "A process vanished during environment scan, this is usually harmless."
                )
                pass  # Ignore and continue

            # If we failed to find the display dynamically, fall back to the ":0"
            if not display:
                logger.warning(
                    f"Could not dynamically find DISPLAY for {username}, using ':0'."
                )
                display = ":0"

            # If we failed to find the xauthority dynamically, fall back to searching the file list
            if not xauthority:
                logger.warning(
                    f"Could not dynamically find XAUTHORITY for {username}, using a list of commonly used"
                    f"files to search for XAUTHORITY."
                )
                xauthority_paths_to_check = [
                    os.path.join(user_home, ".Xauthority"),
                    f"/run/user/{uid}/gdm/Xauthority",  # For GDM
                    f"/var/run/lightdm/{username}/xauthority",  # For LightDM
                ]

                for xpath_candidate in xauthority_paths_to_check:
                    # Since the daemon runs as root, it should have permission to check these paths.
                    if os.path.exists(xpath_candidate):
                        xauthority = xpath_candidate
                        logger.debug(
                            f"Found Xauthority for user {username} at: {xauthority}"
                        )
                        break
            # check if xauthority is found
            if not xauthority:
                logger.warning(
                    f"Could not find a specific Xauthority file for user {username}. Zenity might fail."
                )

            user_data = {
                "username": username,
                "uid": uid,
                "display": display,
                "xauthority": xauthority,
                "home": user_home,
            }
            logger.debug(f"Collected desktop info for user {username}: {user_data}")
            desktop_users_info.append(user_data)

        except KeyError:
            logger.warning(
                f"User {username} not found in password database (pwd.getpwnam failed)."
            )
        except Exception as e_user_info:
            logger.error(
                f"Error getting desktop info for user {username}: {e_user_info}"
            )

    if not desktop_users_info:
        logger.warning(
            "Ultimately failed to collect desktop information for any eligible user."
        )
    return desktop_users_info


def send_desktop_notification_zenity(title, message, user_info, dialog_type="--info"):
    """
    Sends a desktop notification to a specific user using Zenity.
    """
    username = user_info.get("username")
    display = user_info.get("display")
    xauthority = user_info.get("xauthority")

    if not username or not display:
        logger.warning(
            f"Cannot send Zenity notification due to incomplete user info for {username or 'unknown user'}."
        )
        return

    logger.info(f"Attempting to send Zenity notification to user {username}: [{title}]")

    command = [
        "zenity",
        dialog_type,
        "--title",
        title,
        "--text",
        message,
        "--no-markup",
        "--timeout=10",  # Dialog auto-closes after 10 seconds
    ]

    # Set up the environment for the user's display
    env = os.environ.copy()
    env["DISPLAY"] = display
    if xauthority and os.path.exists(xauthority):
        env["XAUTHORITY"] = xauthority
        logger.debug(f"Using XAUTHORITY for Zenity: {xauthority}")
    else:
        # If no Xauthority file was found, still try; DISPLAY might be enough on some systems.
        logger.debug(
            f"No XAUTHORITY file found or used (checked path: {xauthority}). Relying on DISPLAY."
        )

    try:
        # If running as root, use sudo to run the command as the target user
        if os.geteuid() == 0:
            full_command = ["sudo", "-u", username] + command
        else:
            full_command = command

        logger.debug(f"Executing Zenity command: {' '.join(full_command)}")
        logger.debug(
            f"Zenity environment: DISPLAY={env.get('DISPLAY')}, XAUTHORITY={env.get('XAUTHORITY')}"
        )

        result = subprocess.run(
            full_command,
            env=env,
            capture_output=True,
            text=True,
            timeout=15,  # Command execution timeout
        )

        # Zenity return codes can vary. 0, 1, or 5 often indicate the dialog was shown.
        if result.returncode in [0, 1, 5]:
            logger.info(
                f"Zenity dialog likely shown to user {username} (return code: {result.returncode})."
            )
            if result.stdout.strip():
                logger.debug(f"Zenity stdout: {result.stdout.strip()}")
            if result.stderr.strip():
                logger.debug(f"Zenity stderr: {result.stderr.strip()}")
        else:
            logger.warning(
                f"Zenity command failed for user {username} (return code: {result.returncode}): STDERR: {result.stderr.strip()} STDOUT: {result.stdout.strip()}"
            )

    except subprocess.TimeoutExpired:
        logger.warning(
            f"Zenity command timed out for user {username}. The dialog might have been displayed."
        )
    except FileNotFoundError:
        logger.error(
            "'zenity' command not found. Please ensure it is installed (e.g., 'sudo apt install zenity')."
        )
    except Exception as e:
        logger.error(
            f"An unexpected error occurred while sending notification to {username}: {e}"
        )

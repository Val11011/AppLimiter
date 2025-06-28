# AppLimiter/src/applimiter/process_handler.py

"""
Store functions to to handle processes
"""

import logging
import psutil

from applimiter.constants import PROCESS_TERMINATING_PATIENCE

logger = logging.getLogger(__name__)


def get_process_pids(keywords):
    """
    Based on the keywords provided, return a list of process pids that match the keywords.

    :param keywords: the keywords used to determine the pids
    :return: a list of pids
    """
    pids = set()
    for process in psutil.process_iter(attrs=["pid", "name", "cmdline"]):
        try:
            # get info
            info = process.info
            # get name
            name = info.get("name", "")
            name = name.lower()
            # get cmdline
            cmdline = info.get("cmdline")
            cmdline_str = " ".join(cmdline) if cmdline else ""
            cmdline_str = cmdline_str.lower()
            # match keywords
            for keyword in keywords:
                keyword = keyword.lower()
                if keyword in cmdline_str or keyword in name:
                    pids.add(process.pid)
                    break
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            # ignore processes already terminated or not accessible
            pass
    return list(pids)


def terminate_process(pid, app_name):
    """
    terminate a process using pid

    :param pid: the process id
    :param app_name: the app name
    :return: None
    """
    try:
        # get process object
        process = psutil.Process(pid)
        # terminate the process
        logger.info(f"Terminating process {pid} for app {app_name}.")
        process.terminate()
        try:
            # wait till termination completed
            process.wait(PROCESS_TERMINATING_PATIENCE)
            logger.info(f"Process {pid}terminated successfully.")
        except psutil.TimeoutExpired:
            # kill the process if timeout
            logger.warning(
                f"Process {pid} did not terminate within {PROCESS_TERMINATING_PATIENCE} seconds, forcing killing."
            )
            process.kill()

    except psutil.NoSuchProcess:
        logger.info(f"Process {pid} no longer exists.")
    except psutil.AccessDenied:
        logger.warning(f"Process {pid} is not accessible.")
    except Exception as e:
        logger.error(
            f"An unexpected error occurred while terminating process {pid} for app {app_name}: {e}"
        )

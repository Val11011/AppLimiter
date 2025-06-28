import logging
import subprocess
import time
import psutil

# Configure logging to see the output from the functions
logging.basicConfig(
    level=logging.INFO, format="%(levelname)s: [%(name)s] - %(message)s"
)

# Import the functions we want to test
import rewrited_app_limiter.process_handler as process_handler

# --- Test Configuration ---
TEST_APP_COMMAND = "code"
TEST_APP_KEYWORDS = ["code", "vscode"]


def run_tests():
    """Runs all test cases for process_handler.py"""
    print("========= Starting a test run for process_handler.py =========\n")

    try:
        # --- Test 1: Launch VS Code for testing ---
        print("--- Test 1: Launching VS Code for testing ---")
        # Start the process and immediately detach from the launcher process.
        # We don't need its PID anymore.
        subprocess.Popen([TEST_APP_COMMAND, "--new-window"])
        print("VS Code launch command issued. Waiting for it to initialize...")
        time.sleep(
            5
        )  # Give it a few seconds to fully start up and create its main processes.

        # --- Test 2: Verify that get_process_pids finds the running VS Code ---
        print("\n--- Test 2: Testing get_process_pids ---")
        print(f"Searching for processes with keywords: {TEST_APP_KEYWORDS}")
        pids_before_termination = process_handler.get_process_pids(TEST_APP_KEYWORDS)

        print(
            f"Found {len(pids_before_termination)} running VS Code processes: {pids_before_termination}"
        )
        assert pids_before_termination, (
            "FAILED: get_process_pids could not find any running VS Code processes!"
        )
        print("✅ PASSED: get_process_pids successfully found running processes.\n")

        # --- Test 3: Test terminate_process on all found PIDs ---
        print("\n--- Test 3: Testing terminate_process ---")
        print(
            f"Attempting to terminate all {len(pids_before_termination)} found processes..."
        )
        for pid in pids_before_termination:
            # Correctly calling the renamed function
            process_handler.terminate_process(pid, "VSCode (Test)")

        print("\nTermination commands sent. Waiting a moment for processes to exit...")
        time.sleep(3)  # Give a moment for all processes to fully terminate.

        # --- Test 4: Final Verification ---
        print("\n--- Test 4: Verifying complete shutdown ---")
        pids_after_termination = process_handler.get_process_pids(TEST_APP_KEYWORDS)
        print(
            f"Searching again... Found {len(pids_after_termination)} remaining processes: {pids_after_termination}"
        )

        assert not pids_after_termination, (
            f"FAILED: {len(pids_after_termination)} VS Code processes still remain after termination attempt!"
        )
        print("✅ PASSED: All VS Code processes have been successfully terminated.\n")

    except AssertionError as e:
        print(f"\n🔥🔥🔥 A TEST FAILED! 🔥🔥🔥\n{e}")
    except Exception as e:
        print(f"\nAn unexpected error occurred during the test: {e}")
    finally:
        # Cleanup: In case of failure, try one last time to kill any remaining processes.
        # This is a safety net.
        remaining_pids = process_handler.get_process_pids(TEST_APP_KEYWORDS)
        if remaining_pids:
            print("\n--- Cleanup: Forcibly killing leftover processes... ---")
            for pid in remaining_pids:
                try:
                    psutil.Process(pid).kill()
                except psutil.Error:
                    pass  # Ignore if already gone
            print("Cleanup complete.")

    print("========= All process_handler tests completed successfully! =========\n")


if __name__ == "__main__":
    input(
        "WARNING: This test will launch and then terminate ALL Visual Studio Code instances. Please save your work and close any VS Code windows. Press Enter to continue..."
    )
    run_tests()

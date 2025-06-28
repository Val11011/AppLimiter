# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.0.0] - 2025-06-28

This is the first official public release of AppLimiter.

### Added

- **Core Functionality**:
    - `daemon`: A robust background service that runs as `root` to monitor and track application usage against daily and weekly time limits.
    - `cli`: A powerful command-line interface to manage all aspects of the application.

- **Key Features**:
    - **Differentiated Time Limits**: Set separate usage limits for weekdays and weekends.
    - **Process Management**: Intelligently finds processes by keywords and terminates them gracefully (with a `kill` fallback) after a grace period.
    - **Desktop Notifications**: Uses `zenity` to send warnings and alerts to the active user's desktop, even when run as `root`.
    - **Configuration Delay**: An optional safety feature that queues sensitive changes (like increasing time limits or removing apps) for a configurable time period before they can be applied.
    - **Pending Queue Management**: Full CLI support for listing, clearing, and applying pending configuration changes.
    - **Manual Usage Adjustment**: A command to manually add or remove usage time for any application.

- **Project Structure & Tooling**:
    - **Professional `src`-layout**: The project is structured as a standard Python package, separating source code from tests and metadata.
    - **Automated Installer (`install.sh`)**: A user-friendly installation script that deploys the application, sets up system directories, and installs both a `systemd` service and a system-wide `applimiter` command.
    - **Command-Line Shim Script**: Ensures the `applimiter` command works seamlessly for both regular users and with `sudo`.
    - **Comprehensive Test Suite**: A full test suite using `pytest` and `pytest-mock` to ensure code quality and stability.
    - **Complete Documentation**: A `README.md` file with clear installation and usage instructions.
    - **`pyproject.toml`**: Manages project metadata and dependencies.
    - **`LICENSE`**: An MIT License is included to clarify open-source usage rights.
    - **`.gitignore`**: Configured to keep the repository clean.
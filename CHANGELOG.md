# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Fixed
- **Corrected `remove` command logic**: The `remove` command now correctly cleans up usage data from `usage_data.json` in addition to removing the application from `config.json`, preventing orphaned data.
- **Restored `pending apply` functionality**: Fixed a critical bug where the command dispatch logic incorrectly bypassed the `pending` command, making it impossible to apply pending changes. The command dispatcher in `cli.py` has been refactored for robustness.

### Changed
- The notification logic in `daemon.py` no longer sends a 10-minute warning. The `notif_*_10_sent` flags have been removed from the data structure and reset logic accordingly.

---

## [1.0.0] - 2025-06-17

This marks the first stable release.

### Added
- A modular package structure under the `app_limiter/` directory to separate concerns like CLI, daemon logic, and utilities.
- A `CHANGELOG.md` file to document project changes over time.
- A `main.py` as the single, clean entry point for the application.
- A template for the `app_limiter.service` file within the project directory.

### Changed
- **Refactored** the entire project from a single `app_limiter.py` script into a professional, modular Python package.
- **Internationalized** all user-facing strings in the command-line interface and daemon logs from Chinese to English.
- The `systemd` service file now points to the new `main.py` entry point.
- The `__init__.py` file now exposes a clean public API for the package.

### Removed
- The monolithic `app_limiter.py` script has been replaced by the new package structure.
# AppLimiter

**AppLimiter is a powerful, self-hosted application usage manager for Linux desktops.**

It runs as a background service to monitor the time you spend on specific applications and
helps you enforce healthy digital habits by setting daily and weekly time limits. When a limit 
is approaching, it provides gentle desktop notifications, and when the time is up, it ensures the 
application is closed after a grace period.


---

## ✨ Key Features

- **Per-Application Limits**: Set individual time quotas for any application (e.g., games, social media, browsers).
- **Flexible Time Rules**:
    - **Differentiated Limits**: Define separate daily time limits for weekdays (Mon-Fri) and weekends (Sat-Sun).
    - **Weekly Cap**: Enforce a total weekly usage limit.
- **Intelligent Notification System**: Uses `zenity` to display native desktop notifications.
    - **5-Minute Warning**: Get an alert when you are close to reaching a limit.
    - **Grace Period**: Receive a final warning when a limit is hit, with a 5-minute grace period before the app is terminated.
- **Robust Background Service**: Runs as a `systemd` service, reliably started after user login to avoid system boot race conditions.
- **Secure by Design**:
    - **Configuration Delay**: An optional safety feature that queues sensitive changes (like increasing time limits) for a 5-minute delay before they can be applied.
    - **Root Operation**: The daemon runs as `root` to monitor and manage any user process, while notifications are safely displayed on the correct user's desktop.
- **Clean Command-Line Interface**: A simple and powerful CLI to manage all your settings.

---

## ⚙️ Installation

This section guides you through installing AppLimiter as a system-wide service.

### Prerequisites

Ensure you have the following dependencies installed on your system:

- `python3`
- A Python package installer like `pip` or `uv`
- `psutil` (Python library, will be handled by the installer)
- `zenity` (for desktop notifications)

You can typically install `zenity` on Debian/Ubuntu-based systems with:
```bash
sudo apt-get update && sudo apt-get install zenity
```
### Standard Installation
This is the recommended method for most users.
1. Clone the Repository
  ```bash
  git clone https://github.com/your-username/AppLimiter.git
  cd AppLimiter
  ```

2. Run the Installer Script
  Execute the provided installation script with sudo. This will:
  * deploy the application to /opt/AppLimiter, 
  * Create configuration and data directories.
  * Install the systemd service for background operation.
  * Create a system-wide command applimiter in /usr/local/bin.
  ```bash
  sudo chmod +x ./install.sh
  sudo ./install.sh
  ```

## 🚀 Usage (Command-Line Interface)

All configuration-changing commands require sudo.

### Add a New Application
```bash
sudo applimiter add Steam --keywords steam.sh "Proton" -dw 60 -dW 120 --weekly 500
```

### Check Usage Status
```bash
applimiter status
```

### List All Configured Apps
```bash
applimiter list
```

### Remove an Application
```bash
sudo applimiter remove Steam
```

### Enable the 5-Minute Configuration Delay
```bash
sudo applimiter config-delay enable --minutes 5
```

### View and Apply Pending Changes
#### See what's waiting
```bash
applimiter pending list
```

#### Apply all unlocked changes
```bash
sudo applimiter pending apply all
```

#### See All Commands
```bash
applimiter --help
```

## License
This project is licensed under the MIT License. See the LICENSE file for details.

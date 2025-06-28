#!/bin/bash

# ==============================================================================
# AppLimiter Installation Script (Corrected Version)
# ==============================================================================
# This script handles the system-wide installation of AppLimiter, fully
# compatible with the src-layout project structure.
# ==============================================================================

# Exit immediately if a command exits with a non-zero status.
set -e

# --- Configuration Variables ---
readonly APP_NAME="AppLimiter"
readonly SOURCE_PACKAGE_NAME="applimiter"
readonly SOURCE_DIR="src"
readonly INSTALL_DIR="/opt/${APP_NAME}"
readonly SERVICE_NAME="applimiter.service"
readonly CONFIG_DIR="/etc/${APP_NAME}"
readonly DATA_DIR="/var/lib/${APP_NAME}"


# --- Main Installation Logic ---

main() {
    echo "Starting ${APP_NAME} installation..."

    # 1. Root Privilege Check
    # --------------------------------------------------------------------------
    if [ "$(id -u)" -ne 0 ]; then
        echo "Error: This script must be run with sudo or as the root user." >&2
        echo "Please run: sudo ./install.sh" >&2
        exit 1
    fi

    # 2. Deploy Application Code to /opt
    # --------------------------------------------------------------------------
    echo "--> Deploying application code to ${INSTALL_DIR}..."

    if [ -d "${INSTALL_DIR}" ]; then
        echo "    An existing installation was found. Removing it first."
        rm -rf "${INSTALL_DIR}"
    fi

    mkdir -p "${INSTALL_DIR}"

    echo "    Copying package from '${SOURCE_DIR}/${SOURCE_PACKAGE_NAME}'..."
    cp -r "${SOURCE_DIR}/${SOURCE_PACKAGE_NAME}" "${INSTALL_DIR}/"
    echo "    Code deployment complete."


    # 3. Create Configuration and Data Directories
    # --------------------------------------------------------------------------
    echo "--> Creating system directories..."

    if [ ! -d "${CONFIG_DIR}" ]; then
        mkdir -p "${CONFIG_DIR}"
        echo "    Created configuration directory: ${CONFIG_DIR}"
    else
        echo "    Configuration directory already exists. Skipping."
    fi

    if [ ! -d "${DATA_DIR}" ]; then
        mkdir -p "${DATA_DIR}"
        echo "    Created data directory: ${DATA_DIR}"
    else
        echo "    Data directory already exists. Skipping."
    fi

    # 4. Install the systemd Service File
    # --------------------------------------------------------------------------
    echo "--> Installing systemd service..."

    cat > "/etc/systemd/system/${SERVICE_NAME}" << EOF
[Unit]
Description=AppLimiter Daemon
After=network.target

[Service]
Type=simple

ExecStart=/usr/bin/env python3 -m applimiter.main daemon --interval 30

WorkingDirectory=/opt/AppLimiter
User=root
Restart=on-failure
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF
    echo "    Service file created at /etc/systemd/system/${SERVICE_NAME}"

    # 5. Install the Command-Line Shim Script
    # --------------------------------------------------------------------------
    echo "--> Installing command-line shim script to /usr/local/bin..."

    # Copy our shim script to a directory that is in the system's PATH
    cp "applimiter.sh" "/usr/local/bin/applimiter"

    # Ensure it is executable by everyone
    chmod +x "/usr/local/bin/applimiter"
    echo "    Command 'applimiter' is now available system-wide."

    # 6. Reload systemd Daemon
    # --------------------------------------------------------------------------
    echo "--> Reloading systemd daemon to recognize the new service..."
    systemctl daemon-reload


    # --- Installation Complete ---
    # --------------------------------------------------------------------------
    echo
    echo "================================================="
    echo " ${APP_NAME} installation completed successfully! "
    echo "================================================="
    echo
    echo "WHAT'S NEXT?"
    echo "1. Configure your apps by editing the file:"
    echo "   ${CONFIG_DIR}/config.json"
    echo
    echo "2. Set up your desktop's autostart utility to run the following command on login:"
    echo "   sudo systemctl start ${SERVICE_NAME}"
    echo
    echo "   (For detailed instructions, please refer to the README.md file.)"
    echo
}

# --- Script Entrypoint ---
main "$@"
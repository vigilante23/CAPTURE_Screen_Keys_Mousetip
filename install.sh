#!/bin/bash
#
# Installation Script for My PyQt Application
#
# This script installs My PyQt Application, configures auto-start, and sets up shortcuts.
# Usage: ./install.sh
#

# Installation directory for your application (system-wide or user-specific)
INSTALL_DIR="$HOME/myapp"

# Path to your application's tarball (adjust as needed)
SCRIPT_LOCATION="$(cd "$(dirname "$0")" && pwd)"
TAR_FILE="$SCRIPT_LOCATION/Mousetip.tar.gz"

# Name of your application
APP_NAME="Mousetip"

# Create the installation directory
mkdir -p "$INSTALL_DIR"

# Extract your application's files from the tarball to the installation directory
tar -xzf "$TAR_FILE" -C "$INSTALL_DIR"

# Create the .desktop file for auto-start in the user's ~/.config/autostart/ directory
AUTOSTART_DIR="$HOME/.config/autostart"
DESKTOP_FILE="$AUTOSTART_DIR/mousetip.desktop"

echo "[Desktop Entry]
Name=$APP_NAME
Exec=nohup $INSTALL_DIR/Mousetip/Mousetip &
Terminal=false
Type=Application
X-GNOME-Autostart-enabled=true" > "$DESKTOP_FILE"

# Set permissions for the .desktop file to make it executable
chmod +x "$DESKTOP_FILE"

# Inform the user about the installation progress
echo "Installation completed"

nohup "$INSTALL_DIR/Mousetip/Mousetip"
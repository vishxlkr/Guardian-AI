#!/bin/bash
# Personal Security Software - Linux Setup Script
# For Ubuntu/Debian based systems

echo "========================================"
echo "Personal Security Software Setup (Linux)"
echo "========================================"
echo ""

# Check if running as root
if [ "$EUID" -eq 0 ]; then 
   echo "Please do not run this script as root"
   exit 1
fi

# Function to check if command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Check Python installation
echo "Checking Python installation..."
if ! command_exists python3; then
    echo "ERROR: Python 3 is not installed"
    echo "Please install Python 3.8 or higher:"
    echo "  sudo apt-get update"
    echo "  sudo apt-get install python3 python3-pip python3-dev"
    exit 1
fi

PYTHON_VERSION=$(python3 -c 'import sys; print(".".join(map(str, sys.version_info[:2])))')
echo "Found Python $PYTHON_VERSION"

# Check Python version
REQUIRED_VERSION="3.8"
if [ "$(printf '%s\n' "$REQUIRED_VERSION" "$PYTHON_VERSION" | sort -V | head -n1)" != "$REQUIRED_VERSION" ]; then
    echo "ERROR: Python $REQUIRED_VERSION or higher is required"
    exit 1
fi

# Install system dependencies
echo ""
echo "Installing system dependencies..."
echo "This will require your sudo password..."

# Update package list
sudo apt-get update

# Install required packages
PACKAGES="cmake build-essential python3-dev libboost-all-dev libgtk-3-dev"
PACKAGES="$PACKAGES libopenblas-dev liblapack-dev libx11-dev libatlas-base-dev"
PACKAGES="$PACKAGES v4l-utils libv4l-dev libxvidcore-dev libx264-dev"
PACKAGES="$PACKAGES libgtk2.0-dev pkg-config libavcodec-dev libavformat-dev libswscale-dev"
PACKAGES="$PACKAGES libtbb2 libtbb-dev libjpeg-dev libpng-dev libtiff-dev"

echo "Installing: $PACKAGES"
sudo apt-get install -y $PACKAGES

if [ $? -ne 0 ]; then
    echo "ERROR: Failed to install system dependencies"
    exit 1
fi

# Create directory structure
echo ""
echo "Creating directory structure..."
mkdir -p data/{logs,images/{intruders,authorized},models,backups}
mkdir -p config
mkdir -p src/{core,modules,plugins,utils}
mkdir -p scripts
mkdir -p tests

# Create __init__.py files
touch src/__init__.py
touch src/core/__init__.py
touch src/modules/__init__.py
touch src/plugins/__init__.py
touch src/utils/__init__.py
touch tests/__init__.py

echo "Directory structure created"

# Create virtual environment
echo ""
echo "Creating Python virtual environment..."
if [ ! -d "venv" ]; then
    python3 -m venv venv
    echo "Virtual environment created"
else
    echo "Virtual environment already exists"
fi

# Activate virtual environment
source venv/bin/activate

# Upgrade pip
echo ""
echo "Upgrading pip..."
pip install --upgrade pip setuptools wheel

# Install Python dependencies
echo ""
echo "Installing Python dependencies..."
echo "This may take several minutes..."

# Install dlib separately first (it can be problematic)
echo "Installing dlib (this may take a while)..."
pip install dlib || {
    echo "WARNING: dlib installation failed"
    echo "Trying alternative installation method..."
    pip install dlib-bin || {
        echo "ERROR: Could not install dlib"
        echo "Please install it manually or check build dependencies"
    }
}

# Install other requirements
pip install -r requirements.txt

if [ $? -ne 0 ]; then
    echo ""
    echo "ERROR: Failed to install some dependencies"
    echo ""
    echo "Common solutions:"
    echo "1. Install additional build tools:"
    echo "   sudo apt-get install python3-opencv"
    echo "2. Try installing packages individually"
    exit 1
fi

# Create default config if not exists
if [ ! -f "config/config.yaml" ]; then
    echo ""
    echo "Creating default configuration..."
    python3 -c "from src.core.config_manager import ConfigManager; ConfigManager()" || {
        echo "WARNING: Could not create default config"
    }
fi

# Check camera permissions
echo ""
echo "Checking camera access..."
if [ -e /dev/video0 ]; then
    echo "Camera device found at /dev/video0"
    
    # Check if user is in video group
    if ! groups | grep -q video; then
        echo "Adding user to video group for camera access..."
        sudo usermod -a -G video $USER
        echo "You need to log out and back in for camera access to work"
    fi
else
    echo "WARNING: No camera device found"
fi

# Test camera
echo ""
echo "Testing camera access..."
python3 -c "import cv2; cap = cv2.VideoCapture(0); print('Camera test:', 'OK' if cap.isOpened() else 'FAILED'); cap.release()" || {
    echo "WARNING: Camera test failed"
}

# Create desktop entry
echo ""
read -p "Create desktop shortcut? (y/n): " CREATE_DESKTOP
if [ "$CREATE_DESKTOP" = "y" ] || [ "$CREATE_DESKTOP" = "Y" ]; then
    DESKTOP_FILE="$HOME/.local/share/applications/personal-security.desktop"
    cat > "$DESKTOP_FILE" << EOF
[Desktop Entry]
Version=1.0
Type=Application
Name=Personal Security
Comment=Face recognition security software
Exec=$PWD/venv/bin/python $PWD/main.py run
Icon=security-high
Terminal=false
Categories=System;Security;
StartupNotify=true
EOF
    chmod +x "$DESKTOP_FILE"
    echo "Desktop shortcut created"
fi

# Create systemd service
echo ""
read -p "Install as systemd service? (y/n): " CREATE_SERVICE
if [ "$CREATE_SERVICE" = "y" ] || [ "$CREATE_SERVICE" = "Y" ]; then
    SERVICE_FILE="/etc/systemd/system/personal-security.service"
    
    sudo tee "$SERVICE_FILE" > /dev/null << EOF
[Unit]
Description=Personal Security Software
After=network.target

[Service]
Type=simple
User=$USER
WorkingDirectory=$PWD
Environment="PATH=$PWD/venv/bin:/usr/local/bin:/usr/bin:/bin"
ExecStart=$PWD/venv/bin/python $PWD/main.py run
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

    sudo systemctl daemon-reload
    echo "Service installed: personal-security.service"
    echo "To start: sudo systemctl start personal-security"
    echo "To enable on boot: sudo systemctl enable personal-security"
fi

# Setup face recognition
echo ""
echo "========================================"
echo "Face Recognition Setup"
echo "========================================"
echo ""
echo "Please add your authorized face for recognition."
echo ""
read -p "Enter your name: " USER_NAME
if [ ! -z "$USER_NAME" ]; then
    echo ""
    echo "Make sure you have good lighting and look directly at the camera."
    echo "The camera window will open. Press SPACE to capture, Q to quit."
    echo ""
    # This would need a face capture utility
    echo "TODO: Implement face capture for Linux"
    # python3 scripts/capture_face.py --name "$USER_NAME"
fi

# Display summary
echo ""
echo "========================================"
echo "Setup Complete!"
echo "========================================"
echo ""
echo "Installation summary:"
echo "- Python dependencies installed"
echo "- Directory structure created"
echo "- Configuration file created"

if groups | grep -q video; then
    echo "- Camera permissions configured"
else
    echo "- Camera permissions need configuration (logout required)"
fi

echo ""
echo "Next steps:"
echo "1. Activate virtual environment: source venv/bin/activate"
echo "2. Add authorized faces: python3 main.py add-face --name 'Name' --image 'photo.jpg'"
echo "3. Run the application: python3 main.py run"
echo ""
echo "For help: python3 main.py --help"
echo ""
echo "Note: Some features are Windows-specific and may not work on Linux"
echo "========================================"
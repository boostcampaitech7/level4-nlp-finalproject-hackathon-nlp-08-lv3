#!/bin/bash

# Exit on any error
set -e

echo "Starting installation process..."

# Set timezone to Asia/Seoul
echo "Setting timezone to Asia/Seoul..."
ln -sf /usr/share/zoneinfo/Asia/Seoul /etc/localtime

# Update package list
echo "Updating package list..."
apt-get update

# Install system dependencies
echo "Installing system dependencies..."
apt-get install -y python3-pip fonts-nanum

# Install Python packages
echo "Installing Python packages from requirements.txt..."
pip install -r requirements.txt

# Verify font installation
echo "Verifying font installation..."
if [ -f "/usr/share/fonts/truetype/nanum/NanumMyeongjo.ttf" ]; then
    echo "NanumMyeongjo font is successfully installed!"
else
    echo "Warning: NanumMyeongjo font file not found in expected location."
    echo "You might need to install it manually from https://hangeul.naver.com/font"
    exit 1
fi

echo "Installation completed successfully!"

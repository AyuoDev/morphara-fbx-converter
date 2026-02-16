#!/usr/bin/env bash
# Render build script - installs system dependencies

set -o errexit

# Install system packages
apt-get update
apt-get install -y assimp-utils

# Install Python dependencies
pip install --upgrade pip
pip install -r requirements.txt

echo "✓ Build complete"

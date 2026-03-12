#!/bin/bash

# OpenClaw Docker Setup Script (Docker already installed)
# This script sets up OpenClaw assuming Docker is already installed
# Tested on: Ubuntu 20.04+, Debian 10+

set -e

echo "======================================"
echo "OpenClaw Docker Setup Script"
echo "======================================"

# Check if running as root
if [ "$EUID" -ne 0 ]; then 
  echo "Please run this script with sudo"
  exit 1
fi

echo ""
echo "[1/2] Verifying Docker installation..."
docker --version
docker compose --version

echo ""
echo "[2/2] Cloning and starting OpenClaw..."
cd /opt

# Remove existing OpenClaw directory if it exists
if [ -d "openclaw" ]; then
  echo "Removing existing OpenClaw directory..."
  rm -rf openclaw
fi

git clone https://github.com/openclaw/openclaw.git
cd openclaw

# Create directories for OpenClaw config and workspace
echo "Setting up OpenClaw directories..."
mkdir -p /opt/openclaw-config
mkdir -p /opt/openclaw-workspace

# Export environment variables for Docker Compose
export OPENCLAW_CONFIG_DIR=/opt/openclaw-config
export OPENCLAW_WORKSPACE_DIR=/opt/openclaw-workspace

echo ""
echo "Starting OpenClaw with Docker..."

# Check if Dockerfile exists
if [ -f "Dockerfile" ]; then
  echo "Building OpenClaw Docker image from Dockerfile..."
  docker build -t openclaw:local .
else
  echo "No Dockerfile found. Checking docker-compose.yml..."
  if grep -q "build:" docker-compose.yml; then
    echo "Building with docker compose build..."
    docker compose build
  else
    echo "ERROR: Cannot find Dockerfile or build instructions in docker-compose.yml"
    echo "Please check the repository structure."
    exit 1
  fi
fi

# Run OpenClaw container
echo "Starting containers..."
docker compose up -d

echo ""
echo "======================================"
echo "Setup Complete!"
echo "======================================"
echo ""
echo "OpenClaw is now running."
echo "Check status with: cd /opt/openclaw && docker compose ps"
echo "View logs with: cd /opt/openclaw && docker compose logs -f"
echo "Stop with: cd /opt/openclaw && docker compose down"
echo ""

# OpenClaw Docker Setup

This script automates the installation of Docker and OpenClaw on a Linux server.

## Requirements
- Ubuntu 20.04+ (including Ubuntu 24) or Debian 10+
- Root or sudo access
- Internet connection
- Git installed

## Usage

1. Copy the script to your server:
```bash
scp setup-openclaw.sh user@your-server:/tmp/
```

2. SSH into your server:
```bash
ssh user@your-server
```

3. Make the script executable and run it:
```bash
chmod +x /tmp/setup-openclaw.sh
sudo /tmp/setup-openclaw.sh
```

## What the script does:
1. Updates system packages
2. Installs Docker and Docker Compose
3. Clones OpenClaw repository
4. Starts OpenClaw containers

## After installation:

Check if containers are running:
```bash
cd /opt/openclaw
docker compose ps
```

View logs:
```bash
docker compose logs -f
```

Stop OpenClaw:
```bash
docker compose down
```

## Troubleshooting

If you get permission errors:
```bash
sudo usermod -aG docker $USER
# Log out and back in
```

For different Linux distributions, you may need to modify the package manager commands (yum, dnf, etc.)

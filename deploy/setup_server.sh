#!/bin/bash
# Run once on a fresh Ubuntu 22.04 EC2 instance.
# Usage: bash deploy/setup_server.sh <github-repo-url> <soundlog-ai-repo-url>
#
# Before running:
#   1. Launch EC2 (Ubuntu 22.04, t3.medium recommended due to ML models)
#   2. Open ports 22 (SSH) and 80 (HTTP) in the security group
#   3. SSH into the instance: ssh -i your-key.pem ubuntu@<public-ip>
#   4. git clone your soundlog repo, then: bash deploy/setup_server.sh

set -e

SOUNDLOG_REPO="${1:-}"
SOUNDLOG_AI_REPO="${2:-}"
APP_DIR="/var/www/soundlog"
AI_DIR="/var/www/soundlog-ai"
DB_NAME="soundlog_stg"
DB_USER="soundlog"

echo "[1/9] Setting timezone to America/Los_Angeles..."
sudo timedatectl set-timezone America/Los_Angeles

echo "[2/9] Updating system packages..."
sudo apt-get update -y && sudo apt-get upgrade -y

echo "[3/9] Installing Python 3.9, PostgreSQL, Redis, Nginx, build tools..."
sudo apt-get install -y \
    python3 python3-venv python3-dev python3-pip \
    postgresql postgresql-contrib libpq-dev \
    redis-server \
    nginx \
    build-essential git \
    libjpeg-dev zlib1g-dev libpng-dev \
    libheif-dev libde265-dev

echo "[4/9] Setting up PostgreSQL..."
sudo systemctl enable postgresql
sudo systemctl start postgresql
sudo -u postgres psql -tc "SELECT 1 FROM pg_user WHERE usename='${DB_USER}'" | grep -q 1 || \
    sudo -u postgres psql -c "CREATE USER ${DB_USER} WITH PASSWORD 'changeme_in_env';"
sudo -u postgres psql -tc "SELECT 1 FROM pg_database WHERE datname='${DB_NAME}'" | grep -q 1 || \
    sudo -u postgres psql -c "CREATE DATABASE ${DB_NAME} OWNER ${DB_USER};"
sudo -u postgres psql -c "GRANT ALL PRIVILEGES ON DATABASE ${DB_NAME} TO ${DB_USER};"

echo "[5/9] Enabling Redis..."
sudo systemctl enable redis-server
sudo systemctl start redis-server

echo "[6/9] Creating app directories and cloning repos..."
sudo mkdir -p "$APP_DIR" "$AI_DIR"
sudo chown "$USER:$USER" "$APP_DIR" "$AI_DIR"

if [ -n "$SOUNDLOG_REPO" ] && [ ! -d "$APP_DIR/.git" ]; then
    git clone "$SOUNDLOG_REPO" "$APP_DIR"
elif [ -d "$APP_DIR/.git" ]; then
    echo "soundlog already cloned, skipping."
else
    echo "WARNING: No repo URL given. Manually copy soundlog to $APP_DIR."
fi

if [ -n "$SOUNDLOG_AI_REPO" ] && [ ! -d "$AI_DIR/.git" ]; then
    git clone "$SOUNDLOG_AI_REPO" "$AI_DIR"
elif [ -d "$AI_DIR/.git" ]; then
    echo "soundlog-ai already cloned, skipping."
else
    echo "WARNING: No repo URL given. Manually copy soundlog-ai to $AI_DIR."
fi

echo "[7/9] Installing systemd services..."
sudo cp "$APP_DIR/deploy/soundlog.service" /etc/systemd/system/soundlog.service
sudo cp "$APP_DIR/deploy/soundlog-celery.service" /etc/systemd/system/soundlog-celery.service
sudo systemctl daemon-reload
sudo systemctl enable soundlog soundlog-celery

echo "[8/9] Configuring Nginx..."
sudo cp "$APP_DIR/deploy/nginx.conf" /etc/nginx/sites-available/soundlog
sudo ln -sf /etc/nginx/sites-available/soundlog /etc/nginx/sites-enabled/soundlog
sudo rm -f /etc/nginx/sites-enabled/default
sudo nginx -t
sudo systemctl enable nginx
sudo systemctl restart nginx

echo "[9/9] Setting up soundlog-ai cron (midnight PST daily)..."
(crontab -l 2>/dev/null | grep -v soundlog-ai; \
 echo "0 0 * * * cd $AI_DIR && $AI_DIR/.venv/bin/python3 main.py >> $AI_DIR/cron.log 2>&1") \
 | crontab -

echo ""
echo "=== Server setup complete! ==="
echo ""
echo "Next steps:"
echo "  1. cp $APP_DIR/deploy/.env.stg.template $APP_DIR/.env"
echo "  2. Fill in all values in $APP_DIR/.env"
echo "  3. Update PostgreSQL password to match .env:"
echo "     sudo -u postgres psql -c \"ALTER USER soundlog WITH PASSWORD 'your_db_password';\""
echo "  4. cp $APP_DIR/deploy/.env.stg.template $AI_DIR/.env  (then fill in AI values)"
echo "  5. bash $APP_DIR/deploy/deploy.sh"

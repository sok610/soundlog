#!/bin/bash
# Run from the EC2 instance to deploy or update soundlog.
# Usage: bash deploy/deploy.sh
set -e

APP_DIR="/var/www/soundlog"
AI_DIR="/var/www/soundlog-ai"

echo "[1/7] Pulling latest code..."
cd "$APP_DIR"
git pull

echo "[2/7] Installing/updating Python dependencies..."
python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt

echo "[3/7] Collecting static files..."
python manage.py collectstatic --no-input

echo "[4/7] Running database migrations..."
python manage.py migrate

echo "[5/7] Seeding emotion data..."
python manage.py init_emotions

echo "[6/7] Setting up soundlog-ai virtualenv..."
cd "$AI_DIR"
if [ -f ".env" ]; then
    python3 -m venv .venv
    source .venv/bin/activate
    pip install --upgrade pip
    pip install -r requirements.txt 2>/dev/null || pip install \
        google-generativeai psycopg2-binary python-dotenv
    deactivate
else
    echo "WARNING: $AI_DIR/.env not found — skipping soundlog-ai setup."
fi

echo "[7/7] Restarting services..."
sudo systemctl restart soundlog
sudo systemctl restart soundlog-celery
sudo systemctl reload nginx

echo ""
echo "=== Deployment complete! ==="
EC2_IP=$(curl -s http://169.254.169.254/latest/meta-data/public-ipv4 2>/dev/null || echo "<your-ec2-ip>")
echo "App is live at: http://${EC2_IP}"
echo ""
echo "Check service status:"
echo "  sudo systemctl status soundlog"
echo "  sudo systemctl status soundlog-celery"
echo "  sudo journalctl -u soundlog -f"

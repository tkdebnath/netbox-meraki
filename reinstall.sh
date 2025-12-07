#!/bin/bash

set -e

echo "========================================="
echo "NetBox Meraki Plugin - Reinstall"
echo "========================================="
echo ""

# Get the directory where this script is located
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

echo "1. Activating NetBox virtual environment..."
source /opt/netbox/venv/bin/activate

echo "2. Uninstalling existing plugin..."
pip uninstall -y netbox-meraki || echo "Plugin not found, skipping uninstall"

echo "3. Removing Python cache files..."
cd "$SCRIPT_DIR"
find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
find . -type f -name "*.pyc" -delete 2>/dev/null || true

echo "4. Installing plugin from source..."
pip install .

echo "5. Applying migrations..."
cd /opt/netbox/netbox
python manage.py migrate netbox_meraki

echo "6. Collecting static files..."
python manage.py collectstatic --no-input

echo "7. Restarting NetBox services..."
sudo systemctl restart netbox netbox-rq

echo ""
echo "========================================="
echo "✓ Plugin completely reinstalled!"
echo "========================================="
echo ""
echo "Changes are now live in NetBox."

#!/bin/bash
# Complete cleanup and fresh installation of netbox-meraki plugin

set -e  # Exit on any error

echo "=========================================="
echo "NetBox Meraki Plugin - Complete Reinstall"
echo "=========================================="

cd /opt/netbox/netbox
source /opt/netbox/venv/bin/activate

# Step 1: Remove migration history
echo ""
echo "Step 1: Clearing migration history..."
python manage.py migrate netbox_meraki zero 2>/dev/null || echo "No migrations to reverse"

# Step 2: Manually drop all plugin tables
echo ""
echo "Step 2: Dropping all plugin tables from database..."
python manage.py dbshell << 'EOF'
DROP TABLE IF EXISTS netbox_meraki_scheduledjobtracker CASCADE;
DROP TABLE IF EXISTS netbox_meraki_reviewitem CASCADE;
DROP TABLE IF EXISTS netbox_meraki_syncreview CASCADE;
DROP TABLE IF EXISTS netbox_meraki_synclog CASCADE;
DROP TABLE IF EXISTS netbox_meraki_prefixfilterrule CASCADE;
DROP TABLE IF EXISTS netbox_meraki_sitenamerule CASCADE;
DROP TABLE IF EXISTS netbox_meraki_pluginsettings CASCADE;
DELETE FROM django_migrations WHERE app='netbox_meraki';
\q
EOF

# Step 3: Remove Python package
echo ""
echo "Step 3: Uninstalling Python package..."
pip uninstall -y netbox-meraki 2>/dev/null || echo "Package not installed"

# Step 4: Clean up old code
echo ""
echo "Step 4: Removing old plugin code..."
cd /opt/custom_plugin/
rm -rf ra_netbox_meraki/

# Step 5: Clone fresh code
echo ""
echo "Step 5: Cloning fresh code..."
git clone http://192.168.5.11/taranidebnath/ra_netbox_meraki.git
cd ra_netbox_meraki

# Step 6: Install plugin
echo ""
echo "Step 6: Installing plugin..."
pip install -e .

# Step 7: Apply migration
echo ""
echo "Step 7: Applying migration..."
cd /opt/netbox/netbox
python manage.py migrate netbox_meraki

# Step 8: Collect static files
echo ""
echo "Step 8: Collecting static files..."
python manage.py collectstatic --no-input

# Step 9: Restart services
echo ""
echo "Step 9: Restarting NetBox services..."
sudo systemctl restart netbox netbox-rq

echo ""
echo "=========================================="
echo "Installation complete!"
echo "=========================================="
echo ""
echo "Access the plugin at: Plugins → Meraki Dashboard Sync"

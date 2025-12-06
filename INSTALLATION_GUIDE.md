# Installation Guide for NetBox Meraki Plugin

This guide walks you through installing the NetBox Meraki plugin in your existing NetBox instance.

## Prerequisites

- NetBox 4.4.x installed and running
- Python 3.10 or higher
- Access to NetBox configuration files
- Meraki Dashboard API key

## Step 1: Get Your Meraki API Key

1. Log in to the Meraki Dashboard
2. Navigate to **Organization > Settings > Dashboard API access**
3. Enable API access if not already enabled
4. Click **Generate new API key**
5. Copy the API key (save it securely - it's only shown once)

## Step 2: Install the Plugin

### Option A: Install from Source (Development/Testing)

```bash
# Navigate to your NetBox installation directory
cd /opt/netbox

# Activate NetBox virtual environment
source venv/bin/activate

# Clone the plugin repository
cd /opt
git clone https://github.com/yourusername/netbox-meraki.git
cd netbox-meraki

# Install the plugin
pip install -e .
```

### Option B: Install from Package (Production)

```bash
# Activate NetBox virtual environment
cd /opt/netbox
source venv/bin/activate

# Install from pip (when published)
pip install netbox-meraki
```

## Step 3: Configure NetBox

### Method 1: Using Environment Variables (Recommended)

Edit your NetBox environment file (typically `/opt/netbox/netbox/netbox/.env` or create it):

```bash
# Add Meraki API key to .env file
echo "MERAKI_API_KEY=your-meraki-api-key-here" >> /opt/netbox/netbox/netbox/.env
```

Then update `/opt/netbox/netbox/netbox/configuration.py`:

```python
import os

# ... existing configuration ...

# Enable the plugin
PLUGINS = [
    'netbox_meraki',
    # ... other plugins ...
]

# Configure the plugin
PLUGINS_CONFIG = {
    'netbox_meraki': {
        # Get API key from environment variable
        'meraki_api_key': os.environ.get('MERAKI_API_KEY', ''),
        
        # Optional settings with defaults
        'meraki_base_url': 'https://api.meraki.com/api/v1',
        'sync_interval': 3600,  # seconds
        'auto_create_sites': True,
        'auto_create_device_types': True,
        'auto_create_device_roles': True,
        'auto_create_manufacturers': True,
        'default_device_role': 'Network Device',
        'default_manufacturer': 'Cisco Meraki',
    },
    # ... other plugin configs ...
}
```

### Method 2: Direct Configuration

Edit `/opt/netbox/netbox/netbox/configuration.py`:

```python
# Enable the plugin
PLUGINS = [
    'netbox_meraki',
    # ... other plugins ...
]

# Configure the plugin
PLUGINS_CONFIG = {
    'netbox_meraki': {
        # IMPORTANT: In production, use environment variables or secrets management
        'meraki_api_key': 'your-meraki-api-key-here',
        
        # Optional settings
        'meraki_base_url': 'https://api.meraki.com/api/v1',
        'sync_interval': 3600,
        'auto_create_sites': True,
        'auto_create_device_types': True,
        'auto_create_device_roles': True,
        'auto_create_manufacturers': True,
        'default_device_role': 'Network Device',
        'default_manufacturer': 'Cisco Meraki',
    },
    # ... other plugin configs ...
}
```

## Step 4: Run Database Migrations

```bash
cd /opt/netbox/netbox
source /opt/netbox/venv/bin/activate

# Run migrations
python manage.py migrate netbox_meraki

# Expected output:
# Running migrations:
#   Applying netbox_meraki.0001_initial... OK
#   Applying netbox_meraki.0002_add_settings_and_site_rules... OK
#   Applying netbox_meraki.0003_add_sync_review... OK
```

## Step 5: Collect Static Files

```bash
cd /opt/netbox/netbox
python manage.py collectstatic --no-input
```

## Step 6: Restart NetBox Services

```bash
# For systemd-managed NetBox
sudo systemctl restart netbox netbox-rq

# For Docker-based NetBox
docker-compose restart netbox netbox-worker

# For manual/development setup
# Stop and restart your WSGI server (gunicorn/uWSGI) and RQ worker
```

## Step 7: Verify Installation

### Check Web Interface

1. Log in to NetBox
2. Navigate to **Plugins** in the top navigation
3. You should see **Meraki Sync** in the plugins list
4. Click on it to access the dashboard

### Check from Command Line

```bash
cd /opt/netbox/netbox
source /opt/netbox/venv/bin/activate

# List installed plugins
python manage.py showmigrations netbox_meraki

# Should show:
# netbox_meraki
#  [X] 0001_initial
#  [X] 0002_add_settings_and_site_rules
#  [X] 0003_add_sync_review

# Test sync command
python manage.py sync_meraki --mode dry_run
```

## Step 8: Initial Configuration

### Configure Device Role Mappings

1. Navigate to **Plugins > Meraki Sync > Configuration**
2. Set device roles for each Meraki product type:
   - **MX (Security Appliance)**: e.g., "Firewall" or "Security Device"
   - **MS (Switch)**: e.g., "Switch"
   - **MR (Wireless AP)**: e.g., "Wireless Access Point"
   - **MG (Cellular Gateway)**: e.g., "Cellular Gateway"
   - **MV (Camera)**: e.g., "Security Camera"
   - **MT (Sensor)**: e.g., "IoT Sensor"
3. Click **Save Settings**

### Add Site Name Transformation Rules (Optional)

If your Meraki network names need to be transformed before creating sites:

1. Navigate to **Plugins > Meraki Sync > Configuration > Site Name Rules**
2. Click **Add Rule**
3. Configure:
   - **Name**: Description of the rule
   - **Regex Pattern**: Pattern to match (e.g., `^NYC-(.+)$`)
   - **Site Name Template**: Replacement (e.g., `New York - \1`)
   - **Priority**: Lower numbers run first
   - **Enabled**: Check to activate
4. Click **Create**

## Step 9: Run Your First Sync

### Using Web Interface (Recommended for first sync)

1. Navigate to **Plugins > Meraki Sync**
2. Click **Sync Now**
3. Select **Sync with Review** mode (recommended for first sync)
4. Click **Start Synchronization**
5. Review the proposed changes
6. Approve or reject items as needed
7. Click **Apply Approved Changes**

### Using Command Line

```bash
cd /opt/netbox/netbox
source /opt/netbox/venv/bin/activate

# Dry run first (preview only)
python manage.py sync_meraki --mode dry_run

# Review mode (stage for approval)
python manage.py sync_meraki --mode review
# Then approve via web interface

# Auto mode (immediate sync)
python manage.py sync_meraki --mode auto
```

## Troubleshooting

### Plugin Not Showing in NetBox

**Check:**
1. Plugin is installed: `pip list | grep netbox-meraki`
2. Configuration syntax is correct in `configuration.py`
3. NetBox services restarted successfully
4. Check NetBox logs: `tail -f /opt/netbox/netbox/netbox.log`

### Migration Errors

```bash
# Check migration status
python manage.py showmigrations netbox_meraki

# If migrations are not applied
python manage.py migrate netbox_meraki

# If you need to reset (WARNING: deletes plugin data)
python manage.py migrate netbox_meraki zero
python manage.py migrate netbox_meraki
```

### API Authentication Errors

**Check:**
1. API key is correct in configuration
2. API key has not expired
3. API access is enabled in Meraki Dashboard
4. Network connectivity to `api.meraki.com`

Test API access:
```bash
curl -H "X-Cisco-Meraki-API-Key: YOUR_API_KEY" \
  https://api.meraki.com/api/v1/organizations
```

### Permission Errors

Ensure the NetBox user has permissions:
- `dcim.add_site`, `dcim.change_site`
- `dcim.add_device`, `dcim.change_device`
- `dcim.add_devicetype`, `dcim.change_devicetype`
- `ipam.add_vlan`, `ipam.change_vlan`
- `ipam.add_prefix`, `ipam.change_prefix`

### No Data Syncing

1. Check sync logs in **Plugins > Meraki Sync**
2. Verify organizations exist in Meraki Dashboard
3. Check NetBox logs for detailed errors
4. Run with `--mode dry_run` to see what would be synced

## Scheduling Automatic Syncs

### Using Cron

```bash
# Edit crontab
sudo crontab -e

# Add entry (runs every hour in review mode)
0 * * * * cd /opt/netbox/netbox && source /opt/netbox/venv/bin/activate && python manage.py sync_meraki --mode review >> /var/log/netbox/meraki-sync.log 2>&1

# For auto mode (immediate sync)
0 * * * * cd /opt/netbox/netbox && source /opt/netbox/venv/bin/activate && python manage.py sync_meraki --mode auto >> /var/log/netbox/meraki-sync.log 2>&1
```

### Using systemd Timer

Create `/etc/systemd/system/netbox-meraki-sync.service`:

```ini
[Unit]
Description=NetBox Meraki Sync
After=network.target

[Service]
Type=oneshot
User=netbox
WorkingDirectory=/opt/netbox/netbox
ExecStart=/opt/netbox/venv/bin/python manage.py sync_meraki --mode review
StandardOutput=journal
StandardError=journal
```

Create `/etc/systemd/system/netbox-meraki-sync.timer`:

```ini
[Unit]
Description=Run NetBox Meraki Sync Hourly

[Timer]
OnCalendar=hourly
Persistent=true

[Install]
WantedBy=timers.target
```

Enable and start:

```bash
sudo systemctl daemon-reload
sudo systemctl enable netbox-meraki-sync.timer
sudo systemctl start netbox-meraki-sync.timer

# Check status
sudo systemctl status netbox-meraki-sync.timer
```

## Security Best Practices

1. **Never commit API keys to version control**
2. **Use environment variables** for sensitive configuration
3. **Restrict file permissions** on configuration files:
   ```bash
   chmod 600 /opt/netbox/netbox/netbox/configuration.py
   chmod 600 /opt/netbox/netbox/netbox/.env
   ```
4. **Use NetBox RBAC** to control who can trigger syncs
5. **Review mode** for production environments
6. **Regular backups** before running syncs
7. **Test in non-production** environment first

## Upgrading the Plugin

```bash
cd /opt/netbox
source venv/bin/activate

# Upgrade plugin
pip install --upgrade netbox-meraki

# Or for development install
cd /opt/netbox-meraki
git pull
pip install -e . --upgrade

# Run any new migrations
cd /opt/netbox/netbox
python manage.py migrate netbox_meraki

# Collect static files
python manage.py collectstatic --no-input

# Restart services
sudo systemctl restart netbox netbox-rq
```

## Uninstalling the Plugin

```bash
cd /opt/netbox
source venv/bin/activate

# Reverse migrations (WARNING: deletes all plugin data)
cd netbox
python manage.py migrate netbox_meraki zero

# Remove from configuration.py
# Remove 'netbox_meraki' from PLUGINS list
# Remove 'netbox_meraki' from PLUGINS_CONFIG

# Uninstall package
pip uninstall netbox-meraki

# Restart services
sudo systemctl restart netbox netbox-rq
```

## Getting Help

- **Issues**: https://github.com/yourusername/netbox-meraki/issues
- **Documentation**: See README.md and EXAMPLES.md
- **NetBox Community**: https://github.com/netbox-community/netbox/discussions

## Next Steps

After installation:

1. Review [QUICKSTART.md](QUICKSTART.md) for basic usage
2. Check [EXAMPLES.md](EXAMPLES.md) for common scenarios
3. Configure device role mappings for your environment
4. Set up site name transformation rules if needed
5. Run initial sync in review mode
6. Schedule automatic syncs
7. Monitor sync logs regularly

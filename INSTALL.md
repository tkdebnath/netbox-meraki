# NetBox Meraki Plugin Installation Guide

## Quick Start

### 1. Prerequisites

- NetBox 4.4.x
- Python 3.10+
- Meraki Dashboard API access

### 2. Installation

```bash
# Using pip
pip install netbox-meraki

# Or from source
git clone https://github.com/tkdebnath/netbox-meraki.git
cd netbox-meraki
pip install .
```

### 3. Configuration

Edit your NetBox `configuration.py`:

```python
# At the top of the file, ensure you have:
import os

# Enable the plugin
PLUGINS = [
    'netbox_meraki',
]

# Configure the plugin
PLUGINS_CONFIG = {
    'netbox_meraki': {
        # Required: Meraki API key (recommended to use environment variable)
        'meraki_api_key': os.environ.get('MERAKI_API_KEY', ''),
        
        # Optional: Auto-creation settings (defaults to True)
        'auto_create_sites': True,
        'auto_create_device_types': True,
        'auto_create_device_roles': True,
        'auto_create_manufacturers': True,
        
        # Optional: Default values
        # 'default_site_group': None,
        # 'default_manufacturer': 'Cisco Meraki',
        # 'meraki_base_url': 'https://api.meraki.com/api/v1',
        
        # Optional: Customize default device role names
        # 'mx_device_role': 'Meraki Firewall',
        # 'ms_device_role': 'Meraki Switch',
        # 'mr_device_role': 'Meraki AP',
        # 'mg_device_role': 'Meraki Cellular Gateway',
        # 'mv_device_role': 'Meraki Camera',
        # 'mt_device_role': 'Meraki Sensor',
        # 'default_device_role': 'Meraki Unknown',
    }
}
```

### 4. Apply Migrations

```bash
cd /opt/netbox
source venv/bin/activate
python manage.py migrate netbox_meraki
```

### 5. Restart NetBox

```bash
sudo systemctl restart netbox netbox-rq
```

## Development / Code Changes

When modifying the plugin code, you need to completely uninstall and reinstall it for changes to take effect:

### Complete Reinstall After Code Changes

```bash
# Navigate to the plugin directory
cd /path/to/netbox-meraki

# Activate NetBox virtual environment
source /opt/netbox/venv/bin/activate

# Uninstall existing plugin
pip uninstall -y netbox-meraki

# Clean Python cache
find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
find . -type f -name "*.pyc" -delete 2>/dev/null || true

# Install fresh from source
pip install .

# Apply migrations
cd /opt/netbox/netbox
python manage.py migrate netbox_meraki

# Collect static files
python manage.py collectstatic --no-input

# Restart NetBox services to load the new code
sudo systemctl restart netbox netbox-rq
```

### Quick Reinstall Script

Use the provided script for convenience:

```bash
cd /path/to/netbox-meraki
./reinstall.sh
```

This script will:
- Uninstall the existing plugin
- Clean Python cache files
- Install fresh from source
- Apply migrations
- Collect static files
- Restart services

### 6. First Sync

Navigate to **Plugins > Meraki Sync** in NetBox and click **Sync Now**.

## Configuration Options

See the main [README.md](README.md) for detailed configuration options.

## Troubleshooting

### Common Issues

1. **"Meraki API key is required" error**
   - Check that `meraki_api_key` is set in `PLUGINS_CONFIG`
   - Verify the API key is valid

2. **No menu item appears**
   - Ensure the plugin is in the `PLUGINS` list
   - Restart NetBox services
   - Clear browser cache

3. **Permission errors**
   - Ensure your user has appropriate NetBox permissions
   - Minimum required: `dcim.add_device`, `dcim.add_site`, `ipam.add_vlan`, `ipam.add_prefix`

## Next Steps

- Review the [README.md](README.md) for detailed documentation
- Set up automated syncs with cron
- Explore the REST API endpoints

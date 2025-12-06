# NetBox Meraki Plugin Installation Guide

## Quick Start

### 1. Prerequisites

- NetBox 3.5.0 or higher
- Python 3.10+
- Meraki Dashboard API access

### 2. Installation

```bash
# Using pip
pip install netbox-meraki

# Or from source
git clone https://github.com/yourusername/netbox-meraki.git
cd netbox-meraki
pip install .
```

### 3. Configuration

Edit your NetBox `configuration.py`:

```python
# Enable the plugin
PLUGINS = [
    'netbox_meraki',
]

# Configure the plugin
PLUGINS_CONFIG = {
    'netbox_meraki': {
        'meraki_api_key': 'your-api-key-here',
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

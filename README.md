# NetBox Meraki Sync Plugin

A NetBox plugin that synchronizes Cisco Meraki Dashboard data to NetBox. This plugin provides one-way synchronization of networks, devices, VLANs, and prefixes from Meraki to NetBox.

## Features

- **One-way synchronization** from Meraki Dashboard to NetBox
- **Organization support**: Sync multiple Meraki organizations
- **Network sync**: Meraki networks are imported as NetBox Sites
- **Device sync**: Import Meraki devices with accurate information including:
  - Device model and manufacturer
  - Serial numbers
  - Management IP addresses
  - Device status
  - Firmware versions
- **VLAN sync**: Import VLANs configured on MX appliances
- **Prefix sync**: Import subnets/prefixes from Meraki VLANs
- **Automatic tagging**: All synced objects are tagged with "Meraki" for easy identification
- **Sync logging**: Track synchronization history and results
- **Web UI**: Dashboard for monitoring sync status and triggering syncs
- **Management command**: CLI command for automation and scheduling
- **REST API**: Programmatic access to sync logs and trigger syncs

## Requirements

- NetBox 3.5.0 or higher (up to 4.0.0)
- Python 3.10 or higher
- Cisco Meraki Dashboard API key

## Installation

### 1. Install the plugin

```bash
pip install netbox-meraki
```

Or install from source:

```bash
git clone https://github.com/yourusername/netbox-meraki.git
cd netbox-meraki
pip install .
```

### 2. Enable the plugin

Add `netbox_meraki` to the `PLUGINS` list in your NetBox `configuration.py`:

```python
PLUGINS = [
    'netbox_meraki',
]
```

### 3. Configure the plugin

Add the plugin configuration to `PLUGINS_CONFIG` in `configuration.py`:

```python
PLUGINS_CONFIG = {
    'netbox_meraki': {
        'meraki_api_key': 'your-meraki-api-key-here',
        'meraki_base_url': 'https://api.meraki.com/api/v1',
        'sync_interval': 3600,  # Optional: seconds between auto-syncs
        'auto_create_sites': True,
        'auto_create_device_types': True,
        'auto_create_device_roles': True,
        'auto_create_manufacturers': True,
        'default_device_role': 'Network Device',
        'default_manufacturer': 'Cisco Meraki',
    }
}
```

### 4. Run database migrations

```bash
cd /opt/netbox
source venv/bin/activate
python manage.py migrate netbox_meraki
```

### 5. Restart NetBox

```bash
sudo systemctl restart netbox netbox-rq
```

## Configuration

### Required Settings

- `meraki_api_key`: Your Cisco Meraki Dashboard API key

### Optional Settings

- `meraki_base_url`: Meraki API base URL (default: `https://api.meraki.com/api/v1`)
- `sync_interval`: Auto-sync interval in seconds (default: 3600)
- `auto_create_sites`: Automatically create sites for Meraki networks (default: True)
- `auto_create_device_types`: Automatically create device types (default: True)
- `auto_create_device_roles`: Automatically create device roles (default: True)
- `auto_create_manufacturers`: Automatically create manufacturers (default: True)
- `default_device_role`: Default device role name (default: "Network Device")
- `default_manufacturer`: Default manufacturer name (default: "Cisco Meraki")

### Getting a Meraki API Key

1. Log in to the Meraki Dashboard
2. Navigate to Organization > Settings > Dashboard API access
3. Enable API access
4. Generate an API key
5. Copy the key and add it to your NetBox configuration

## Usage

### Web Interface

1. Navigate to **Plugins > Meraki Sync** in NetBox
2. View the dashboard for sync status and history
3. Click **Sync Now** to trigger a manual synchronization
4. View detailed sync logs by clicking on log entries

### Management Command

Run synchronization from the command line:

```bash
python manage.py sync_meraki
```

With a custom API key:

```bash
python manage.py sync_meraki --api-key your-api-key
```

### REST API

Trigger a sync via API:

```bash
curl -X POST \
  https://your-netbox-instance/api/plugins/meraki/sync-logs/trigger_sync/ \
  -H "Authorization: Token your-netbox-api-token" \
  -H "Content-Type: application/json"
```

List sync logs:

```bash
curl https://your-netbox-instance/api/plugins/meraki/sync-logs/ \
  -H "Authorization: Token your-netbox-api-token"
```

### Scheduling Automatic Syncs

You can schedule regular syncs using cron:

```bash
# Add to crontab (run every hour)
0 * * * * cd /opt/netbox && source venv/bin/activate && python manage.py sync_meraki >> /var/log/netbox/meraki-sync.log 2>&1
```

## What Gets Synchronized

### Organizations
- All organizations accessible with your API key

### Networks → Sites
- Network name becomes Site name
- Network ID stored in site comments
- Organization name included in site description

### Devices
- Serial number (used as unique identifier)
- Device name
- Device model (creates DeviceType if needed)
- Device status (active/offline)
- Management IP address
- MAC address
- Firmware version
- Product type

### VLANs
- VLAN ID
- VLAN name
- Associated subnet information
- Grouped by site

### Prefixes
- Subnet/prefix from Meraki VLANs
- Associated with NetBox sites
- VLAN association details

## Tagging

All objects imported from Meraki are automatically tagged with a "Meraki" tag. This allows you to:
- Filter objects synced from Meraki
- Identify which objects are managed by the plugin
- Create reports specific to Meraki infrastructure

## Sync Behavior

- **One-way sync**: Data flows only from Meraki to NetBox
- **Updates**: Existing objects are updated based on serial number (devices) or name (sites, VLANs)
- **No deletions**: The plugin does not delete objects from NetBox
- **Idempotent**: Running sync multiple times produces the same result

## Troubleshooting

### API Key Issues

If you see authentication errors:
1. Verify your API key is correct in `configuration.py`
2. Ensure API access is enabled in Meraki Dashboard
3. Check that the API key has access to the organizations

### No Data Syncing

1. Check sync logs in the plugin dashboard
2. Review NetBox logs: `/var/log/netbox/netbox.log`
3. Verify network connectivity to Meraki API
4. Ensure you have organizations and networks in Meraki

### Permission Errors

The user triggering the sync needs appropriate NetBox permissions:
- `dcim.add_device`
- `dcim.add_site`
- `ipam.add_vlan`
- `ipam.add_prefix`

## Development

### Running Tests

```bash
python manage.py test netbox_meraki
```

### Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests
5. Submit a pull request

## Support

- **Issues**: [GitHub Issues](https://github.com/yourusername/netbox-meraki/issues)
- **Documentation**: [GitHub Wiki](https://github.com/yourusername/netbox-meraki/wiki)

## License

This project is licensed under the Apache License 2.0 - see the LICENSE file for details.

## Acknowledgments

- Built for [NetBox](https://github.com/netbox-community/netbox)
- Uses [Cisco Meraki Dashboard API](https://developer.cisco.com/meraki/api-latest/)

## Changelog

### Version 0.1.0 (Initial Release)

- Initial plugin implementation
- One-way sync from Meraki to NetBox
- Support for networks, devices, VLANs, and prefixes
- Web UI dashboard and sync management
- REST API endpoints
- Management command for CLI usage
- Comprehensive sync logging

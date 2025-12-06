# NetBox Meraki Plugin - Quick Reference

## Project Structure

```
netbox-meraki/
├── netbox_meraki/              # Main plugin package
│   ├── __init__.py            # Plugin configuration
│   ├── admin.py               # Django admin configuration
│   ├── models.py              # Database models (SyncLog)
│   ├── views.py               # Web views
│   ├── urls.py                # URL routing
│   ├── navigation.py          # Plugin menu items
│   ├── meraki_client.py       # Meraki API client
│   ├── sync_service.py        # Synchronization logic
│   ├── api/                   # REST API
│   │   ├── __init__.py
│   │   ├── serializers.py
│   │   ├── views.py
│   │   └── urls.py
│   ├── management/            # Management commands
│   │   ├── __init__.py
│   │   └── commands/
│   │       ├── __init__.py
│   │       └── sync_meraki.py
│   └── templates/             # HTML templates
│       └── netbox_meraki/
│           ├── dashboard.html
│           ├── sync.html
│           ├── synclog.html
│           └── config.html
├── README.md                  # Main documentation
├── INSTALL.md                 # Installation guide
├── LICENSE                    # Apache 2.0 license
├── pyproject.toml            # Package metadata
├── requirements.txt          # Dependencies
├── MANIFEST.in               # Package manifest
├── configuration_example.py  # Config example
└── setup.sh                  # Setup script

```

## Key Features

### 1. Meraki API Client (`meraki_client.py`)
- Connects to Cisco Meraki Dashboard API
- Retrieves organizations, networks, devices, VLANs, and subnets
- Handles authentication and error management

### 2. Sync Service (`sync_service.py`)
- One-way synchronization from Meraki to NetBox
- Creates/updates:
  - Sites (from Meraki networks)
  - Devices (with types, roles, manufacturers)
  - VLANs (grouped by site)
  - Prefixes (from VLAN subnets)
  - IP addresses and interfaces
- Automatic tagging with "Meraki" tag
- Comprehensive error handling and logging

### 3. Web Interface
- **Dashboard**: View sync status and history
- **Sync Page**: Trigger manual synchronization
- **Sync Logs**: Detailed results of each sync
- **Configuration**: View current plugin settings

### 4. Management Command
```bash
python manage.py sync_meraki [--api-key KEY]
```

### 5. REST API
- `GET /api/plugins/meraki/sync-logs/` - List sync logs
- `POST /api/plugins/meraki/sync-logs/trigger_sync/` - Trigger sync

## Installation Steps

1. **Install the plugin**:
   ```bash
   pip install netbox-meraki
   ```

2. **Configure NetBox** (`configuration.py`):
   ```python
   PLUGINS = ['netbox_meraki']
   
   PLUGINS_CONFIG = {
       'netbox_meraki': {
           'meraki_api_key': 'your-api-key',
       }
   }
   ```

3. **Run migrations**:
   ```bash
   python manage.py migrate netbox_meraki
   ```

4. **Restart NetBox**:
   ```bash
   sudo systemctl restart netbox netbox-rq
   ```

## Usage Examples

### Web UI
1. Navigate to **Plugins > Meraki Sync**
2. Click **Sync Now**
3. View results in the dashboard

### CLI
```bash
# Manual sync
python manage.py sync_meraki

# With custom API key
python manage.py sync_meraki --api-key YOUR_KEY

# Schedule with cron (every hour)
0 * * * * cd /opt/netbox && source venv/bin/activate && python manage.py sync_meraki
```

### API
```bash
# Trigger sync
curl -X POST \
  http://netbox.example.com/api/plugins/meraki/sync-logs/trigger_sync/ \
  -H "Authorization: Token YOUR_TOKEN" \
  -H "Content-Type: application/json"

# Get sync logs
curl http://netbox.example.com/api/plugins/meraki/sync-logs/ \
  -H "Authorization: Token YOUR_TOKEN"
```

## Data Mapping

| Meraki | NetBox |
|--------|--------|
| Organization | Organization context |
| Network | Site |
| Device | Device (with DeviceType, DeviceRole) |
| VLAN | VLAN (in VLANGroup) |
| Subnet | Prefix |
| Device LAN IP | IPAddress + Interface |

## Configuration Options

| Setting | Default | Description |
|---------|---------|-------------|
| `meraki_api_key` | Required | Meraki Dashboard API key |
| `meraki_base_url` | `https://api.meraki.com/api/v1` | Meraki API URL |
| `sync_interval` | 3600 | Auto-sync interval (seconds) |
| `auto_create_sites` | True | Auto-create sites |
| `auto_create_device_types` | True | Auto-create device types |
| `auto_create_device_roles` | True | Auto-create device roles |
| `auto_create_manufacturers` | True | Auto-create manufacturers |
| `default_device_role` | "Network Device" | Default device role |
| `default_manufacturer` | "Cisco Meraki" | Default manufacturer |

## Permissions Required

Users triggering syncs need:
- `dcim.add_device`
- `dcim.add_site`
- `dcim.add_devicetype`
- `dcim.add_devicerole`
- `dcim.add_manufacturer`
- `ipam.add_vlan`
- `ipam.add_prefix`
- `ipam.add_ipaddress`

## Troubleshooting

### No data syncing
- Check API key is valid
- Verify Meraki API access is enabled
- Check sync logs for errors
- Review NetBox logs: `/var/log/netbox/netbox.log`

### Authentication errors
- Verify API key in configuration
- Check API key has organization access
- Ensure API access is enabled in Meraki Dashboard

### Permission errors
- Verify user has required NetBox permissions
- Check NetBox logs for specific permission issues

## Development

### Running locally
```bash
# Clone repository
git clone https://github.com/yourusername/netbox-meraki.git
cd netbox-meraki

# Setup
./setup.sh

# Activate environment
source venv/bin/activate

# Install in development mode
pip install -e .
```

### Testing
```bash
python manage.py test netbox_meraki
```

## Support

- **Documentation**: [README.md](README.md)
- **Installation**: [INSTALL.md](INSTALL.md)
- **Issues**: GitHub Issues
- **Configuration**: [configuration_example.py](configuration_example.py)

## License

Apache License 2.0 - See [LICENSE](LICENSE)

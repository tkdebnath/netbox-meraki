# NetBox Meraki Sync Plugin

A NetBox plugin that synchronizes Cisco Meraki Dashboard data to NetBox. This plugin provides intelligent one-way synchronization with automatic cleanup and update capabilities.

## Features

### Core Synchronization
- **One-way synchronization** from Meraki Dashboard to NetBox
- **Organization support**: Sync multiple Meraki organizations
- **Network sync**: Meraki networks are imported as NetBox Sites
- **Device sync**: Import Meraki devices with accurate information including:
  - Device model and manufacturer
  - Serial numbers (enforced uniqueness)
  - Management IP addresses and interfaces
  - Device status (active/offline)
  - Firmware versions (custom field)
  - Wireless SSIDs (for access points)
  - Switch port configurations with VLANs
- **VLAN sync**: Import VLANs configured on MX appliances
- **Prefix sync**: Import subnets/prefixes with automatic site updates

### Smart Data Management
- **Orphaned object cleanup**: Automatically removes objects deleted from Meraki
- **Device serial uniqueness**: Prevents duplicate devices with same serial number
- **Prefix site updates**: Automatically updates prefix sites when networks change
- **Interface management**: Full switch port sync with VLAN assignments (access/trunk)
- **Custom fields**: Automatic creation for firmware versions and SSIDs

### Operational Features
- **Three sync modes**: Auto, Review (with approval), and Dry Run
- **Automatic tagging**: All synced objects tagged with "Meraki"
- **Comprehensive logging**: Track all sync operations with detailed statistics
- **Web UI**: Dashboard for monitoring sync status and triggering syncs
- **Management command**: CLI command for automation and scheduling
- **REST API**: Programmatic access to sync logs and trigger syncs
- **Scheduling**: Built-in scheduler with cron/systemd/continuous service support

## Requirements

- NetBox 4.4.x
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

### Sync Modes

The plugin supports three synchronization modes to give you control over how changes are applied:

#### Auto Sync
All changes from Meraki are immediately applied to NetBox without review. This is the fastest mode and is suitable for automated environments where you trust the sync process.

**Use cases:**
- Scheduled automatic syncs
- Initial setup and testing
- Environments where immediate sync is required

#### Sync with Review
Changes are staged for review before being applied. You can approve or reject individual items (sites, devices, VLANs, prefixes) before they are created or updated in NetBox.

**Use cases:**
- Production environments requiring change control
- When you want to selectively sync certain items
- Compliance requirements for change approval

**Workflow:**
1. Trigger sync with "Review" mode
2. Review all proposed changes in the web interface
3. Approve or reject individual items
4. Apply approved changes to NetBox

#### Dry Run
Preview all changes that would be made without actually modifying NetBox. This is useful for testing and understanding what the sync will do.

**Use cases:**
- Testing before running a real sync
- Understanding the impact of synchronization
- Validating configuration before applying changes

### Web Interface

1. Navigate to **Plugins > Meraki Sync** in NetBox
2. View the dashboard for sync status and history
3. Click **Sync Now** to trigger a manual synchronization
4. Select your desired sync mode (Auto, Review, or Dry Run)
5. For Review mode: navigate to the review page to approve/reject changes
6. View detailed sync logs by clicking on log entries

### Management Command

Run synchronization from the command line:

```bash
# Auto sync (default - immediate application)
python manage.py sync_meraki

# Sync with review (stage changes for approval)
python manage.py sync_meraki --mode review

# Dry run (preview only, no changes applied)
python manage.py sync_meraki --mode dry_run
```

With a custom API key:

```bash
python manage.py sync_meraki --api-key your-api-key --mode review
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

## Additional Documentation

- **[SCHEDULING_GUIDE.md](SCHEDULING_GUIDE.md)** - Complete guide for setting up automatic scheduled syncs
- **[SYNC_BEHAVIOR.md](SYNC_BEHAVIOR.md)** - Detailed sync behavior, cleanup rules, and data consistency
- **[INSTALLATION_GUIDE.md](INSTALLATION_GUIDE.md)** - Comprehensive installation and setup guide
- **[CONFIGURATION_EXAMPLES.md](CONFIGURATION_EXAMPLES.md)** - Configuration examples and recipes
- **[QUICK_REFERENCE.md](QUICK_REFERENCE.md)** - Quick reference for common tasks

## License

This project is licensed under the Apache License 2.0 - see the LICENSE file for details.

## Acknowledgments

- Built for [NetBox](https://github.com/netbox-community/netbox)
- Uses [Cisco Meraki Dashboard API](https://developer.cisco.com/meraki/api-latest/)

## Changelog

### Version 0.6.0 (Latest)

**Live Progress & Monitoring:**
- Real-time progress tracking with live logs during sync
- Progress bar showing completion percentage
- Current operation display showing what's being synced
- Auto-refreshing sync log view (3-second intervals)
- Comprehensive progress logging with timestamps and levels (INFO/WARN/ERROR)
- SSID synchronization tracking in statistics

**Cancel Sync Capability:**
- Cancel button for ongoing sync operations
- Graceful cancellation after current operation completes
- API endpoint for programmatic cancellation
- Cancellation timestamp tracking
- Prevents data corruption by completing current operation

**Enhanced Review Mode:**
- Categorized review items by type (Sites, Devices, VLANs, Prefixes, SSIDs)
- Detailed preview displays for each item showing all field values
- Related object information (site, role, manufacturer, etc.)
- Side-by-side comparison for updates (current vs. new values)
- Expandable sections for better organization
- Device type and SSID item types added

**Automatic Device Type Creation:**
- Automatically creates missing device types during sync
- Part number field automatically filled with model number
- Updates existing device types if part number is missing
- Reduces manual configuration requirements
- Progress log entry when device types are created

**API Enhancements:**
- `/api/plugins/netbox-meraki/sync-logs/{id}/progress/` - Get live progress updates
- `/api/plugins/netbox-meraki/sync-logs/{id}/cancel/` - Cancel ongoing sync
- Real-time JSON response with all sync statistics
- SSID count included in progress data

**Migration Required:**
```bash
python manage.py migrate netbox_meraki
```

### Version 0.5.0

**Name Transformation Features:**
- Configurable name transformations for devices, sites, VLANs, and SSIDs
- Options: Keep Original, UPPERCASE, lowercase, Title Case
- Applied during sync for consistent naming conventions
- Separate control for each object type

**NetBox Job Integration:**
- Native NetBox background job support
- `MerakiSyncJob` - Manual sync via Jobs UI
- `ScheduledMerakiSyncJob` - Scheduled sync with status tracking
- View job status, logs, and history in NetBox UI
- Schedule jobs using NetBox's built-in scheduler
- Better visibility and monitoring

**UI Enhancements:**
- New "Name Transformations" configuration tab
- Examples for each transformation type
- Quick access to Scheduled Jobs from dashboard
- Improved configuration organization

**Migration Required:**
```bash
python manage.py migrate netbox_meraki
```

See configuration tab for name transformation settings.

### Version 0.4.0

**Scheduling Features:**
- Built-in scheduling system with configurable intervals
- Multiple deployment options: systemd service, systemd timer, cron jobs
- Continuous background service mode with auto-restart
- Configurable sync modes for scheduled runs (auto/review/dry_run)
- Automatic next-sync-time calculation and tracking
- Web UI for scheduling configuration
- `schedule_meraki_sync` management command
- Systemd and cron deployment templates included

See [SCHEDULING_GUIDE.md](SCHEDULING_GUIDE.md) for setup instructions.

### Version 0.3.0

**Smart Data Management:**
- Automatic orphaned object cleanup (sites, devices, VLANs, prefixes)
- Device serial number uniqueness enforcement (prevents duplicates)
- Automatic prefix site updates when network changes
- Comprehensive interface syncing with VLANs (access/trunk modes)
- Switch port configuration sync with VLAN assignments

**Enhanced Features:**
- Custom fields for firmware versions and SSIDs
- Wireless AP SSID tracking
- IP address management on interfaces
- Detailed cleanup and update statistics
- Enhanced logging for all operations

See [SYNC_BEHAVIOR.md](SYNC_BEHAVIOR.md) for detailed documentation on new features.

### Version 0.2.0

- Added three sync modes: Auto, Review, and Dry Run
- Review management interface for staged changes
- Approve/reject individual items before applying
- Enhanced management command with --mode option
- Database-backed review tracking with SyncReview and ReviewItem models

### Version 0.1.0 (Initial Release)

- Initial plugin implementation
- One-way sync from Meraki to NetBox
- Support for networks, devices, VLANs, and prefixes
- Web UI dashboard and sync management
- REST API endpoints
- Management command for CLI usage
- Comprehensive sync logging
- Device role mappings and site name transformation rules

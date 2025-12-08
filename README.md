# NetBox Meraki Sync Plugin

A comprehensive NetBox plugin for synchronizing Cisco Meraki infrastructure with NetBox. Automatically imports networks, devices, VLANs, IP prefixes, wireless LANs, and maintains accurate inventory with intelligent cleanup capabilities.

**Author:** Tarani Debnath

## Performance

Optimized for efficiency using NetBox's native job scheduling system.

## Features

### Core Synchronization
- **Organizations & Networks**: Sync single or multiple Meraki organizations with selective network filtering
- **Sites**: Meraki networks automatically mapped to NetBox sites with customizable name rules
- **Devices**: Complete device inventory with accurate models, roles, and serial numbers
  - Automatic device role assignment based on product type (MX, MS, MR, MG, MV, MT)
  - Color-coded roles for easy visual identification
  - Firmware version tracking via custom fields
  - MAC address storage
  - Device status monitoring (active/offline)
- **VLANs**: Import configured VLANs from MX security appliances
- **IP Prefixes/Subnets**: Automatic prefix discovery with site association
- **Interfaces**: 
  - WAN interfaces with public IP assignments for MX devices
  - SVI (VLAN) interfaces for all configured VLANs on MX appliances
  - Wireless interfaces for access points
- **Wireless LANs**: Native NetBox Wireless LAN objects for SSIDs
  - Organization-wide SSID management
  - Automatic association with access points
  - Authentication and encryption tracking

### Advanced Features
- **Three Sync Modes**:
  - **Auto Sync**: Immediate application of changes
  - **Review Mode**: Stage changes for manual approval
  - **Dry Run**: Preview changes without modifications
- **Intelligent Cleanup**: Automatic removal of objects no longer in Meraki
- **Flexible Filtering**:
  - Organization selection
  - Network-specific sync
  - Prefix filtering with include/exclude rules
  - Site name transformation rules
- **Name Transformations**: Standardize naming across devices, sites, VLANs, and SSIDs
- **Tag Management**: Optional tagging for all synchronized objects
- **API Rate Limiting**: Built-in throttling to respect Meraki API limits
- **Scheduled Syncs**: Background job support with configurable intervals
- **Live Progress Tracking**: Real-time sync status with detailed logs

## Requirements

- NetBox 4.4.x or higher
- Python 3.10+
- Meraki Dashboard API access

## Installation

### Option 1: Docker Installation (Recommended)

For NetBox running in Docker, add the plugin to your NetBox container:

#### Step 1: Clone the Repository

```bash
cd /opt
git clone https://github.com/tkdebnath/netbox-meraki.git
```

#### Step 2: Update Docker Compose

Edit your `docker-compose.yml`:

```yaml
services:
  netbox:
    image: netboxcommunity/netbox:latest
    # ... other configuration ...
    volumes:
      - /opt/netbox-meraki:/opt/netbox-meraki:ro
      - ./extra-requirements.txt:/opt/netbox/extra-requirements.txt:ro
```

#### Step 3: Create Requirements File

Create `extra-requirements.txt` in your NetBox directory:

```txt
/opt/netbox-meraki
```

#### Step 4: Rebuild and Restart

```bash
docker-compose down
docker-compose build --no-cache netbox
docker-compose up -d
```

#### Step 5: Run Migrations

```bash
docker-compose exec netbox python /opt/netbox/netbox/manage.py migrate netbox_meraki
docker-compose exec netbox python /opt/netbox/netbox/manage.py collectstatic --no-input
```

#### Step 6: Restart Services

```bash
docker-compose restart netbox
```

### Option 2: Standard Installation

For NetBox installed directly on a server:

#### Step 1: Activate Virtual Environment

```bash
source /opt/netbox/venv/bin/activate
```

#### Step 2: Install Plugin

```bash
# From PyPI (when published)
pip install netbox-meraki

# Or from source
cd /opt
git clone https://github.com/tkdebnath/netbox-meraki.git
cd netbox-meraki
pip install .
```

#### Step 3: Run Migrations

```bash
cd /opt/netbox/netbox
python manage.py migrate netbox_meraki
```

#### Step 4: Collect Static Files

```bash
python manage.py collectstatic --no-input
```

#### Step 5: Restart Services

```bash
sudo systemctl restart netbox netbox-rq
```

## Configuration

Edit your NetBox `configuration.py` file (located at `/opt/netbox/netbox/netbox/configuration.py`):

```python
# At the top of configuration.py, ensure you have:
import os

# Enable the plugin
PLUGINS = [
    'netbox_meraki',
]

# Plugin configuration
PLUGINS_CONFIG = {
    'netbox_meraki': {
        # Required: Meraki API key (can use environment variable)
        'meraki_api_key': os.environ.get('MERAKI_API_KEY', 'your_meraki_api_key_here'),
        
        # Optional: Meraki API base URL (default shown)
        'meraki_base_url': 'https://api.meraki.com/api/v1',
        
        # Optional: Auto-creation settings (all default to True)
        'auto_create_sites': True,
        'auto_create_device_types': True,
        'auto_create_device_roles': True,
        'auto_create_manufacturers': True,
        
        # Optional: Default values
        'default_site_group': None,  # Site group name or None
        'default_manufacturer': 'Cisco Meraki',
        
        # Optional: Override default device role names
        'mx_device_role': 'Meraki Firewall',
        'ms_device_role': 'Meraki Switch',
        'mr_device_role': 'Meraki AP',
        'mg_device_role': 'Meraki Cellular Gateway',
        'mv_device_role': 'Meraki Camera',
        'mt_device_role': 'Meraki Sensor',
        'default_device_role': 'Meraki Unknown',
    }
}
```

### Configuration Options

#### Using Environment Variables (Recommended)

For security, it's recommended to use environment variables for sensitive data:

```bash
# Add to /opt/netbox/netbox/netbox/configuration.py
import os

PLUGINS_CONFIG = {
    'netbox_meraki': {
        'meraki_api_key': os.environ.get('MERAKI_API_KEY', ''),
        # ... other settings
    }
}
```

Then set the environment variable in your NetBox systemd service or `.env` file:
```bash
MERAKI_API_KEY=your_actual_api_key_here
```

#### Auto-Creation Settings

Control automatic object creation during sync:
- **`auto_create_sites`** (default: `True`): Automatically create sites from Meraki networks
- **`auto_create_device_types`** (default: `True`): Automatically create device types for Meraki models
- **`auto_create_device_roles`** (default: `True`): Automatically create device roles if they don't exist
- **`auto_create_manufacturers`** (default: `True`): Automatically create the Cisco Meraki manufacturer

#### Default Values

- **`default_site_group`** (default: `None`): Site group name to assign to all created sites
- **`default_manufacturer`** (default: `'Cisco Meraki'`): Manufacturer name for all Meraki devices
- **`meraki_base_url`** (default: `'https://api.meraki.com/api/v1'`): Meraki Dashboard API base URL

#### Device Role Name Customization

Device role names can be customized in two ways:

1. **In `configuration.py`** (recommended for consistent defaults):
   - Add role name overrides to `PLUGINS_CONFIG` as shown above
   - These apply globally and persist across plugin database resets
   - Changes require a NetBox restart

2. **In the Web UI** (Plugins > Meraki Sync > Configuration > Device Role Mappings):
   - Customize role names on a per-installation basis
   - Changes take effect immediately
   - Stored in the plugin database

**Priority:** Web UI settings take precedence over `configuration.py` defaults.

#### Complete Configuration Reference

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `meraki_api_key` | string | `''` | **Required.** Meraki Dashboard API key |
| `meraki_base_url` | string | `'https://api.meraki.com/api/v1'` | Meraki API base URL |
| `auto_create_sites` | boolean | `True` | Auto-create sites from Meraki networks |
| `auto_create_device_types` | boolean | `True` | Auto-create device types for Meraki models |
| `auto_create_device_roles` | boolean | `True` | Auto-create device roles if missing |
| `auto_create_manufacturers` | boolean | `True` | Auto-create Cisco Meraki manufacturer |
| `default_site_group` | string/null | `None` | Site group name for all created sites |
| `default_manufacturer` | string | `'Cisco Meraki'` | Manufacturer name for devices |
| `mx_device_role` | string | `'Meraki Firewall'` | Device role for MX (Security Appliance) |
| `ms_device_role` | string | `'Meraki Switch'` | Device role for MS (Switch) |
| `mr_device_role` | string | `'Meraki AP'` | Device role for MR (Wireless AP) |
| `mg_device_role` | string | `'Meraki Cellular Gateway'` | Device role for MG (Cellular Gateway) |
| `mv_device_role` | string | `'Meraki Camera'` | Device role for MV (Camera) |
| `mt_device_role` | string | `'Meraki Sensor'` | Device role for MT (Sensor) |
| `default_device_role` | string | `'Meraki Unknown'` | Fallback device role for unknown types |

### Obtaining a Meraki API Key

1. Log in to the [Meraki Dashboard](https://dashboard.meraki.com/)
2. Navigate to **Organization > Settings > Dashboard API access**
3. Enable API access
4. Generate a new API key
5. Copy the key to your NetBox configuration
6. Restart NetBox after updating configuration

## Usage

### Quick Start Guide

#### 1. Access the Plugin

Navigate to **Plugins > Meraki Sync > Dashboard** in NetBox.

#### 2. Start a Sync

Click the **Sync Now** button to open the synchronization interface.

#### 3. Choose Sync Mode

Select your preferred sync mode:
- **Auto Sync**: Changes apply immediately to NetBox
- **Sync with Review**: Review and approve changes before applying
- **Dry Run**: Preview changes without making any modifications

#### 4. Filter Options (Optional)

- **Organization**: Select a specific organization or sync all
- **Networks**: Choose specific networks or sync all networks in the organization

#### 5. Start Synchronization

Click **Start Synchronization** and monitor the live progress logs.

### Configuration Options

Access **Plugins > Meraki Sync > Configuration** to customize behavior:

#### Device Role Mappings Tab

Configure which NetBox device role to use for each Meraki product type:

| Product Type | Default Role | Description |
|--------------|--------------|-------------|
| MX | Meraki Firewall | Security appliances and firewalls |
| MS | Meraki Switch | Network switches |
| MR | Meraki AP | Wireless access points |
| MG | Meraki Cellular Gateway | Cellular gateways |
| MV | Meraki Camera | Security cameras |
| MT | Meraki Sensor | Environmental sensors |

**Note:** Device role names can be overridden in `configuration.py` (see Configuration section above) or customized in the web UI. The plugin will automatically create device roles if they don't exist.

#### Name Transformations Tab

Standardize naming conventions for all synchronized objects:
- **Device Names**: Transform device names (UPPERCASE, lowercase, Title Case, Keep Original)
- **Site Names**: Transform site names
- **VLAN Names**: Transform VLAN names
- **SSID Names**: Transform wireless SSID names

#### Site Name Rules Tab

Define regex patterns to transform Meraki network names into NetBox site names:

**Example:**
```
Pattern: ^(?P<region>[A-Z]{2})-(?P<site>[A-Z]{3})-.*
Template: {region}-{site}
Priority: 1
```

**Result:** `AMER-ABC-ALBERTA` becomes `AMER-ABC`

#### Prefix Filters Tab

Control which subnets are synchronized to NetBox:

**Include Rules:**
- Add patterns for prefixes to sync (e.g., `10.0.0.0/8`)
- Supports CIDR notation and wildcard patterns

**Exclude Rules:**
- Block specific prefixes (e.g., management networks)
- Takes precedence over include rules

#### Tag Configuration Tab

Add tags to all synchronized objects:
- **Site Tags**: Tags for sites created from Meraki networks
- **Device Tags**: Tags for all devices
- **VLAN Tags**: Tags for VLANs
- **Prefix Tags**: Tags for IP prefixes

### Scheduled Synchronization

Schedule syncs through NetBox's job system:

1. Go to **Jobs → Background Jobs** in NetBox
2. Find **"Meraki Dashboard Sync"**
3. Click **Run Job Now**
4. Set **Repeat every** to your desired interval (in minutes):
   - `60` = Hourly
   - `1440` = Daily
   - `10080` = Weekly
5. Click **Run Job**

Or schedule programmatically:

```python
from netbox_meraki.jobs import MerakiSyncJob

MerakiSyncJob.enqueue(user=request.user, interval=60)
```

#### Alternative: Cron Job

Add to crontab:

```bash
*/5 * * * * cd /opt/netbox && /opt/netbox/venv/bin/python manage.py run_scheduled_sync
```

#### Alternative: Systemd Timer

Create `/etc/systemd/system/netbox-meraki-scheduler.service`:

```ini
[Unit]
Description=NetBox Meraki Scheduled Sync
After=network.target

[Service]
Type=oneshot
User=netbox
WorkingDirectory=/opt/netbox
ExecStart=/opt/netbox/venv/bin/python /opt/netbox/netbox/manage.py run_scheduled_sync
```

Create `/etc/systemd/system/netbox-meraki-scheduler.timer`:

```ini
[Unit]
Description=Run NetBox Meraki Scheduled Sync

[Timer]
OnCalendar=*:0/5
Persistent=true

[Install]
WantedBy=timers.target
```

Enable and start:

```bash
sudo systemctl daemon-reload
sudo systemctl enable netbox-meraki-scheduler.timer
sudo systemctl start netbox-meraki-scheduler.timer
```



#### Task Execution and Monitoring

- Tasks update their status in real-time (Pending → Running → Completed/Failed)
- Failed tasks automatically retry at next scheduled time
- Task history tracks total runs, successes, and failures
- Last error message shown for failed tasks
- Success rate calculated from historical executions

#### API Performance Tab

Configure API behavior:

**API Throttling:**
- **Enabled (Recommended)**: Limits requests to 5 per second
- Prevents hitting Meraki API rate limits

**Multithreading:**
- **Disabled (Safe)**: Sequential processing
- **Enabled (Fast)**: Parallel API requests (3-5 threads)
- ⚠️ May increase API usage

### Reviewing Changes (Review Mode)

When using **Sync with Review** mode:

1. After sync completes, click **View Reviews** from the dashboard
2. Review all staged changes grouped by type:
   - Sites
   - Device Types
   - VLANs
   - Prefixes
   - Devices
   - Interfaces
   - IP Addresses
   - SSIDs
3. **Edit** proposed data if needed
4. **Approve** or **Reject** individual items
5. Use **Approve All** or **Reject All** for bulk actions
6. Click **Apply Approved Changes** to commit to NetBox

## Troubleshooting

### Common Issues

#### API Key Invalid

**Symptoms:** Authentication errors, "Invalid API key" messages

**Solutions:**
- Verify API key in NetBox configuration
- Check API access is enabled in Meraki Dashboard
- Ensure key has not expired
- Restart NetBox after configuration changes

#### Rate Limit Errors

**Symptoms:** "Rate limit exceeded" errors in logs

**Solutions:**
- Enable API throttling in API Performance settings
- Reduce max worker threads
- Increase sync interval for scheduled jobs
- Use dry run mode to test before full sync

#### Objects Not Syncing

**Symptoms:** Expected devices/networks not appearing

**Solutions:**
- Check organization and network filters
- Review sync logs for specific errors
- Verify objects exist in Meraki Dashboard
- Check site name rules aren't filtering out networks
- Review prefix filters for IP objects

#### Duplicate Objects

**Symptoms:** Multiple entries for same device/site

**Solutions:**
- Review site name transformation rules
- Check for conflicting regex patterns
- Verify serial numbers are unique
- Use dry run mode to preview changes

#### Sync Hangs or Times Out

**Symptoms:** Sync doesn't complete, UI becomes unresponsive

**Solutions:**
- Check network connectivity to Meraki API
- Disable multithreading
- Sync smaller network batches
- Check NetBox logs for Python errors

### Viewing Logs

#### Dashboard Logs
Navigate to **Dashboard** to view recent sync logs with:
- Sync date and time
- Sync mode used
- Statistics (sites, devices, VLANs, prefixes created)
- Status (completed, failed, in progress)

#### Detailed Logs

**Standard Installation:**
```bash
tail -f /opt/netbox/netbox/logs/netbox.log
```

**Docker Installation:**
```bash
docker-compose logs -f netbox
```

#### Admin Interface

Access Django admin for full sync history:
1. Navigate to **Admin** in NetBox
2. Go to **NETBOX_MERAKI** section
3. View **Sync logs** for complete history
4. View **Sync reviews** for staged changes

### Getting Help

If issues persist:
1. Enable debug logging in NetBox configuration
2. Run sync in dry run mode
3. Check GitHub issues for similar problems
4. Provide logs when reporting issues

## Development

### Local Development Setup

```bash
# Clone repository
git clone https://github.com/tkdebnath/netbox-meraki.git
cd netbox-meraki

# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Install in development mode
pip install -e .

# Run tests (if available)
python -m pytest
```

### Project Structure

```
netbox-meraki/
├── netbox_meraki/
│   ├── __init__.py
│   ├── admin.py
│   ├── forms.py
│   ├── models.py
│   ├── views.py
│   ├── urls.py
│   ├── navigation.py
│   ├── sync_service.py
│   ├── meraki_client.py
│   ├── jobs.py
│   ├── api/
│   │   ├── __init__.py
│   │   ├── serializers.py
│   │   └── views.py
│   ├── management/
│   │   └── commands/
│   │       └── run_scheduled_sync.py
│   ├── migrations/
│   ├── templates/
│   │   └── netbox_meraki/
│   └── templatetags/
├── README.md
├── INSTALL.md
├── CHANGELOG.md
├── LICENSE
├── pyproject.toml
├── requirements.txt
├── MANIFEST.in
└── reinstall.sh
```

### Contributing

Contributions are welcome! To contribute:

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Make your changes
4. Test thoroughly
5. Commit your changes (`git commit -m 'Add amazing feature'`)
6. Push to the branch (`git push origin feature/amazing-feature`)
7. Open a Pull Request

Please ensure:
- Code follows existing style
- All tests pass
- Documentation is updated
- Commit messages are clear

## License

This project is licensed under the Apache License 2.0 - see the [LICENSE](LICENSE) file for details.

## Support

### Documentation
- [Installation Guide](INSTALL.md) - Detailed installation instructions
- [Changelog](CHANGELOG.md) - Version history and changes

### Issues and Questions
- **GitHub Issues**: [Report a bug or request a feature](https://github.com/tkdebnath/netbox-meraki/issues)
- **Discussions**: Share ideas and ask questions

### Compatibility
- NetBox 4.4.x (tested)
- Python 3.10, 3.11, 3.12
- Meraki Dashboard API v1

## Acknowledgments

- **NetBox Community** for the excellent IPAM/DCIM platform
- **Cisco Meraki** for their comprehensive API
- All contributors who help improve this plugin

---

**Made with ❤️ by Tarani Debnath**

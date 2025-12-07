# NetBox Meraki Sync Plugin

A comprehensive NetBox plugin for synchronizing Cisco Meraki infrastructure with NetBox. Automatically imports networks, devices, VLANs, IP prefixes, wireless LANs, and maintains accurate inventory with intelligent cleanup capabilities.

**Author:** Tarani Debnath

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

## Screenshots

### Dashboard
![Dashboard](docs/images/dashboard.png)
*Main dashboard showing sync status and quick actions*

### Sync Interface
![Sync Interface](docs/images/sync.png)
*Start synchronization with organization and network filtering*

### Configuration
![Configuration](docs/images/configuration.png)
*Device role mappings and transformation settings*

### API Performance Settings
![API Performance](docs/images/api_performance.png)
*API rate limiting and multithreading configuration*

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
# Enable the plugin
PLUGINS = [
    'netbox_meraki',
]

# Plugin configuration
PLUGINS_CONFIG = {
    'netbox_meraki': {
        'meraki_api_key': 'your_meraki_api_key_here',
        'meraki_base_url': 'https://api.meraki.com/api/v1',
        'hide_api_key': True,
    }
}
```

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
| MX | Security Appliance | Security appliances and firewalls |
| MS | Switch | Network switches |
| MR | Wireless AP | Wireless access points |
| MG | Cellular Gateway | Cellular gateways |
| MV | Camera | Security cameras |
| MT | Sensor | Environmental sensors |

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

The plugin provides a comprehensive scheduling system to automate synchronization tasks.

#### Access Scheduled Sync

Navigate to **Plugins > Meraki Sync > Scheduled Sync** or click **Scheduled Sync** from the dashboard.

#### Creating a Scheduled Task

1. Click **Create New Task** button
2. Fill in task details:
   - **Task Name**: Descriptive name (e.g., "Daily Full Sync")
   - **Frequency**: One Time, Hourly, Daily, or Weekly
   - **Start Date/Time**: When should the task first run

3. Configure sync options:
   - **Sync Mode**: Full Sync, Selective Networks, or Single Network
   - **Select Networks**: Choose specific networks (for selective/single mode)
   - **Sync Components**: Toggle organizations, sites, devices, VLANs, prefixes
   - **Cleanup Orphaned**: Remove objects that no longer exist in Meraki
   - **Enable Task**: Whether the task is active

4. Click **Create Task**

#### Managing Scheduled Tasks

The scheduled sync page displays all tasks with:
- Task name and sync mode
- Frequency and next run time
- Last run time and status
- Success rate statistics
- Enable/disable toggle
- Edit and delete actions

#### Running Scheduled Tasks

##### Method 1: NetBox Jobs (Recommended - Easiest!)

Use NetBox's built-in job scheduling system:

1. Navigate to **Jobs → Jobs** in NetBox
2. Find **"Execute Scheduled Sync Tasks"** 
3. Click **Run Job** → Check **Schedule at**
4. Set interval: `*/5 * * * *` (every 5 minutes)
5. Click **Run Job**

NetBox will automatically execute due tasks every 5 minutes. View results in **Jobs → Job Results**.

##### Method 2: Cron Job (Alternative)

Add to your crontab:

```bash
# Run every minute to check for due tasks
* * * * * cd /opt/netbox && /opt/netbox/venv/bin/python manage.py run_scheduled_sync
```

##### Method 3: Systemd Timer

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
Description=Run NetBox Meraki Scheduled Sync every minute

[Timer]
OnCalendar=*:0/1
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

##### Method 4: Continuous Service

Run as a persistent background service:

```bash
cd /opt/netbox
./venv/bin/python manage.py run_scheduled_sync --continuous --interval 60
```

Or create a systemd service:

```ini
[Unit]
Description=NetBox Meraki Scheduler Service
After=network.target

[Service]
Type=simple
User=netbox
WorkingDirectory=/opt/netbox
ExecStart=/opt/netbox/venv/bin/python /opt/netbox/netbox/manage.py run_scheduled_sync --continuous
Restart=always

[Install]
WantedBy=multi-user.target
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
│   ├── templates/
│   ├── api/
│   ├── management/
│   └── migrations/
├── README.md
├── LICENSE
├── pyproject.toml
└── requirements.txt
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

# Fresh Installation Guide for NetBox Meraki Plugin

## For Docker NetBox Installation

### Step 1: Ensure Plugin is in Correct Location
```bash
cd /home/tdebnath/ra_netbox_meraki
```

### Step 2: Update Docker Compose Override
Add to your `docker-compose.override.yml`:

```yaml
services:
  netbox:
    volumes:
      - /home/tdebnath/ra_netbox_meraki:/opt/netbox/netbox/netbox_meraki:ro
```

### Step 3: Update NetBox Configuration
Add to your `configuration.py`:

```python
PLUGINS = [
    'netbox_meraki',
]

PLUGINS_CONFIG = {
    'netbox_meraki': {
        'meraki_api_key': 'your-meraki-api-key-here',  # Required
        # Optional overrides (these override database settings)
        # 'mx_device_role': 'Firewall',
        # 'ms_device_role': 'Switch',
        # 'mr_device_role': 'Access Point',
        # 'default_manufacturer': 'Cisco Meraki',
    }
}
```

### Step 4: Restart NetBox and Run Migrations
```bash
# If using docker-compose
cd /path/to/netbox-docker
docker-compose down
docker-compose up -d

# Wait for NetBox to start, then run migrations
docker-compose exec netbox python manage.py migrate netbox_meraki

# Create a superuser if needed
docker-compose exec netbox python manage.py createsuperuser
```

### Step 5: Verify Installation
1. Access NetBox web interface
2. Go to Plugins menu
3. Click on "Meraki Dashboard Sync"
4. You should see the dashboard

---

## For Standard (Non-Docker) Installation

### Step 1: Copy Plugin to NetBox
```bash
cp -r /home/tdebnath/ra_netbox_meraki/netbox_meraki /opt/netbox/netbox/
```

### Step 2: Activate Virtual Environment
```bash
source /opt/netbox/venv/bin/activate
```

### Step 3: Update Configuration
Edit `/opt/netbox/netbox/netbox/configuration.py`:

```python
PLUGINS = [
    'netbox_meraki',
]

PLUGINS_CONFIG = {
    'netbox_meraki': {
        'meraki_api_key': 'your-meraki-api-key-here',
    }
}
```

### Step 4: Run Migrations
```bash
cd /opt/netbox/netbox
python manage.py migrate netbox_meraki
```

### Step 5: Restart NetBox Services
```bash
sudo systemctl restart netbox netbox-rq
```

---

## Post-Installation

### Configure Plugin Settings
1. Navigate to **Plugins → Meraki Dashboard Sync**
2. Click **View Configuration**
3. Configure:
   - Device roles (MX, MS, MR, MG, MV, MT)
   - Auto-creation settings
   - Site/Device name transformations
   - Tags for sites, devices, VLANs, prefixes

### Create Your First Sync
1. Click **Sync Now** on the dashboard
2. Select organization and networks
3. Choose sync mode:
   - **Auto Sync**: Immediate sync
   - **Review Mode**: Preview changes before applying
   - **Dry Run**: View what would be synced without changes

### Schedule Recurring Syncs
1. Click **Manage Scheduled Jobs** on the dashboard
2. Click **Schedule New Sync**
3. Configure:
   - Job name
   - Organization and networks
   - Sync interval (minutes)
   - Start time (optional)
4. Jobs will appear on the dashboard with Edit/Pause/Delete buttons

---

## Troubleshooting

### Migration Issues
If you see "No migrations to apply" but have model changes:

```bash
# Remove old migration
rm /home/tdebnath/ra_netbox_meraki/netbox_meraki/migrations/0001_initial.py

# Inside NetBox container or venv
python manage.py makemigrations netbox_meraki
python manage.py migrate netbox_meraki
```

### Plugin Not Showing
- Check NetBox logs: `docker-compose logs netbox` or `/var/log/netbox/`
- Verify configuration.py has correct syntax
- Ensure plugin path is mounted correctly in Docker

### API Connection Issues
- Verify Meraki API key is correct
- Check network connectivity to api.meraki.com
- Review sync logs for detailed error messages

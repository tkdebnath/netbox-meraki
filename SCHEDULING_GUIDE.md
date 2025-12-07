# NetBox Meraki Plugin - Scheduling Guide

## Overview

The NetBox Meraki plugin supports multiple methods for scheduling automatic synchronization:
1. **Built-in Scheduler** with cron/systemd integration
2. **Continuous Background Service**
3. **NetBox RQ/Celery Integration** (optional)
4. **Manual Cron Jobs**

## Quick Start

### 1. Enable Scheduling in NetBox UI

1. Navigate to **Plugins → Meraki → Configuration**
2. Click the **Scheduling** tab
3. Enable **"Enable Scheduled Sync"**
4. Set **Sync Interval** (minimum 5 minutes)
5. Choose **Scheduled Sync Mode** (auto/review/dry_run)
6. Click **Save Scheduling Settings**

### 2. Set Up Scheduler (Choose One Method)

## Method 1: Systemd Timer (Recommended for Linux)

### Continuous Service (Always Running)

**Install Service:**
```bash
# Copy service file
sudo cp deployment/systemd/netbox-meraki-scheduler.service /etc/systemd/system/

# Edit paths if needed
sudo nano /etc/systemd/system/netbox-meraki-scheduler.service

# Reload systemd
sudo systemctl daemon-reload

# Enable and start service
sudo systemctl enable netbox-meraki-scheduler.service
sudo systemctl start netbox-meraki-scheduler.service

# Check status
sudo systemctl status netbox-meraki-scheduler.service

# View logs
sudo journalctl -u netbox-meraki-scheduler.service -f
```

**Service Configuration:**
```ini
[Unit]
Description=NetBox Meraki Sync Scheduler
After=network.target netbox.service
Requires=netbox.service

[Service]
Type=simple
User=netbox
Group=netbox
WorkingDirectory=/opt/netbox/netbox
Environment="PYTHON=/opt/netbox/venv/bin/python"
ExecStart=/opt/netbox/venv/bin/python /opt/netbox/netbox/manage.py schedule_meraki_sync --continuous --interval 60
Restart=on-failure
RestartSec=30

[Install]
WantedBy=multi-user.target
```

### Timer-Based (Periodic Checks)

**Install Timer:**
```bash
# Copy both files
sudo cp deployment/systemd/netbox-meraki-scheduler-oneshot.service /etc/systemd/system/
sudo cp deployment/systemd/netbox-meraki-scheduler.timer /etc/systemd/system/

# Edit paths if needed
sudo nano /etc/systemd/system/netbox-meraki-scheduler-oneshot.service

# Reload systemd
sudo systemctl daemon-reload

# Enable and start timer
sudo systemctl enable netbox-meraki-scheduler.timer
sudo systemctl start netbox-meraki-scheduler.timer

# Check timer status
sudo systemctl list-timers netbox-meraki-scheduler.timer

# View logs
sudo journalctl -u netbox-meraki-scheduler-oneshot.service -f
```

**Timer Configuration:**
```ini
[Unit]
Description=NetBox Meraki Sync Timer

[Timer]
OnBootSec=5min
OnUnitActiveSec=5min
Unit=netbox-meraki-scheduler-oneshot.service

[Install]
WantedBy=timers.target
```

## Method 2: Cron Job (Universal)

### Setup Cron

**Edit crontab:**
```bash
crontab -e
```

**Add one of these lines:**

**Every 5 minutes:**
```cron
*/5 * * * * cd /opt/netbox/netbox && /opt/netbox/venv/bin/python manage.py schedule_meraki_sync >> /var/log/netbox/meraki-sync.log 2>&1
```

**Every 15 minutes:**
```cron
*/15 * * * * cd /opt/netbox/netbox && /opt/netbox/venv/bin/python manage.py schedule_meraki_sync >> /var/log/netbox/meraki-sync.log 2>&1
```

**Every 30 minutes:**
```cron
*/30 * * * * cd /opt/netbox/netbox && /opt/netbox/venv/bin/python manage.py schedule_meraki_sync >> /var/log/netbox/meraki-sync.log 2>&1
```

**Every hour:**
```cron
0 * * * * cd /opt/netbox/netbox && /opt/netbox/venv/bin/python manage.py schedule_meraki_sync >> /var/log/netbox/meraki-sync.log 2>&1
```

**Daily at 2:00 AM:**
```cron
0 2 * * * cd /opt/netbox/netbox && /opt/netbox/venv/bin/python manage.py schedule_meraki_sync >> /var/log/netbox/meraki-sync.log 2>&1
```

**Weekdays at 6:00 AM:**
```cron
0 6 * * 1-5 cd /opt/netbox/netbox && /opt/netbox/venv/bin/python manage.py schedule_meraki_sync >> /var/log/netbox/meraki-sync.log 2>&1
```

### Cron with Error Notifications

```cron
*/30 * * * * cd /opt/netbox/netbox && /opt/netbox/venv/bin/python manage.py schedule_meraki_sync 2>&1 | tee -a /var/log/netbox/meraki-sync.log | grep -i error && echo "Meraki sync error" | mail -s "NetBox Meraki Error" admin@example.com || true
```

## Method 3: Continuous Background Service

### Run Directly

**Start in background:**
```bash
cd /opt/netbox/netbox
nohup /opt/netbox/venv/bin/python manage.py schedule_meraki_sync --continuous --interval 60 >> /var/log/netbox/meraki-sync.log 2>&1 &
```

**With screen/tmux:**
```bash
screen -S meraki-sync
cd /opt/netbox/netbox
/opt/netbox/venv/bin/python manage.py schedule_meraki_sync --continuous --interval 60
# Press Ctrl+A, D to detach
```

**Reattach later:**
```bash
screen -r meraki-sync
```

## Method 4: Docker Integration

### Docker Compose

Add scheduler service to your `docker-compose.yml`:

```yaml
services:
  netbox:
    # ... existing netbox service ...
  
  meraki-scheduler:
    image: netboxcommunity/netbox:latest
    depends_on:
      - netbox
      - postgres
      - redis
    env_file: env/netbox.env
    command:
      - /opt/netbox/venv/bin/python
      - /opt/netbox/netbox/manage.py
      - schedule_meraki_sync
      - --continuous
      - --interval
      - "60"
    volumes:
      - ./configuration:/etc/netbox/config:z,ro
    restart: unless-stopped
```

## Management Commands

### schedule_meraki_sync

Main scheduling command that checks if sync should run based on settings.

**Usage:**
```bash
python manage.py schedule_meraki_sync [OPTIONS]
```

**Options:**

| Option | Description |
|--------|-------------|
| `--force` | Force sync even if not scheduled |
| `--continuous` | Run continuously, checking at regular intervals |
| `--interval SECONDS` | Check interval for continuous mode (default: 60) |

**Examples:**

**Single check (respects schedule):**
```bash
python manage.py schedule_meraki_sync
```

**Force sync (ignores schedule):**
```bash
python manage.py schedule_meraki_sync --force
```

**Continuous mode (checks every 60 seconds):**
```bash
python manage.py schedule_meraki_sync --continuous --interval 60
```

**Continuous mode (checks every 5 minutes):**
```bash
python manage.py schedule_meraki_sync --continuous --interval 300
```

## Configuration Settings

### Plugin Settings (via UI or Admin)

| Setting | Type | Default | Description |
|---------|------|---------|-------------|
| `enable_scheduled_sync` | Boolean | False | Enable automatic scheduled sync |
| `sync_interval_minutes` | Integer | 60 | Minutes between syncs (min: 5) |
| `scheduled_sync_mode` | Choice | auto | Mode for scheduled syncs (auto/review/dry_run) |
| `last_scheduled_sync` | DateTime | None | Last sync timestamp (auto-updated) |
| `next_scheduled_sync` | DateTime | None | Next sync timestamp (auto-calculated) |

### Accessing Settings Programmatically

```python
from netbox_meraki.models import PluginSettings

settings = PluginSettings.get_settings()

# Check if should run
if settings.should_run_scheduled_sync():
    # Run sync
    pass

# Update next sync time
settings.update_next_sync_time()
```

## Monitoring

### Check Scheduler Status

**Systemd service:**
```bash
sudo systemctl status netbox-meraki-scheduler.service
```

**Systemd timer:**
```bash
sudo systemctl list-timers netbox-meraki-scheduler.timer
```

**Cron logs:**
```bash
grep CRON /var/log/syslog | grep meraki
```

### View Sync Logs

**Application logs:**
```bash
tail -f /var/log/netbox/meraki-sync.log
```

**Systemd logs:**
```bash
sudo journalctl -u netbox-meraki-scheduler.service -f
```

**In NetBox UI:**
- Navigate to **Plugins → Meraki → Dashboard**
- View **Recent Sync Logs**
- Click on any log for detailed information

### Sync Statistics

Each scheduled sync logs:
- Start/end time
- Status (success/partial/failed)
- Objects synced (organizations, networks, devices, VLANs, prefixes)
- Objects deleted (orphaned cleanup)
- Errors encountered

## Troubleshooting

### Scheduler Not Running

**Check if enabled:**
```python
python manage.py shell
from netbox_meraki.models import PluginSettings
settings = PluginSettings.get_settings()
print(f"Enabled: {settings.enable_scheduled_sync}")
print(f"Next sync: {settings.next_scheduled_sync}")
```

**Check service status:**
```bash
# Systemd
sudo systemctl status netbox-meraki-scheduler.service

# Cron
sudo grep meraki /var/spool/cron/crontabs/*
```

### Sync Failing

**Check Meraki API key:**
```python
python manage.py shell
from netbox_meraki.models import PluginSettings
settings = PluginSettings.get_settings()
print(f"API Key configured: {bool(settings.meraki_api_key)}")
```

**Test manual sync:**
```bash
python manage.py sync_meraki --mode dry_run
```

**Check error logs:**
```bash
grep ERROR /var/log/netbox/meraki-sync.log
```

### Permission Issues

**Fix file permissions:**
```bash
sudo chown -R netbox:netbox /var/log/netbox/
sudo chmod 755 /var/log/netbox/
```

**Fix systemd service user:**
```bash
sudo nano /etc/systemd/system/netbox-meraki-scheduler.service
# Ensure User=netbox and Group=netbox
sudo systemctl daemon-reload
sudo systemctl restart netbox-meraki-scheduler.service
```

## Best Practices

### Production Environments

1. **Use Review Mode Initially**
   ```python
   scheduled_sync_mode = 'review'
   ```
   Review changes before applying in production.

2. **Set Reasonable Intervals**
   - Small deployments: 30-60 minutes
   - Large deployments: 2-4 hours
   - Avoid intervals < 15 minutes

3. **Monitor Sync Duration**
   - Check sync duration in logs
   - Adjust interval to avoid overlapping syncs

4. **Use Systemd for Reliability**
   - Auto-restart on failure
   - Integrated logging
   - Better process management

5. **Set Up Alerting**
   ```bash
   # Example: Alert on failed syncs
   */15 * * * * grep -q "status.*failed" /var/log/netbox/meraki-sync.log && echo "Meraki sync failed" | mail -s "Alert" admin@example.com
   ```

### Development/Testing

1. **Use Dry Run Mode**
   ```python
   scheduled_sync_mode = 'dry_run'
   ```

2. **Shorter Intervals**
   ```python
   sync_interval_minutes = 5
   ```

3. **Manual Triggers**
   ```bash
   python manage.py schedule_meraki_sync --force
   ```

## Advanced Configurations

### Multi-Organization Scheduling

Different intervals for different organizations (requires custom script):

```python
# custom_meraki_sync.py
from netbox_meraki.sync_service import MerakiSyncService

# Sync org A every hour
if should_sync_org_a():
    service = MerakiSyncService(api_key=ORG_A_KEY)
    service.sync_all()

# Sync org B every 4 hours
if should_sync_org_b():
    service = MerakiSyncService(api_key=ORG_B_KEY)
    service.sync_all()
```

### Off-Peak Scheduling

Run syncs during off-peak hours:

```cron
# Run every 15 minutes between 8PM and 6AM
*/15 20-23,0-6 * * * cd /opt/netbox/netbox && /opt/netbox/venv/bin/python manage.py schedule_meraki_sync
```

### Failure Notifications

Slack/Teams webhook on failure:

```bash
#!/bin/bash
OUTPUT=$(python manage.py schedule_meraki_sync 2>&1)
if echo "$OUTPUT" | grep -q "failed"; then
    curl -X POST -H 'Content-type: application/json' \
        --data '{"text":"Meraki sync failed!"}' \
        https://hooks.slack.com/services/YOUR/WEBHOOK/URL
fi
```

## Migration from Manual to Scheduled

1. **Test current manual sync:**
   ```bash
   python manage.py sync_meraki --mode dry_run
   ```

2. **Enable scheduling in UI**

3. **Set up scheduler (choose method)**

4. **Monitor first few runs**

5. **Disable manual syncs if satisfied**

## Summary

The plugin provides flexible scheduling options:

✅ **Built-in scheduler** respects NetBox settings  
✅ **Multiple deployment methods** (systemd/cron/continuous)  
✅ **Automatic cleanup** in scheduled syncs  
✅ **Comprehensive logging** and monitoring  
✅ **Configurable intervals** and sync modes  
✅ **Production-ready** with error handling  

Choose the method that best fits your infrastructure and operational requirements!

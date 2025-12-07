# Quick Reference - Scheduling Commands

## Enable Scheduling
**In NetBox UI:**
Plugins → Meraki → Configuration → Scheduling Tab → Enable → Save

## Management Command

### Basic Usage
```bash
# Check and run if scheduled
python manage.py schedule_meraki_sync

# Force run (ignore schedule)
python manage.py schedule_meraki_sync --force

# Run continuously (checks every 60 seconds)
python manage.py schedule_meraki_sync --continuous --interval 60
```

## Systemd Setup

### Continuous Service
```bash
# Install
sudo cp deployment/systemd/netbox-meraki-scheduler.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable netbox-meraki-scheduler.service
sudo systemctl start netbox-meraki-scheduler.service

# Monitor
sudo systemctl status netbox-meraki-scheduler.service
sudo journalctl -u netbox-meraki-scheduler.service -f
```

### Timer-Based
```bash
# Install
sudo cp deployment/systemd/netbox-meraki-scheduler-oneshot.service /etc/systemd/system/
sudo cp deployment/systemd/netbox-meraki-scheduler.timer /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable netbox-meraki-scheduler.timer
sudo systemctl start netbox-meraki-scheduler.timer

# Monitor
sudo systemctl list-timers netbox-meraki-scheduler.timer
sudo journalctl -u netbox-meraki-scheduler-oneshot.service -f
```

## Cron Setup

### Common Schedules
```bash
# Edit crontab
crontab -e

# Every 5 minutes
*/5 * * * * cd /opt/netbox/netbox && /opt/netbox/venv/bin/python manage.py schedule_meraki_sync >> /var/log/netbox/meraki-sync.log 2>&1

# Every 30 minutes
*/30 * * * * cd /opt/netbox/netbox && /opt/netbox/venv/bin/python manage.py schedule_meraki_sync >> /var/log/netbox/meraki-sync.log 2>&1

# Every hour
0 * * * * cd /opt/netbox/netbox && /opt/netbox/venv/bin/python manage.py schedule_meraki_sync >> /var/log/netbox/meraki-sync.log 2>&1

# Daily at 2 AM
0 2 * * * cd /opt/netbox/netbox && /opt/netbox/venv/bin/python manage.py schedule_meraki_sync >> /var/log/netbox/meraki-sync.log 2>&1
```

## Monitoring

### Check Status
```bash
# Systemd service
sudo systemctl status netbox-meraki-scheduler.service

# Systemd timer
sudo systemctl list-timers

# Cron
sudo grep meraki /var/spool/cron/crontabs/*
```

### View Logs
```bash
# Application log
tail -f /var/log/netbox/meraki-sync.log

# Systemd journal
sudo journalctl -u netbox-meraki-scheduler.service -f

# Last 50 lines
sudo journalctl -u netbox-meraki-scheduler.service -n 50
```

### Check Settings
```python
python manage.py shell
from netbox_meraki.models import PluginSettings
s = PluginSettings.get_settings()
print(f"Enabled: {s.enable_scheduled_sync}")
print(f"Interval: {s.sync_interval_minutes} minutes")
print(f"Mode: {s.scheduled_sync_mode}")
print(f"Last sync: {s.last_scheduled_sync}")
print(f"Next sync: {s.next_scheduled_sync}")
```

## Troubleshooting

### Not Running
```bash
# Check if enabled
python manage.py shell -c "from netbox_meraki.models import PluginSettings; print(PluginSettings.get_settings().enable_scheduled_sync)"

# Check service
sudo systemctl status netbox-meraki-scheduler.service

# Restart service
sudo systemctl restart netbox-meraki-scheduler.service
```

### Errors
```bash
# View recent errors
grep ERROR /var/log/netbox/meraki-sync.log | tail -20

# Test manual sync
python manage.py sync_meraki --mode dry_run
```

### Permissions
```bash
# Fix log directory
sudo mkdir -p /var/log/netbox
sudo chown -R netbox:netbox /var/log/netbox
sudo chmod 755 /var/log/netbox
```

## Quick Migration

```bash
# 1. Run migration
python manage.py migrate netbox_meraki

# 2. Enable in UI (or via shell)
python manage.py shell
from netbox_meraki.models import PluginSettings
s = PluginSettings.get_settings()
s.enable_scheduled_sync = True
s.sync_interval_minutes = 60
s.scheduled_sync_mode = 'auto'
s.save()
exit()

# 3. Install systemd service (recommended)
sudo cp deployment/systemd/netbox-meraki-scheduler.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now netbox-meraki-scheduler.service

# 4. Verify
sudo systemctl status netbox-meraki-scheduler.service
```

## Docker Compose Addition

```yaml
  meraki-scheduler:
    image: netboxcommunity/netbox:latest
    depends_on: [netbox, postgres, redis]
    env_file: env/netbox.env
    command: ["/opt/netbox/venv/bin/python", "/opt/netbox/netbox/manage.py", 
              "schedule_meraki_sync", "--continuous", "--interval", "60"]
    volumes: ["./configuration:/etc/netbox/config:z,ro"]
    restart: unless-stopped
```

## See Also
- **SCHEDULING_GUIDE.md** - Complete documentation
- **SYNC_BEHAVIOR.md** - Sync behavior and cleanup
- **README.md** - General plugin information

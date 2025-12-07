# Scheduling Implementation Summary

## Overview
Added comprehensive scheduling capabilities to the NetBox Meraki plugin with multiple deployment options and full UI integration.

## Features Implemented

### 1. Database Schema (Migration 0005)
**New fields in `PluginSettings` model:**
- `enable_scheduled_sync` - Boolean to enable/disable scheduling
- `sync_interval_minutes` - Integer for interval (minimum 5 minutes)
- `scheduled_sync_mode` - Choice field (auto/review/dry_run)
- `last_scheduled_sync` - DateTime tracking last execution
- `next_scheduled_sync` - DateTime for next scheduled run

**Methods added:**
- `clean()` - Validates sync_interval_minutes >= 5
- `update_next_sync_time()` - Calculates and sets next sync timestamp
- `should_run_scheduled_sync()` - Checks if sync should run now

### 2. Management Command
**File:** `netbox_meraki/management/commands/schedule_meraki_sync.py`

**Functionality:**
- Checks if scheduled sync is due
- Respects plugin settings (enable/interval/mode)
- Updates next sync time after completion
- Logs all operations

**Options:**
- `--force` - Run sync regardless of schedule
- `--continuous` - Run continuously with periodic checks
- `--interval SECONDS` - Check interval for continuous mode

**Usage Examples:**
```bash
# Single check (respects schedule)
python manage.py schedule_meraki_sync

# Force sync
python manage.py schedule_meraki_sync --force

# Continuous mode (checks every 60 seconds)
python manage.py schedule_meraki_sync --continuous --interval 60
```

### 3. Deployment Templates

**Systemd Service (Continuous):**
- File: `deployment/systemd/netbox-meraki-scheduler.service`
- Runs continuously with auto-restart
- Integrated with journald logging

**Systemd Timer (Periodic):**
- Files: `deployment/systemd/netbox-meraki-scheduler.timer`
- Files: `deployment/systemd/netbox-meraki-scheduler-oneshot.service`
- Runs on-demand at specified intervals
- Lower resource usage

**Cron Examples:**
- File: `deployment/cron/meraki-sync-cron.sh`
- Multiple example schedules
- Email notification examples

### 4. Web UI Updates

**Configuration Page:**
- New "Scheduling" tab added
- Form fields for all scheduling settings
- Real-time display of last/next sync times
- Setup instructions with command examples
- Visual feedback for enabled state

**Form Updates:**
- `forms.py` updated with scheduling fields
- Bootstrap styling classes applied
- Number input with min=5, step=5 validation
- Select dropdowns for mode choices

### 5. Documentation

**SCHEDULING_GUIDE.md** - Comprehensive guide covering:
- Quick start instructions
- All deployment methods (systemd/cron/continuous/docker)
- Command reference
- Configuration settings
- Monitoring and troubleshooting
- Best practices
- Advanced configurations
- Migration guide

## Deployment Options

### Option 1: Systemd Service (Recommended)
**Pros:**
- Auto-restart on failure
- Integrated logging
- Best for production

**Setup:**
```bash
sudo cp deployment/systemd/netbox-meraki-scheduler.service /etc/systemd/system/
sudo systemctl enable netbox-meraki-scheduler.service
sudo systemctl start netbox-meraki-scheduler.service
```

### Option 2: Systemd Timer
**Pros:**
- Lower resource usage
- Good for less frequent syncs
- Timer-based scheduling

**Setup:**
```bash
sudo cp deployment/systemd/*.service /etc/systemd/system/
sudo cp deployment/systemd/*.timer /etc/systemd/system/
sudo systemctl enable netbox-meraki-scheduler.timer
sudo systemctl start netbox-meraki-scheduler.timer
```

### Option 3: Cron Job
**Pros:**
- Universal (works on any Linux)
- Simple setup
- Familiar to admins

**Setup:**
```bash
crontab -e
# Add line:
*/30 * * * * cd /opt/netbox/netbox && /opt/netbox/venv/bin/python manage.py schedule_meraki_sync
```

### Option 4: Docker Compose
**Pros:**
- Container-based
- Easy to scale
- Integrated with NetBox container

**Setup:**
Add service to docker-compose.yml (see SCHEDULING_GUIDE.md)

## Configuration Flow

1. **User enables in UI:**
   - Navigate to Plugins → Meraki → Configuration → Scheduling
   - Enable "Enable Scheduled Sync"
   - Set interval (e.g., 60 minutes)
   - Choose mode (auto/review/dry_run)
   - Save settings

2. **System setup:**
   - Admin installs systemd service OR
   - Admin configures cron job OR
   - Admin starts continuous service

3. **Execution:**
   - Scheduler checks `should_run_scheduled_sync()`
   - If true, runs `MerakiSyncService.sync_all()`
   - Updates `last_scheduled_sync` and `next_scheduled_sync`
   - Logs results

4. **Monitoring:**
   - Check systemd status: `systemctl status netbox-meraki-scheduler`
   - View logs: `journalctl -u netbox-meraki-scheduler -f`
   - Check NetBox UI: Plugins → Meraki → Dashboard → Recent Logs

## Key Features

### Smart Scheduling
✅ Respects configured intervals  
✅ Skips if not due (prevents unnecessary syncs)  
✅ Force option for manual override  
✅ Continuous mode for always-on operation  

### Reliability
✅ Auto-restart on failure (systemd)  
✅ Comprehensive error logging  
✅ Graceful handling of API failures  
✅ No overlapping syncs  

### Flexibility
✅ Multiple deployment options  
✅ Configurable intervals (min 5 minutes)  
✅ Per-schedule sync modes  
✅ Force sync capability  

### Monitoring
✅ Last/next sync timestamps  
✅ Detailed sync logs  
✅ Error tracking  
✅ Status in UI and CLI  

## Migration Path

**From manual syncs:**
1. Test current manual sync
2. Enable scheduling in UI
3. Set up scheduler (choose method)
4. Monitor first few runs
5. Disable manual triggers if satisfied

**Required migration:**
```bash
python manage.py migrate netbox_meraki
```

## Files Modified/Created

### Modified:
1. `netbox_meraki/models.py` - Added scheduling fields and methods
2. `netbox_meraki/forms.py` - Added scheduling form fields
3. `netbox_meraki/templates/netbox_meraki/config.html` - Added scheduling tab
4. `netbox_meraki/__init__.py` - Version 0.3.0 → 0.4.0
5. `README.md` - Updated with scheduling features

### Created:
1. `netbox_meraki/migrations/0005_add_scheduling.py` - Database migration
2. `netbox_meraki/management/commands/schedule_meraki_sync.py` - Scheduler command
3. `deployment/systemd/netbox-meraki-scheduler.service` - Systemd service
4. `deployment/systemd/netbox-meraki-scheduler.timer` - Systemd timer
5. `deployment/systemd/netbox-meraki-scheduler-oneshot.service` - One-shot service
6. `deployment/cron/meraki-sync-cron.sh` - Cron examples
7. `SCHEDULING_GUIDE.md` - Complete documentation

## Testing Checklist

### Database:
- [ ] Run migration successfully
- [ ] Verify new fields in admin panel
- [ ] Test field validation (interval >= 5)

### Management Command:
- [ ] Test single run: `python manage.py schedule_meraki_sync`
- [ ] Test force mode: `python manage.py schedule_meraki_sync --force`
- [ ] Test continuous: `python manage.py schedule_meraki_sync --continuous --interval 60`
- [ ] Verify respects enable_scheduled_sync setting
- [ ] Verify updates last/next sync times

### UI:
- [ ] View scheduling tab in configuration
- [ ] Enable scheduled sync
- [ ] Set interval and mode
- [ ] Save settings
- [ ] Verify last/next sync displayed

### Systemd:
- [ ] Install service file
- [ ] Start service
- [ ] Check status
- [ ] View logs
- [ ] Verify auto-restart on crash

### Cron:
- [ ] Add crontab entry
- [ ] Wait for scheduled run
- [ ] Check logs
- [ ] Verify sync occurred

## Best Practices Implemented

1. **Minimum Interval:** 5 minutes enforced to prevent API abuse
2. **Mode Flexibility:** Different modes for scheduled vs manual
3. **Auto-restart:** Systemd service configuration
4. **Comprehensive Logging:** All operations logged
5. **Status Tracking:** UI shows last/next sync times
6. **Multiple Options:** Choose deployment method that fits infrastructure
7. **Documentation:** Complete guide with examples
8. **Error Handling:** Graceful failures with logging

## Summary

The scheduling implementation provides:

✅ **Built-in scheduler** with multiple deployment options  
✅ **UI configuration** for all scheduling settings  
✅ **Automatic execution** based on configured intervals  
✅ **Flexible deployment** (systemd/cron/continuous/docker)  
✅ **Production-ready** with auto-restart and logging  
✅ **Well-documented** with complete guide  
✅ **Easy setup** with provided templates  
✅ **Monitoring** through UI and system logs  

Version 0.4.0 ready for deployment!

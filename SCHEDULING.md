# NetBox Meraki Scheduled Sync Setup

## Overview

The NetBox Meraki plugin includes a comprehensive scheduling system that allows you to automate synchronization tasks with full control over timing, frequency, and sync options.

## Features

✅ **Flexible Scheduling**: One-time, hourly, daily, or weekly execution
✅ **Full Sync Control**: Same options as "Sync Now" page (mode, networks, components)
✅ **Task Queue Management**: View, edit, enable/disable, and delete scheduled tasks
✅ **Execution Tracking**: Monitor success rate, last run, next run, and error details
✅ **Multiple Sync Modes**: Full sync, selective networks, or single network
✅ **Component Selection**: Choose which objects to sync (devices, VLANs, prefixes, etc.)

## Quick Start

### 1. Access Scheduling Page

Navigate to: **Plugins > Meraki Sync > Dashboard** → Click **Scheduled Sync**

Or go directly to: **Plugins > Meraki Sync > Scheduled Sync**

### 2. Create Your First Task

1. Click **Create New Task** button
2. Enter task details:
   - **Name**: "Daily Full Sync" (or your preferred name)
   - **Frequency**: Daily
   - **Start Date/Time**: Select when you want it to start

3. Configure sync settings:
   - **Sync Mode**: Full Sync (or choose Selective/Single Network)
   - **Sync Components**: Check all (Organizations, Sites, Devices, VLANs, Prefixes)
   - **Cleanup Orphaned**: Optional (removes objects deleted from Meraki)
   - **Enable Task**: Checked

4. Click **Create Task**

### 3. Set Up Task Executor

Choose ONE of these methods to run scheduled tasks:

#### Option A: Cron Job (Simplest)

Add to crontab (`crontab -e`):

```bash
* * * * * cd /opt/netbox && /opt/netbox/venv/bin/python manage.py run_scheduled_sync >> /var/log/netbox/meraki-scheduler.log 2>&1
```

This checks for due tasks every minute.

#### Option B: Systemd Timer (Recommended for Production)

1. Create service file: `/etc/systemd/system/netbox-meraki-scheduler.service`

```ini
[Unit]
Description=NetBox Meraki Scheduled Sync
After=network.target

[Service]
Type=oneshot
User=netbox
Group=netbox
WorkingDirectory=/opt/netbox
Environment="PYTHONPATH=/opt/netbox/netbox"
ExecStart=/opt/netbox/venv/bin/python /opt/netbox/netbox/manage.py run_scheduled_sync
StandardOutput=journal
StandardError=journal
```

2. Create timer file: `/etc/systemd/system/netbox-meraki-scheduler.timer`

```ini
[Unit]
Description=Run NetBox Meraki Scheduled Sync Check

[Timer]
OnCalendar=*:0/1
Persistent=true

[Install]
WantedBy=timers.target
```

3. Enable and start:

```bash
sudo systemctl daemon-reload
sudo systemctl enable netbox-meraki-scheduler.timer
sudo systemctl start netbox-meraki-scheduler.timer
sudo systemctl status netbox-meraki-scheduler.timer
```

#### Option C: Continuous Service (Alternative)

Run as a persistent background process:

```bash
cd /opt/netbox
./venv/bin/python manage.py run_scheduled_sync --continuous --interval 60 &
```

Or create systemd service:

```ini
[Unit]
Description=NetBox Meraki Scheduler Daemon
After=network.target

[Service]
Type=simple
User=netbox
Group=netbox
WorkingDirectory=/opt/netbox
Environment="PYTHONPATH=/opt/netbox/netbox"
ExecStart=/opt/netbox/venv/bin/python /opt/netbox/netbox/manage.py run_scheduled_sync --continuous
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

Enable: `sudo systemctl enable --now netbox-meraki-scheduler.service`

## Task Management

### View Task Queue

The main scheduling page shows all tasks with:

- **Name**: Task identifier
- **Frequency**: How often it runs (one-time, hourly, daily, weekly)
- **Next Run**: When it will execute next
- **Last Run**: Most recent execution time
- **Status**: Pending, Running, Completed, Failed, Cancelled
- **Success Rate**: Historical success percentage
- **Enabled**: Whether task is active

### Edit a Task

1. Click the **Edit** (pencil) button
2. Modify any settings (name, frequency, schedule, sync options)
3. Click **Save Changes**

### Enable/Disable a Task

- Click the **Pause** button to disable an enabled task
- Click the **Play** button to enable a disabled task
- Disabled tasks won't run even if they're scheduled

### Delete a Task

1. Click the **Delete** (trash) button
2. Confirm deletion in the popup

## Task Configuration Options

### Sync Mode

- **Full Sync**: Synchronize all organizations and networks
- **Selective Networks**: Sync specific networks only
- **Single Network**: Sync just one network

### Sync Components

Toggle what objects to synchronize:

- ✅ **Organizations**: Sync Meraki organizations
- ✅ **Sites/Networks**: Sync networks as NetBox sites
- ✅ **Devices**: Sync Meraki devices
- ✅ **VLANs**: Sync VLAN configuration
- ✅ **Prefixes**: Sync subnet/prefix data

### Cleanup Options

- **Cleanup Orphaned Objects**: Remove NetBox objects that no longer exist in Meraki
  - Only removes objects from synced networks
  - Safe to use with selective sync

### Frequency Options

- **One Time**: Runs once at scheduled time, then stops
- **Hourly**: Repeats every hour
- **Daily**: Repeats every 24 hours
- **Weekly**: Repeats every 7 days

## Monitoring

### Task Status

- **Pending**: Waiting for scheduled time
- **Running**: Currently executing
- **Completed**: Last run succeeded
- **Failed**: Last run encountered errors (shows error message)
- **Cancelled**: Task was manually cancelled

### Success Rate

Calculated as: `(Successful Runs / Total Runs) × 100%`

### Error Handling

- Failed tasks display error message
- Tasks automatically retry at next scheduled time
- Failed tasks don't block other tasks

## Best Practices

1. **Start Small**: Create one task, verify it works, then add more
2. **Stagger Schedules**: Don't schedule all tasks at the same time
3. **Monitor Logs**: Check logs regularly for errors
4. **Test First**: Use "Sync Now" with review mode before scheduling
5. **Use Cleanup Carefully**: Only enable if you want automated deletion

## Troubleshooting

### Task Not Running

1. Check task is **Enabled** (green badge)
2. Verify **Next Run** time is in the future
3. Confirm scheduler is running (cron/systemd)
4. Check NetBox logs: `/var/log/netbox/`

### Task Fails Repeatedly

1. View error message in task list
2. Check Meraki API key is valid
3. Verify network connectivity
4. Try manual sync with same options
5. Check NetBox logs for detailed error

### Scheduler Not Starting

1. Verify Python path: `which python` or `/opt/netbox/venv/bin/python`
2. Check permissions: `ls -la /opt/netbox/venv/bin/python`
3. Test manually: `cd /opt/netbox && ./venv/bin/python manage.py run_scheduled_sync`
4. Check systemd logs: `sudo journalctl -u netbox-meraki-scheduler -f`

### Task Stuck in "Running"

1. Task may have crashed - check logs
2. Reset status: Edit task and save (updates status)
3. Or delete and recreate the task

## Docker-Specific Notes

If NetBox runs in Docker:

1. Execute commands inside container:
   ```bash
   docker exec -it netbox python manage.py run_scheduled_sync
   ```

2. Set up cron in container or use host cron with docker exec:
   ```bash
   * * * * * docker exec netbox python manage.py run_scheduled_sync >> /var/log/meraki-scheduler.log 2>&1
   ```

3. Or create a separate scheduler container that shares NetBox's database

## Advanced Usage

### Custom Intervals

For non-standard intervals, create multiple tasks:

- Every 6 hours: Create 4 tasks, staggered by 6 hours
- Every 15 minutes: Use cron with management command directly

### Selective Network Sync

1. Choose **Selective Networks** mode
2. Select specific networks from dropdown
3. Only those networks will sync
4. Perfect for testing or gradual rollout

### Network-Specific Schedules

Create separate tasks for different networks:

- Task 1: HQ Network - Hourly
- Task 2: Branch Networks - Daily
- Task 3: Test Networks - Weekly

## Support

For issues or questions:

- **GitHub Issues**: https://github.com/tkdebnath/netbox-meraki/issues
- **Documentation**: https://github.com/tkdebnath/netbox-meraki
- **Plugin Author**: Tarani Debnath

---

**Created by**: Tarani Debnath  
**Repository**: https://github.com/tkdebnath/netbox-meraki

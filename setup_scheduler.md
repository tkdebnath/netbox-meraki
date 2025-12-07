# Setting Up Scheduled Task Execution

Your scheduled task didn't run because the **ExecuteScheduledTasksJob** isn't set up to run automatically.

## Method 1: NetBox Scheduled Jobs (Recommended)

1. **Navigate to NetBox Admin:**
   - Go to: http://your-netbox/admin/extras/scheduledjob/

2. **Create a new Scheduled Job:**
   - Click **"Add Scheduled Job"**
   - **Name:** Execute Meraki Scheduled Tasks
   - **Job:** Select `netbox_meraki.jobs.ExecuteScheduledTasksJob`
   - **Interval:** Custom (see below)
   - **Enabled:** ✓ Check this

3. **Set the Interval:**
   - Click "Show" next to "Custom interval"
   - Set **minutes** to: `5` or `10`
   - This means the job runs every 5-10 minutes to check for due tasks

4. **Save**

## Method 2: System Cron (Alternative)

If NetBox scheduled jobs aren't working, use system cron:

```bash
# Edit crontab
sudo crontab -e

# Add this line (runs every 5 minutes)
*/5 * * * * /opt/netbox/venv/bin/python /opt/netbox/netbox/manage.py runjob netbox_meraki.ExecuteScheduledTasksJob
```

## Method 3: Systemd Timer (Alternative)

Create two files:

**File: /etc/systemd/system/netbox-meraki-scheduler.service**
```ini
[Unit]
Description=NetBox Meraki Scheduled Task Executor
After=network.target

[Service]
Type=oneshot
User=netbox
WorkingDirectory=/opt/netbox/netbox
ExecStart=/opt/netbox/venv/bin/python manage.py runjob netbox_meraki.ExecuteScheduledTasksJob

[Install]
WantedBy=multi-user.target
```

**File: /etc/systemd/system/netbox-meraki-scheduler.timer**
```ini
[Unit]
Description=Run NetBox Meraki Scheduler every 5 minutes
Requires=netbox-meraki-scheduler.service

[Timer]
OnBootSec=5min
OnUnitActiveSec=5min
AccuracySec=1min

[Install]
WantedBy=timers.target
```

Then enable and start:
```bash
sudo systemctl daemon-reload
sudo systemctl enable netbox-meraki-scheduler.timer
sudo systemctl start netbox-meraki-scheduler.timer
```

## Verification

After setting up, check if it's working:

1. **Check NetBox Logs:**
   ```bash
   # Check for execution messages
   journalctl -u netbox -f | grep "ExecuteScheduledTasksJob"
   ```

2. **View Job Results in NetBox:**
   - Go to: **Jobs → Job Results**
   - Look for "Execute Scheduled Sync Tasks" entries

3. **Check Task History:**
   - Go to your scheduled task edit page
   - Look at **Task History** - it should show runs

## Current Task Status

Your task shows:
- **Next Run:** 2025-12-07 09:51:00
- **Total Runs:** 0
- **Status:** Enabled ✓

This means:
- ✓ Task is enabled
- ✗ ExecuteScheduledTasksJob hasn't run yet (0 total runs)
- The task was scheduled to run at 09:51, but nothing executed it

**Solution:** Set up ExecuteScheduledTasksJob using Method 1 above!

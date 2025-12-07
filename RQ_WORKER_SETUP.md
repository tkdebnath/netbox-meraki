# RQ Worker Setup for Scheduled Tasks

## Issue
The **Execute Scheduled Sync Tasks** job is not running because the NetBox RQ (Redis Queue) worker is not active.

## Why RQ Worker is Required
The `@system_job` decorator requires an RQ worker to execute background jobs. Without it:
- Scheduled tasks will not execute at their scheduled times
- The ExecuteScheduledTasksJob will appear as "Scheduled" but never run
- Background job processing is disabled

## Solution

### Option 1: Start RQ Worker with Systemd (Recommended for Production)

If NetBox was installed with systemd services:

```bash
# Start the RQ worker
sudo systemctl start netbox-rq

# Enable it to start on boot
sudo systemctl enable netbox-rq

# Check status
sudo systemctl status netbox-rq

# View logs
journalctl -u netbox-rq -f
```

### Option 2: Start RQ Worker Manually

If systemd service doesn't exist, start RQ worker manually:

```bash
# Navigate to NetBox directory
cd /opt/netbox/netbox

# Start RQ worker (replace with your NetBox path if different)
python manage.py rqworker --with-scheduler

# Or run in background
nohup python manage.py rqworker --with-scheduler > /tmp/netbox-rq.log 2>&1 &
```

### Option 3: Docker Setup

If running NetBox in Docker:

```bash
# Check if netbox-rq container is running
docker ps | grep netbox-rq

# If not running, start it
docker-compose up -d netbox-rq

# View logs
docker logs -f netbox-rq
```

### Option 4: Create Systemd Service (if doesn't exist)

Create `/etc/systemd/system/netbox-rq.service`:

```ini
[Unit]
Description=NetBox RQ Worker
Documentation=https://docs.netbox.dev/
After=network-online.target redis.service
Wants=network-online.target

[Service]
Type=simple
User=netbox
WorkingDirectory=/opt/netbox/netbox
Environment="PYTHONUNBUFFERED=1"
ExecStart=/opt/netbox/venv/bin/python manage.py rqworker --with-scheduler
Restart=always
RestartSec=30
PrivateTmp=true

[Install]
WantedBy=multi-user.target
```

Then:
```bash
sudo systemctl daemon-reload
sudo systemctl enable netbox-rq
sudo systemctl start netbox-rq
```

## Verification

### 1. Check if RQ Worker is Running

```bash
# Check process
ps aux | grep rqworker

# Check systemd status
systemctl status netbox-rq
```

### 2. Check NetBox Jobs Interface

1. Go to NetBox → Jobs → Job Results
2. Look for "Execute Scheduled Sync Tasks" 
3. It should show as "Scheduled" and execute every minute
4. After it's hidden (with `hidden=True`), check logs instead

### 3. Check Logs

```bash
# If using systemd
journalctl -u netbox-rq -f | grep -i scheduled

# If manual/background
tail -f /tmp/netbox-rq.log | grep -i scheduled

# Check NetBox logs
tail -f /var/log/netbox/netbox.log | grep -i scheduled
```

### 4. Verify Task Execution

Check your scheduled tasks in the plugin:
- Next Run time should update after execution
- Last Run should show recent execution time
- Status should change from "pending" to "running" to "completed"

## Troubleshooting

### Tasks Still Not Running

1. **Check Redis is running:**
   ```bash
   systemctl status redis
   # or
   redis-cli ping
   ```

2. **Check NetBox configuration:**
   ```bash
   grep -i redis /opt/netbox/netbox/netbox/configuration.py
   ```

3. **Verify job is registered:**
   ```bash
   cd /opt/netbox/netbox
   python manage.py shell
   ```
   ```python
   from core.models import Job
   Job.objects.filter(name__icontains='scheduled').values('name', 'enabled', 'installed')
   ```

4. **Check for errors in RQ worker logs**

### Manual Test

You can manually trigger the job:

```bash
cd /opt/netbox/netbox
python manage.py shell
```

```python
from netbox_meraki.jobs import ExecuteScheduledTasksJob
job = ExecuteScheduledTasksJob()
result = job.run()
print(result)
```

## Expected Behavior

Once RQ worker is running:

1. **Every minute**, ExecuteScheduledTasksJob checks for due tasks
2. Tasks with `next_run <= current_time` are executed
3. After execution:
   - `last_run` is updated
   - `next_run` is calculated based on frequency
   - `status` changes (pending → running → completed/failed)
   - `total_runs` and `successful_runs` are incremented

## Important Notes

- The job is set to `hidden=True` so it won't clutter the Jobs list
- It runs automatically in the background every minute
- You don't need to manually schedule it in the Jobs interface
- Requires NetBox v4.2+ for `@system_job` support

## Alternative: Cron-based Execution

If you cannot run RQ worker, you can use cron instead (less efficient):

```bash
# Edit crontab
crontab -e

# Add this line to run every minute
* * * * * cd /opt/netbox/netbox && /opt/netbox/venv/bin/python manage.py shell -c "from netbox_meraki.jobs import ExecuteScheduledTasksJob; ExecuteScheduledTasksJob().run()" >> /tmp/netbox-scheduled-sync.log 2>&1
```

However, this approach:
- Doesn't use NetBox's job tracking
- Doesn't integrate with the Jobs interface
- Less efficient than RQ worker
- RQ worker is strongly recommended

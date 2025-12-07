# Name Transformations & NetBox Jobs Guide

## Overview

Version 0.5.0 introduces two major features:
1. **Name Transformations** - Control how names are formatted when syncing from Meraki
2. **NetBox Job Integration** - Use NetBox's built-in job system for scheduling and monitoring

## Name Transformations

### Feature Description

Control how object names are transformed when syncing from Meraki Dashboard to NetBox. Each object type (devices, sites, VLANs, SSIDs) can have its own transformation rule.

### Transformation Options

| Option | Description | Example |
|--------|-------------|---------|
| **Keep Original** | No transformation applied | `Switch-Floor1` |
| **UPPERCASE** | Convert to uppercase | `SWITCH-FLOOR1` |
| **lowercase** | Convert to lowercase | `switch-floor1` |
| **Title Case** | Capitalize first letter of each word | `Switch-Floor1` |

### Configuration

**Via Web UI:**
1. Navigate to **Plugins → Meraki → Configuration**
2. Click **Name Transformations** tab
3. Select transformation for each object type:
   - Device Names
   - Site/Network Names
   - VLAN Names
   - SSID Names
4. Click **Save Name Transformation Settings**

**Via Django Admin:**
1. Navigate to **Admin → Netbox_Meraki → Plugin Settings**
2. Configure transformation fields
3. Save

### How It Works

**Order of Operations:**
1. **Sites**: Regex rules applied first, then transformation
2. **Devices**: Transformation applied to device name from Meraki
3. **VLANs**: Transformation applied to VLAN name
4. **SSIDs**: Transformation applied to SSID names

**Example Flow:**
```
Meraki Network Name: "asia-south-mumbai-oil"
↓
Regex Rule: Extract "mumbai"
↓
Site Name Transform: UPPERCASE
↓
NetBox Site: "MUMBAI"
```

### Use Cases

**Standardize Device Names:**
```
Meraki: "switch-floor1", "SWITCH-FLOOR2", "Switch-Floor3"
Transform: UPPERCASE
Result: "SWITCH-FLOOR1", "SWITCH-FLOOR2", "SWITCH-FLOOR3"
```

**Normalize Site Names:**
```
Meraki: "New York Office", "NEW YORK BRANCH", "new york dc"
Transform: Title Case
Result: "New York Office", "New York Branch", "New York Dc"
```

**Consistent VLAN Names:**
```
Meraki: "Management", "GUEST", "iot"
Transform: lowercase
Result: "management", "guest", "iot"
```

**SSID Formatting:**
```
Meraki: "Guest-WiFi", "EMPLOYEE-WIFI", "iot-devices"
Transform: Title Case
Result: "Guest-Wifi", "Employee-Wifi", "Iot-Devices"
```

### Important Notes

⚠️ **Existing Objects:**
- Name transformations apply only to new syncs
- Existing objects are NOT automatically renamed
- To update existing objects, delete and re-sync

⚠️ **Site Name Rules:**
- Transformations apply AFTER regex rules
- Regex rules process Meraki names first
- Then transformation is applied to result

⚠️ **Case Sensitivity:**
- NetBox searches may be case-sensitive
- Choose transformations that match your conventions
- "keep" is safest for initial setup

## NetBox Job Integration

### Feature Description

The plugin now integrates with NetBox's built-in job system, providing:
- Native NetBox UI for job management
- Job scheduling with NetBox's scheduler
- Status tracking and history
- Detailed logging in NetBox UI
- Queue management

### Available Jobs

#### 1. Meraki Dashboard Sync
**Class:** `MerakiSyncJob`  
**Purpose:** Manual sync execution via NetBox Jobs UI  
**Scheduling:** Enabled  
**Queue:** default  

**Features:**
- Syncs all data from Meraki Dashboard
- Uses default sync mode from settings
- Detailed progress logging
- Error reporting in job results

**Usage:**
1. Navigate to **Jobs → Jobs**
2. Find "Meraki Dashboard Sync"
3. Click **Run Job**
4. Optionally schedule for later execution
5. View results and logs in job detail

#### 2. Scheduled Meraki Dashboard Sync
**Class:** `ScheduledMerakiSyncJob`  
**Purpose:** Scheduled sync that respects scheduling settings  
**Scheduling:** Enabled  
**Queue:** default  

**Features:**
- Checks if sync is due based on settings
- Uses scheduled sync mode
- Updates next sync time automatically
- Skips if not due (reports next sync time)

**Usage:**
1. Enable scheduling in plugin configuration
2. Navigate to **Jobs → Jobs**
3. Find "Scheduled Meraki Dashboard Sync"
4. Click **Add Schedule**
5. Configure schedule (interval, cron, etc.)
6. Job runs automatically per schedule

### Setting Up Job Scheduling

#### Method 1: Interval-Based Schedule

**Steps:**
1. Go to **Jobs → Jobs**
2. Find "Scheduled Meraki Dashboard Sync"
3. Click **Add Schedule** button
4. Configure:
   - **Name**: `Hourly Meraki Sync`
   - **Interval**: `Every hour`
   - **Start time**: Choose start time
   - **Enabled**: ✓
5. Save

**Example Intervals:**
- Every 30 minutes
- Every hour
- Every 4 hours
- Every day at 2:00 AM

#### Method 2: Cron-Based Schedule

**Steps:**
1. Go to **Jobs → Jobs**
2. Find job and click **Add Schedule**
3. Configure:
   - **Name**: `Daily Sync at 2 AM`
   - **Cron expression**: `0 2 * * *`
   - **Enabled**: ✓
4. Save

**Example Cron Expressions:**
```
0 * * * *       # Every hour
*/30 * * * *    # Every 30 minutes
0 2 * * *       # Daily at 2:00 AM
0 6 * * 1-5     # Weekdays at 6:00 AM
0 0 * * 0       # Sundays at midnight
```

### Viewing Job Results

**Job List:**
1. Navigate to **Jobs → Job Results**
2. Filter by job name
3. View status (pending/running/completed/errored/failed)
4. Click on result to view details

**Job Detail:**
- Execution start/end time
- Duration
- Status
- Full log output
- Success/error messages
- Objects synced counts
- Cleanup statistics

### Monitoring Jobs

**Dashboard:**
- Quick access button: "Scheduled Jobs"
- Links directly to NetBox Jobs UI
- View all job status at a glance

**Job Status:**
- ⏱️ **Pending**: Queued for execution
- ▶️ **Running**: Currently executing
- ✅ **Completed**: Finished successfully
- ⚠️ **Errored**: Completed with errors
- ❌ **Failed**: Execution failed

**Log Levels:**
- INFO: General progress messages
- WARNING: Non-critical issues (e.g., cleanup operations)
- ERROR: Failures and exceptions

### Comparison: Jobs vs Management Commands

| Feature | NetBox Jobs | Management Commands |
|---------|-------------|---------------------|
| **UI Access** | ✅ Native NetBox UI | ❌ CLI only |
| **Scheduling** | ✅ Built-in scheduler | Manual (cron/systemd) |
| **Status Tracking** | ✅ Full history | Manual logging |
| **Log Viewing** | ✅ In UI | Check log files |
| **Queue Management** | ✅ Yes | No |
| **Retry Logic** | ✅ Yes | Manual |
| **Progress Tracking** | ✅ Real-time | Manual |
| **Best For** | Production, scheduled | One-off, automation |

### Best Practices

#### For Production

1. **Use NetBox Jobs** for all scheduling
   ```
   ✅ Jobs → Scheduled Meraki Dashboard Sync
   ❌ Cron → schedule_meraki_sync
   ```

2. **Configure Scheduling in Plugin Settings**
   - Enable scheduled sync
   - Set appropriate interval
   - Choose sync mode (review recommended)

3. **Set Up Job Schedule**
   - Use interval or cron expression
   - Match plugin settings interval
   - Enable notifications for failures

4. **Monitor Regularly**
   - Check Job Results weekly
   - Review error logs
   - Adjust schedule if needed

#### For Development

1. **Use Manual Job Execution**
   - Jobs → Meraki Dashboard Sync → Run Job
   - Quick testing without scheduling

2. **Use Management Commands**
   - `python manage.py sync_meraki --mode dry_run`
   - Faster for iterative testing

3. **Check Job Logs**
   - Detailed debugging information
   - Stack traces for errors

### Migration from Management Commands

**Old Method (Cron):**
```cron
*/30 * * * * python manage.py schedule_meraki_sync
```

**New Method (NetBox Jobs):**
1. Remove cron entry
2. Disable systemd service (if used)
3. Set up job schedule in NetBox UI
4. Monitor via Jobs UI

**Benefits:**
- ✅ Better visibility
- ✅ No external dependencies
- ✅ Integrated with NetBox
- ✅ Easier troubleshooting
- ✅ Historical tracking

### Troubleshooting

**Job Not Running:**
1. Check if RQ worker is running:
   ```bash
   python manage.py rqworker
   ```
2. Verify schedule is enabled
3. Check NetBox logs for errors

**Job Failing:**
1. View job result details
2. Check error messages in logs
3. Verify Meraki API key
4. Test with dry run mode

**Jobs Not Appearing:**
1. Restart NetBox:
   ```bash
   sudo systemctl restart netbox
   ```
2. Clear cache:
   ```bash
   python manage.py clearcache
   ```
3. Check plugin is enabled

**Schedule Not Triggering:**
1. Verify schedule is enabled
2. Check start time hasn't passed
3. Ensure interval is configured
4. Check RQ worker is processing jobs

### Advanced Configuration

**Custom Queue:**
Create dedicated queue for Meraki syncs:

```python
# configuration.py
RQ_QUEUES = {
    'default': {},
    'meraki-sync': {
        'DEFAULT_TIMEOUT': 3600,  # 1 hour timeout
    }
}
```

Update job queue in plugin if needed.

**Job Timeout:**
For large Meraki deployments, increase timeout:

```python
# In jobs.py
class MerakiSyncJob(Job):
    class Meta:
        name = "Meraki Dashboard Sync"
        timeout = 7200  # 2 hours
```

**Concurrent Execution:**
Prevent overlapping syncs:

```python
# Jobs are single-threaded by default
# Use atomic operations in sync_service.py
```

## Configuration Examples

### Example 1: Standardized Uppercase

**Settings:**
- Device Names: UPPERCASE
- Site Names: UPPERCASE
- VLAN Names: UPPERCASE
- SSID Names: UPPERCASE

**Result:**
```
Devices: SWITCH-FLOOR1, ROUTER-CORE
Sites: NEW YORK OFFICE, LOS ANGELES DC
VLANs: MANAGEMENT, GUEST, IOT
SSIDs: EMPLOYEE-WIFI, GUEST-WIFI
```

### Example 2: Clean Lowercase

**Settings:**
- Device Names: lowercase
- Site Names: lowercase
- VLAN Names: lowercase
- SSID Names: lowercase

**Result:**
```
Devices: switch-floor1, router-core
Sites: new york office, los angeles dc
VLANs: management, guest, iot
SSIDs: employee-wifi, guest-wifi
```

### Example 3: Mixed (Recommended)

**Settings:**
- Device Names: Keep Original (Meraki names are good)
- Site Names: Title Case (Clean for UI)
- VLAN Names: UPPERCASE (Network standard)
- SSID Names: Keep Original (User-facing)

**Result:**
```
Devices: SW-NYC-01, RTR-LA-CORE-01
Sites: New York Office, Los Angeles Dc
VLANs: MANAGEMENT, GUEST, IOT
SSIDs: Employee-WiFi, Guest-WiFi
```

## Summary

### Name Transformations
✅ Four transformation options per object type  
✅ Applied during sync automatically  
✅ Separate controls for devices, sites, VLANs, SSIDs  
✅ Examples shown in UI  
✅ Works with regex site rules  

### NetBox Jobs
✅ Native NetBox job integration  
✅ Built-in scheduling and monitoring  
✅ Status tracking and history  
✅ Detailed logging in UI  
✅ Queue management  
✅ Better than management commands for production  

Choose the tools that fit your workflow - both methods remain available!

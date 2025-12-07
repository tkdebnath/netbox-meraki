# Enhanced Sync Features Guide (Version 0.6.0)

## Overview

Version 0.6.0 introduces powerful new capabilities for monitoring and controlling sync operations, including live progress tracking, sync cancellation, enhanced review mode with detailed previews, and automatic device type creation.

## Live Progress Tracking

### Features

- **Real-time Progress Bar**: Visual progress indicator showing sync completion (0-100%)
- **Current Operation Display**: Shows what's currently being synced (e.g., "Syncing organization: Main Office")
- **Live Log Stream**: Auto-refreshing log entries with timestamps and severity levels
- **Auto-Refresh**: Updates every 3 seconds while sync is running
- **Statistics Display**: Real-time counters for all synced object types including SSIDs

### Using Live Progress

1. **Start a Sync**: Navigate to Dashboard → Click "Run Sync Now"
2. **View Progress**: You'll be redirected to the sync log page
3. **Monitor Live**: 
   - Watch the progress bar advance
   - See current operation updates
   - View new log entries as they appear
   - Track object counts in real-time
4. **Auto-Refresh Control**: 
   - Click "Pause Auto-Refresh" to stop updates
   - Click "Resume Auto-Refresh" to continue

### Progress Log Levels

- **INFO** (Blue): Normal progress messages
  - "Starting Meraki synchronization"
  - "Found 3 organizations"
  - "Processing organization: Main Office"
  - "Auto-created device type: MX84"
  
- **WARN** (Yellow): Non-critical issues or cleanup operations
  - "Sync cancelled by user"
  - "Deleting orphaned device: OLD-DEVICE"
  
- **ERROR** (Red): Failures and exceptions
  - "Error syncing organization Main: Connection timeout"
  - "Failed to create device: Invalid model"

### Progress Stages

The sync progresses through these stages:

1. **Initialization (0-5%)**: Setting up, creating tags
2. **Organization Sync (5-80%)**: Processing each organization and its networks
3. **Cleanup (80-95%)**: Removing orphaned objects (auto mode only)
4. **Finalization (95-100%)**: Updating statistics, completing

### API Access

**Get Progress via API:**
```bash
curl -X GET http://netbox/api/plugins/netbox-meraki/sync-logs/{id}/progress/ \
  -H "Authorization: Token YOUR_TOKEN"
```

**Response:**
```json
{
  "id": 123,
  "status": "running",
  "current_operation": "Syncing device: Switch-1",
  "progress_percent": 45,
  "progress_logs": [
    {
      "timestamp": "2025-12-06T10:15:30",
      "level": "info",
      "message": "Starting sync"
    }
  ],
  "cancel_requested": false,
  "organizations_synced": 2,
  "networks_synced": 15,
  "devices_synced": 87,
  "vlans_synced": 34,
  "prefixes_synced": 56,
  "ssids_synced": 12
}
```

## Sync Cancellation

### Features

- **Cancel Button**: Visible on sync log page while sync is running
- **Graceful Cancellation**: Completes current operation before stopping
- **Prevents Data Corruption**: Ensures database consistency
- **Cancellation Tracking**: Records when and by whom sync was cancelled
- **API Support**: Can cancel via REST API

### How to Cancel

**Via Web UI:**
1. Navigate to ongoing sync log page
2. Click "Cancel Sync" button (yellow)
3. Confirm cancellation in dialog
4. Sync will stop after completing current operation
5. Status will show as "Failed" with message "Sync cancelled by user"

**Via API:**
```bash
curl -X POST http://netbox/api/plugins/netbox-meraki/sync-logs/{id}/cancel/ \
  -H "Authorization: Token YOUR_TOKEN" \
  -H "Content-Type: application/json"
```

**Response:**
```json
{
  "message": "Cancellation requested",
  "cancelled_at": "2025-12-06T10:20:45Z"
}
```

### Cancellation Behavior

When you cancel a sync:

1. **Cancel flag is set**: `cancel_requested = True`
2. **Current operation completes**: Prevents partial data
3. **Sync stops**: No new operations started
4. **Progress log updated**: "Sync cancelled by user" entry added
5. **Status set to failed**: Final status shows cancellation
6. **Timestamp recorded**: `cancelled_at` field populated

### When to Cancel

Cancel a sync when:
- Taking too long and blocking other operations
- Discovered configuration error mid-sync
- Need to update settings before completion
- Testing and want to abort early
- System maintenance required immediately

## Enhanced Review Mode

### Overview

Review mode now shows detailed previews of what will be created or updated, organized by object type in separate sections.

### Categorized Review Sections

#### 1. Sites Section (Blue Header)
Shows all networks being created/updated as NetBox sites:
```
Site Name: Mumbai Office
Network ID: L_1234567890
Time Zone: Asia/Kolkata
Description: Main office network
```

#### 2. Devices Section (Green Header)
Detailed device information with related objects:
```
Name: MX84-Primary
Serial: Q2AB-CDEF-GHIJ
Model: MX84
Manufacturer: Cisco Meraki
Device Role: Security Appliance
Site: Mumbai Office
Status: active
Product Type: appliance
MAC Address: 00:18:0a:xx:xx:xx
LAN IP: 192.168.1.1
Firmware: MX 18.107.2
```

**Related Info Badges:**
- Site: Mumbai Office
- Role: Security Appliance

#### 3. VLANs Section (Yellow Header)
Compact VLAN listings:
```
VLAN Name: Management
VID: 10
Site: Mumbai Office
```

#### 4. Prefixes Section (Cyan Header)
IP prefix details with VLAN associations:
```
Prefix: 192.168.10.0/24
Site: Mumbai Office
VLAN: Management
Status: active
```

#### 5. SSIDs Section (Gray Header)
Wireless SSID information:
```
SSID Name: Employee-WiFi
Network: Mumbai Office
Enabled: True
Auth Mode: WPA2-PSK
```

### Action Badges

Each item shows its action type:
- **CREATE** (Green): New object will be created
- **UPDATE** (Yellow): Existing object will be updated
- **SKIP** (Gray): Object exists and matches

### Approval Workflow

**Individual Approval:**
1. Review each item's details
2. Click "Approve" or "Reject" for each
3. Items show approved/rejected status

**Bulk Actions:**
- **Approve All**: Approve all pending items at once
- **Reject All**: Reject all pending items at once
- **Apply Approved Changes**: Execute all approved items

**Comparison View (Updates):**
For updates, click "Show changes" to see:
```
Field       Current         New
----        -------         ---
status      offline         active
firmware    MX 17.x         MX 18.107.2
site        Old Site        Mumbai Office
```

### Review Best Practices

1. **Check Site Assignments**: Verify devices are going to correct sites
2. **Review Device Roles**: Ensure roles match your conventions
3. **Validate VLANs**: Check VID numbers don't conflict
4. **Examine Prefixes**: Confirm subnet assignments are correct
5. **Verify SSIDs**: Check wireless network names are accurate

## Automatic Device Type Creation

### Features

- **Auto-Creation**: Missing device types created automatically during sync
- **Part Number Population**: Model number used as part number
- **Update Existing**: Fills missing part numbers on existing device types
- **Progress Logging**: Logs when device types are created
- **No Manual Work**: Reduces pre-sync configuration requirements

### How It Works

**When Syncing a Device:**
1. Check if device type exists for model (e.g., "MX84")
2. If not found:
   - Create new DeviceType
   - Set manufacturer to "Cisco Meraki"
   - Set slug from model name
   - **Set part_number to model name**
   - Log: "Auto-created device type: MX84"
3. If found but missing part_number:
   - Update part_number field
   - Log: "Updated device type MX84 with part number"

### Part Number Mapping

| Model | Part Number | Notes |
|-------|-------------|-------|
| MX84 | MX84 | Security Appliance |
| MS220-8P | MS220-8P | Switch |
| MR46 | MR46 | Wireless AP |
| MV72 | MV72 | Camera |

### Benefits

- **Faster Setup**: No need to pre-create device types
- **Consistency**: All device types have part numbers
- **Less Manual Work**: Automatically handles new models
- **Better Inventory**: Part numbers improve asset tracking

### Manual Override

If you want custom part numbers:

1. Navigate to **Device Types**
2. Find the device type (e.g., "MX84")
3. Edit the **Part Number** field
4. Save changes
5. Future syncs won't override manual changes

## SSID Tracking

### Features

- **SSID Counter**: Tracks total SSIDs synchronized
- **AP Association**: SSIDs stored in custom field on wireless APs
- **Name Transformation**: Applies configured transformations to SSID names
- **Review Support**: SSIDs appear in review mode for approval

### SSID Storage

SSIDs are stored in the `meraki_ssids` custom field:
```
Device: MR46-Floor2
Custom Field: meraki_ssids
Value: "Employee-WiFi, Guest-WiFi, IoT-Network"
```

### SSID Statistics

Displayed in sync log:
- Main statistics grid shows SSID count
- Progress updates include SSID totals
- API responses include `ssids_synced` field

## API Endpoints Summary

### Progress Endpoint
**GET** `/api/plugins/netbox-meraki/sync-logs/{id}/progress/`

Returns real-time sync progress including:
- Current operation
- Progress percentage
- Live log entries
- All object counters (including SSIDs)
- Cancellation status

### Cancel Endpoint
**POST** `/api/plugins/netbox-meraki/sync-logs/{id}/cancel/`

Requests cancellation of ongoing sync:
- Returns cancellation timestamp
- Sync stops gracefully
- Error if sync not running

### Trigger Sync Endpoint
**POST** `/api/plugins/netbox-meraki/sync-logs/trigger_sync/`

Starts new synchronization:
- Uses default sync mode from settings
- Returns sync log object
- Includes initial status

## Integration Examples

### Monitoring Script

```python
import requests
import time

NETBOX_URL = "http://netbox"
TOKEN = "your_token"
headers = {"Authorization": f"Token {TOKEN}"}

# Start sync
response = requests.post(f"{NETBOX_URL}/api/plugins/netbox-meraki/sync-logs/trigger_sync/", headers=headers)
sync_id = response.json()['id']

# Monitor progress
while True:
    progress = requests.get(f"{NETBOX_URL}/api/plugins/netbox-meraki/sync-logs/{sync_id}/progress/", headers=headers).json()
    
    print(f"Progress: {progress['progress_percent']}% - {progress['current_operation']}")
    print(f"Devices: {progress['devices_synced']}, VLANs: {progress['vlans_synced']}, SSIDs: {progress['ssids_synced']}")
    
    if progress['status'] != 'running':
        print(f"Sync complete: {progress['status']}")
        break
    
    time.sleep(3)
```

### Cancel on Timeout

```python
import requests
import time
from datetime import datetime, timedelta

# Start sync
sync_id = start_sync()
start_time = datetime.now()
timeout = timedelta(minutes=30)

while True:
    if datetime.now() - start_time > timeout:
        # Cancel if taking too long
        requests.post(f"{NETBOX_URL}/api/plugins/netbox-meraki/sync-logs/{sync_id}/cancel/", headers=headers)
        print("Sync cancelled due to timeout")
        break
    
    progress = get_progress(sync_id)
    if progress['status'] != 'running':
        break
    
    time.sleep(5)
```

## Troubleshooting

### Progress Not Updating

**Symptoms:** Progress bar stuck, logs not appearing

**Solutions:**
1. Check browser console for JavaScript errors
2. Verify API endpoint is accessible: `/api/plugins/netbox-meraki/sync-logs/{id}/progress/`
3. Ensure NetBox version is 4.4.x or higher
4. Clear browser cache
5. Try different browser

### Cancel Not Working

**Symptoms:** Cancel button doesn't stop sync

**Solutions:**
1. Sync must complete current operation first (can take 30-60 seconds)
2. Check sync status is actually "running"
3. Verify API endpoint returns 200 status
4. Check NetBox logs for errors
5. Ensure user has proper permissions

### Device Types Not Auto-Creating

**Symptoms:** Getting errors about missing device types

**Solutions:**
1. Check sync logs for "Auto-created device type" messages
2. Verify manufacturer "Cisco Meraki" exists in NetBox
3. Check model name from Meraki is valid
4. Look for errors in NetBox logs
5. Manually create one device type to test

### Review Items Missing Previews

**Symptoms:** Preview display is blank or incomplete

**Solutions:**
1. Run migration: `python manage.py migrate netbox_meraki`
2. Check that `preview_display` field exists in database
3. Re-run sync in review mode
4. Check sync_service.py `_create_review_item` method
5. Verify proposed_data contains all required fields

### SSIDs Not Appearing

**Symptoms:** SSID count is 0 or custom field is empty

**Solutions:**
1. Ensure devices are wireless APs (product type starts with "MR")
2. Check SSIDs are enabled in Meraki Dashboard
3. Verify network ID is correct for device
4. Check custom field `meraki_ssids` exists
5. Review sync logs for SSID-related errors

## Performance Considerations

### Large Deployments

For organizations with 100+ devices:
- Progress updates may slow down (increase refresh interval)
- Consider using scheduled sync mode
- Cancel and resume if needed
- Monitor database size (logs grow over time)

### Progress Log Size

Each sync generates log entries:
- Average: 50-200 entries per sync
- Large syncs: 500+ entries
- Stored as JSON in database
- Consider periodic cleanup of old logs

### Auto-Refresh Impact

Auto-refresh makes API calls every 3 seconds:
- Minimal database impact
- No performance issues for single user
- Multiple simultaneous viewers may increase load
- Can pause refresh if needed

## Best Practices

1. **Use Review Mode for First Sync**: See what will be created
2. **Monitor Progress**: Watch for errors during sync
3. **Cancel if Needed**: Don't let problematic syncs run
4. **Check Device Types**: Verify auto-created types are correct
5. **Review SSIDs**: Ensure wireless configurations are accurate
6. **Clean Old Logs**: Periodically delete old sync logs
7. **Test Cancel**: Verify cancellation works before production use
8. **Use API for Automation**: Integrate with monitoring systems

## Summary

Version 0.6.0 provides comprehensive sync monitoring and control:

✅ **Live Progress** - See exactly what's happening  
✅ **Cancel Capability** - Stop syncs safely  
✅ **Enhanced Review** - Detailed previews and organized sections  
✅ **Auto Device Types** - No manual pre-configuration  
✅ **SSID Tracking** - Complete wireless inventory  
✅ **Better APIs** - Programmatic control and monitoring  

These features make the plugin production-ready for large Meraki deployments!

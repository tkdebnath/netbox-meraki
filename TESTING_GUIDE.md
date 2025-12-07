# Testing Guide for Version 0.6.0

## Pre-Testing Setup

### 1. Run Migration
```bash
cd /home/tdebnath/ra_netbox_meraki
python manage.py migrate netbox_meraki
```

Expected output:
```
Running migrations:
  Applying netbox_meraki.0007_enhanced_sync_features... OK
```

### 2. Restart NetBox
```bash
sudo systemctl restart netbox
sudo systemctl restart netbox-rq
```

### 3. Verify Migration
```bash
python manage.py showmigrations netbox_meraki
```

Should show:
```
netbox_meraki
 [X] 0001_initial
 [X] 0002_...
 [X] 0006_add_name_transforms
 [X] 0007_enhanced_sync_features
```

## Feature Testing

### Test 1: Live Progress Tracking

**Steps:**
1. Navigate to NetBox → Plugins → Meraki → Dashboard
2. Click "Run Sync Now"
3. Observe sync log page

**Expected Results:**
- ✅ Progress bar appears (0-100%)
- ✅ "Current Operation" shows sync status
- ✅ Progress logs section appears
- ✅ Logs auto-update every 3 seconds
- ✅ New log entries appear at bottom
- ✅ Auto-scroll to latest entry
- ✅ Timestamp format: [2025-12-06 10:15:30]
- ✅ Level badges: INFO (blue), WARN (yellow), ERROR (red)
- ✅ Statistics update in real-time

**Sample Log Entries:**
```
[2025-12-06 10:15:30] INFO Starting Meraki synchronization
[2025-12-06 10:15:31] INFO Fetching organizations from Meraki Dashboard
[2025-12-06 10:15:32] INFO Found 2 organizations
[2025-12-06 10:15:33] INFO Processing organization: Main Office
[2025-12-06 10:15:45] INFO Auto-created device type: MX84
```

**Test Variations:**
- Large sync (100+ devices)
- Small sync (few devices)
- Sync with errors
- Multiple browser tabs

### Test 2: Auto-Refresh Controls

**Steps:**
1. During running sync, click "Pause Auto-Refresh"
2. Observe logs stop updating
3. Click "Resume Auto-Refresh"
4. Observe logs resume updating

**Expected Results:**
- ✅ Button text changes: "Pause" ↔ "Resume"
- ✅ Updates stop when paused
- ✅ Updates resume when resumed
- ✅ No errors in browser console

### Test 3: Sync Cancellation

**Steps:**
1. Start a sync operation
2. Click "Cancel Sync" button (yellow)
3. Confirm dialog
4. Wait for completion

**Expected Results:**
- ✅ Cancel button appears only for running syncs
- ✅ Confirmation dialog shows
- ✅ Progress log shows: "Sync cancelled by user"
- ✅ Sync stops after current operation
- ✅ Status becomes "failed"
- ✅ Message: "Sync cancelled by user"
- ✅ Cancelled_at timestamp shown
- ✅ Cancel button becomes disabled

**Edge Cases:**
- Cancel immediately after start
- Cancel near completion
- Cancel during cleanup phase

### Test 4: SSID Tracking

**Prerequisites:** 
- At least one wireless AP (MR device) in Meraki
- SSIDs enabled on the network

**Steps:**
1. Run sync (auto or review mode)
2. Check sync log statistics
3. Navigate to a wireless AP device
4. View custom fields

**Expected Results:**
- ✅ SSID counter shows in statistics
- ✅ Counter > 0 if APs exist
- ✅ Custom field `meraki_ssids` populated
- ✅ Value format: "SSID1, SSID2, SSID3"
- ✅ Only enabled SSIDs included
- ✅ Name transformations applied

**Sample Custom Field:**
```
meraki_ssids: "Employee-WiFi, Guest-WiFi, IoT-Network"
```

### Test 5: Automatic Device Type Creation

**Steps:**
1. Delete a device type from NetBox (e.g., "MX84")
2. Run sync
3. Check progress logs
4. Check device type in NetBox

**Expected Results:**
- ✅ Progress log: "Auto-created device type: MX84"
- ✅ Device type exists in NetBox
- ✅ Manufacturer: Cisco Meraki
- ✅ Part number field filled with model
- ✅ Slug auto-generated
- ✅ Device created successfully

**Test Variations:**
- New model not in NetBox
- Existing type with missing part number
- Multiple new types in one sync

**Verify Part Numbers:**
```sql
SELECT model, part_number FROM dcim_devicetype 
WHERE manufacturer_id = (SELECT id FROM dcim_manufacturer WHERE name = 'Cisco Meraki');
```

Expected:
```
 model    | part_number
----------+-------------
 MX84     | MX84
 MS220-8P | MS220-8P
 MR46     | MR46
```

### Test 6: Enhanced Review Mode

**Steps:**
1. Configure sync mode: "Sync with Review"
2. Run sync
3. Navigate to review detail page

**Expected Results:**

**Section Organization:**
- ✅ Sites section (blue header) with site items
- ✅ Devices section (green header) with device items
- ✅ VLANs section (yellow header) with VLAN items
- ✅ Prefixes section (cyan header) with prefix items
- ✅ SSIDs section (gray header) with SSID items
- ✅ Empty sections don't display

**Preview Displays:**

Sites:
```
**Name:** Mumbai Office
**Network ID:** L_1234567890
**Time Zone:** Asia/Kolkata
**Description:** Main office network
```

Devices:
```
**Name:** MX84-Primary
**Serial:** Q2AB-CDEF-GHIJ
**Model:** MX84
**Manufacturer:** Cisco Meraki
**Device Role:** Security Appliance
**Site:** Mumbai Office
**Status:** active
**Product Type:** appliance
**MAC Address:** 00:18:0a:xx:xx:xx
**LAN IP:** 192.168.1.1
**Firmware:** MX 18.107.2
```

**Related Object Badges:**
- ✅ Site badges on devices
- ✅ Role badges on devices
- ✅ Site badges on VLANs/prefixes
- ✅ VLAN badges on prefixes
- ✅ Network badges on SSIDs

**Action Badges:**
- ✅ CREATE (green) for new objects
- ✅ UPDATE (yellow) for modifications
- ✅ SKIP (gray) for existing

**Approval Workflow:**
1. Click "Approve" on individual item
2. Status badge changes to "APPROVED" (green)
3. Click "Reject" on another item
4. Status badge changes to "REJECTED" (red)
5. Click "Approve All"
6. All items become approved
7. Click "Apply Approved Changes"
8. Redirect to sync log
9. Success message appears

**Change Comparison (Updates):**
- ✅ "Show changes" link appears
- ✅ Expandable section opens
- ✅ Table with Field/Current/New columns
- ✅ Only changed fields shown
- ✅ Color coding (current vs. new)

### Test 7: API Endpoints

**Progress Endpoint:**
```bash
# Get sync ID from recent sync
SYNC_ID=123

# Test progress endpoint
curl -X GET \
  "http://localhost:8000/api/plugins/netbox-meraki/sync-logs/${SYNC_ID}/progress/" \
  -H "Authorization: Token YOUR_TOKEN"
```

**Expected Response:**
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

**Cancel Endpoint:**
```bash
curl -X POST \
  "http://localhost:8000/api/plugins/netbox-meraki/sync-logs/${SYNC_ID}/cancel/" \
  -H "Authorization: Token YOUR_TOKEN" \
  -H "Content-Type: application/json"
```

**Expected Response:**
```json
{
  "message": "Cancellation requested",
  "cancelled_at": "2025-12-06T10:20:45Z"
}
```

**Error Cases:**
- Non-existent sync ID → 404 Not Found
- Already completed sync → 400 Bad Request
- No auth token → 401 Unauthorized

### Test 8: Database Integrity

**Check New Fields:**
```sql
-- SyncLog fields
SELECT 
  ssids_synced,
  progress_percent,
  cancel_requested,
  LENGTH(progress_logs::text) as log_size,
  current_operation
FROM netbox_meraki_synclog
ORDER BY timestamp DESC
LIMIT 5;

-- ReviewItem fields  
SELECT 
  item_type,
  LENGTH(preview_display) as preview_size,
  related_object_info
FROM netbox_meraki_reviewitem
LIMIT 10;
```

**Expected:**
- ✅ All fields exist
- ✅ No NULL constraint violations
- ✅ JSON fields properly formatted
- ✅ Timestamps in correct format

### Test 9: Browser Compatibility

Test in multiple browsers:
- ✅ Chrome/Chromium
- ✅ Firefox
- ✅ Safari (if available)
- ✅ Edge

**Check:**
- Progress bar rendering
- JavaScript auto-refresh
- Cancel button functionality
- Modal dialogs
- Log auto-scroll

### Test 10: Performance

**Large Sync Test:**
- Organizations: 3+
- Networks: 50+
- Devices: 200+
- VLANs: 100+

**Measure:**
- Total sync time
- Progress update latency
- Page responsiveness
- Memory usage
- Database load

**Acceptable Performance:**
- Progress updates < 200ms
- UI remains responsive
- No browser lag
- Memory stable (no leaks)

## Regression Testing

Ensure existing features still work:

### Basic Sync
- ✅ Auto mode works
- ✅ Review mode works
- ✅ Dry run mode works

### Data Sync
- ✅ Sites created correctly
- ✅ Devices created with all fields
- ✅ VLANs synced properly
- ✅ Prefixes with correct sites
- ✅ Interfaces created
- ✅ Switch ports configured

### Cleanup
- ✅ Orphaned sites deleted
- ✅ Orphaned devices deleted
- ✅ Orphaned VLANs deleted
- ✅ Orphaned prefixes deleted
- ✅ Statistics accurate

### Name Transformations
- ✅ Device names transformed
- ✅ Site names transformed
- ✅ VLAN names transformed
- ✅ SSID names transformed

### Scheduling
- ✅ Scheduled sync runs
- ✅ Next sync time updates
- ✅ Scheduling UI works

## Error Handling

Test error scenarios:

### Network Errors
- ✅ Meraki API unreachable
- ✅ Timeout during sync
- ✅ Invalid API key
- ✅ Rate limiting

### Data Errors
- ✅ Invalid device model
- ✅ Duplicate serial numbers
- ✅ Missing required fields
- ✅ Invalid VLAN IDs

### System Errors
- ✅ Database connection lost
- ✅ Insufficient permissions
- ✅ Disk full
- ✅ Memory exhausted

**Expected Behavior:**
- Errors logged to progress logs
- Sync continues if possible
- Graceful degradation
- Clear error messages
- No data corruption

## Sign-Off Checklist

Before marking version 0.6.0 as complete:

- [ ] All migrations applied successfully
- [ ] Live progress tracking working
- [ ] Auto-refresh functional
- [ ] Cancel capability working
- [ ] SSID tracking accurate
- [ ] Auto device type creation verified
- [ ] Enhanced review mode displays correctly
- [ ] API endpoints responding correctly
- [ ] No errors in NetBox logs
- [ ] Database schema correct
- [ ] Performance acceptable
- [ ] Documentation complete
- [ ] All regression tests pass

## Rollback Plan

If issues found:

1. **Stop NetBox:**
   ```bash
   sudo systemctl stop netbox netbox-rq
   ```

2. **Rollback migration:**
   ```bash
   python manage.py migrate netbox_meraki 0006_add_name_transforms
   ```

3. **Revert code:**
   ```bash
   git checkout v0.5.0
   ```

4. **Restart:**
   ```bash
   sudo systemctl start netbox netbox-rq
   ```

## Success Criteria

Version 0.6.0 is ready for production when:

✅ All features tested and working  
✅ No critical bugs found  
✅ Performance acceptable  
✅ Documentation complete  
✅ Migration safe and reversible  
✅ API endpoints stable  
✅ UI responsive and functional  

## Post-Deployment

After deploying to production:

1. Monitor first few syncs closely
2. Check progress logs for errors
3. Verify SSID tracking
4. Test cancel if needed
5. Collect user feedback
6. Document any issues

## Support

For testing issues:
- Check NetBox logs: `/var/log/netbox/`
- Enable DEBUG mode for details
- Use browser developer console
- Test with dry run first
- Verify database state with SQL queries

---

**Remember**: Test in a non-production environment first!

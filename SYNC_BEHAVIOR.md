# NetBox Meraki Plugin - Sync Behavior Guide

## Overview

The NetBox Meraki plugin performs intelligent synchronization with automatic cleanup and update capabilities. This guide explains how the plugin handles data consistency between Meraki Dashboard and NetBox.

## Sync Modes

### 1. Auto Sync Mode
- **Full synchronization** with automatic database modifications
- Creates, updates, and deletes objects automatically
- Detects and removes orphaned objects
- Updates objects when data changes in Meraki

### 2. Review Mode
- Generates proposed changes for manual approval
- No automatic modifications
- Review changes before applying
- Ideal for production environments

### 3. Dry Run Mode
- Shows what would be synchronized without making changes
- No database modifications
- Perfect for testing and validation

## Data Consistency Rules

### Device Management

#### Serial Number Uniqueness
- **Rule**: Only ONE device per serial number
- **Behavior**: 
  - If duplicate devices exist with same serial, keeps the first one and deletes duplicates
  - Always uses serial number as the unique identifier
  - Updates existing device when serial matches

**Example**:
```python
# Before sync: Two devices with serial "Q2XX-XXXX-XXXX"
Device 1: Name="Switch-Floor1", Serial="Q2XX-XXXX-XXXX"
Device 2: Name="Switch-Old", Serial="Q2XX-XXXX-XXXX"  # Duplicate

# After sync: Only one device remains
Device 1: Name="Switch-Floor1", Serial="Q2XX-XXXX-XXXX"  # Updated from Meraki
# Device 2 deleted automatically
```

#### Device Updates
- Updates all device properties when serial matches:
  - Name
  - Device type
  - Device role
  - Site assignment
  - Status (active/offline)
  - Comments and custom fields

### Prefix Management

#### Site Reassignment
- **Rule**: Prefix site must match current Meraki network
- **Behavior**:
  - Detects when prefix exists but site has changed
  - Automatically reassigns prefix to new site
  - Logs site changes for tracking

**Example**:
```python
# Before sync:
Prefix: 10.0.1.0/24, Site="Office-NY"

# Meraki now shows this prefix in "Office-LA" network
# After sync:
Prefix: 10.0.1.0/24, Site="Office-LA"  # Site updated
# Stats show: updated_prefixes = 1
```

#### Prefix Updates
Prefix properties updated on each sync:
- Site assignment (if changed)
- VLAN association
- Description
- Status

### Orphaned Object Cleanup

#### What are Orphaned Objects?
Objects that exist in NetBox with the `meraki` tag but no longer exist in Meraki Dashboard.

#### Automatic Cleanup (Auto Sync Mode Only)
The plugin automatically deletes orphaned:
- **Sites** - Networks removed from Meraki
- **Devices** - Devices removed from Meraki inventory
- **VLANs** - VLANs removed from network configuration
- **Prefixes** - Subnets no longer in Meraki

**Important**: Cleanup only runs in `auto` mode, not in `review` or `dry_run` modes.

#### Cleanup Process
1. During sync, tracks all object IDs synced from Meraki
2. After sync completes, queries all NetBox objects with `meraki` tag
3. Compares synced IDs with existing objects
4. Deletes objects not in synced set

**Example**:
```python
# Meraki has: Device A, Device B, Device C
# NetBox has: Device A, Device B, Device C, Device D (orphaned)

# After sync:
# - Device A, B, C updated
# - Device D deleted (no longer in Meraki)
# Stats show: deleted_devices = 1
```

### VLAN Management

#### VLAN Updates
- Updates VLAN name and description
- Maintains VLAN group association with site
- Updates subnet information

#### VLAN Cleanup
- Removes VLANs deleted from Meraki networks
- Cleans up entire VLAN groups if network removed

### Interface Management

#### Interface Updates
All interface properties updated:
- Type (based on speed and product)
- Mode (access/tagged)
- VLAN assignments (untagged and tagged)
- MAC address
- Description
- Enabled/disabled status

#### IP Address Management
- Creates IP addresses for interfaces
- Updates DNS names
- Maintains interface-to-IP assignments
- Updates descriptions

## Statistics Tracking

### Sync Statistics
Each sync operation tracks:
- `organizations_synced` - Meraki organizations processed
- `networks_synced` - Networks synchronized
- `devices_synced` - Devices created/updated
- `vlans_synced` - VLANs created/updated
- `prefixes_synced` - Prefixes created/updated

### Cleanup Statistics (New)
- `deleted_sites` - Orphaned sites removed
- `deleted_devices` - Orphaned devices removed
- `deleted_vlans` - Orphaned VLANs removed
- `deleted_prefixes` - Orphaned prefixes removed
- `updated_prefixes` - Prefixes with site changes

## Viewing Sync Results

### Dashboard View
Shows latest sync with cleanup summary:
```
Devices: 45
VLANs: 23
Prefixes: 18

Cleaned: 2 devices, 5 VLANs, 3 prefixes
```

### Detailed Sync Log
View full statistics including:
- All synced object counts
- Cleanup operations performed
- Updated object counts
- Error messages if any

## Best Practices

### For Production Environments

1. **Use Review Mode Initially**
   ```bash
   python manage.py sync_meraki --mode review
   ```
   Review all proposed changes before applying.

2. **Run Dry Run Before Major Changes**
   ```bash
   python manage.py sync_meraki --mode dry_run
   ```
   Verify sync behavior without modifications.

3. **Monitor Cleanup Operations**
   - Check deleted object counts
   - Review logs for unexpected deletions
   - Backup NetBox before enabling auto cleanup

### For Development/Testing

1. **Use Auto Mode for Speed**
   ```bash
   python manage.py sync_meraki --mode auto
   ```
   Fast iteration with automatic cleanup.

2. **Check Duplicate Devices**
   Before first sync, query for duplicate serials:
   ```python
   from dcim.models import Device
   from django.db.models import Count
   
   duplicates = Device.objects.values('serial')\
       .annotate(count=Count('id'))\
       .filter(count__gt=1)
   ```

## Migration Required

After updating to this version, run migration:
```bash
python manage.py migrate netbox_meraki
```

This adds the cleanup statistics fields to the `SyncLog` model.

## Logging

All operations logged to `netbox_meraki` logger:

### Key Log Messages

**Device Cleanup**:
```
Deleting orphaned device: Switch-Old (Serial: Q2XX-XXXX-XXXX, ID: 123)
Deleted 2 orphaned device(s)
```

**Duplicate Detection**:
```
Deleting duplicate device with serial Q2XX-XXXX-XXXX: Switch-Duplicate (ID: 456)
```

**Prefix Site Change**:
```
Prefix 10.0.1.0/24 site changed: Office-NY -> Office-LA
Updated prefix site: 10.0.1.0/24 -> Office-LA
```

**Orphan Cleanup Summary**:
```
Checking for orphaned objects to clean up...
Deleted 2 orphaned device(s)
Deleted 5 orphaned VLAN(s)
Deleted 3 orphaned prefix(es)
Orphaned object cleanup complete
```

## FAQ

### Q: What happens to devices removed from Meraki?
**A**: In auto mode, they're automatically deleted from NetBox if tagged with `meraki`. In review mode, deletion is proposed for approval.

### Q: Can I prevent automatic deletion?
**A**: Yes, remove the `meraki` tag from objects you want to preserve, or use review mode for manual control.

### Q: What if a prefix moves between sites in Meraki?
**A**: The plugin detects the change and updates the site assignment automatically, incrementing `updated_prefixes` counter.

### Q: How are duplicate serial numbers handled?
**A**: The plugin keeps the first device found and deletes all duplicates, then updates the remaining device with latest Meraki data.

### Q: Does cleanup run in dry run mode?
**A**: No, cleanup only runs in auto mode to prevent accidental deletions during testing.

### Q: Can I see what will be deleted before it happens?
**A**: Yes, run in dry run or review mode first. Review mode will show all proposed changes including deletions.

## Troubleshooting

### Objects Not Cleaning Up
**Check**: 
- Sync mode is `auto` (cleanup disabled in other modes)
- Objects have the `meraki` tag
- Sync completed successfully

### Unexpected Deletions
**Check**:
- Meraki API connectivity
- Organization/network access permissions
- Sync log errors for failed API calls

### Prefix Site Not Updating
**Check**:
- Prefix exists in NetBox
- Site name transformation rules
- Network assignment in Meraki Dashboard

## Summary

The NetBox Meraki plugin ensures data consistency by:
✅ Enforcing device serial uniqueness
✅ Updating prefix sites when they change
✅ Automatically cleaning up orphaned objects
✅ Tracking all changes with detailed statistics
✅ Providing full control through sync modes

All operations are logged and tracked for full audit trail.

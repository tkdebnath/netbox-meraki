# Update Summary - Smart Sync with Cleanup & Update Logic

## Overview
Enhanced the NetBox Meraki plugin with comprehensive data consistency management including automatic cleanup of orphaned objects, prefix site updates, and device serial uniqueness enforcement.

## Changes Implemented

### 1. Orphaned Object Detection & Cleanup

**Location**: `netbox_meraki/sync_service.py`

#### Added Tracking System
```python
self.synced_object_ids = {
    'sites': set(),
    'devices': set(),
    'vlans': set(),
    'prefixes': set(),
}
```

During sync, all object IDs synced from Meraki are tracked in these sets.

#### New Method: `_cleanup_orphaned_objects()`
- Runs after all syncing is complete (only in auto mode)
- Compares synced IDs with all NetBox objects tagged with 'meraki'
- Deletes objects not in the synced set
- Logs each deletion with object details
- Updates statistics counters

**Behavior**:
- Sites removed from Meraki → Deleted from NetBox
- Devices removed from Meraki inventory → Deleted from NetBox
- VLANs removed from network → Deleted from NetBox
- Prefixes no longer in Meraki → Deleted from NetBox

**Safety**: Only runs in `auto` mode. Review and dry_run modes preserve all objects.

### 2. Device Serial Number Uniqueness

**Location**: `netbox_meraki/sync_service.py` - `_sync_device()` method

#### Duplicate Detection
```python
existing_devices = Device.objects.filter(serial=serial)
if existing_devices.count() > 1:
    # Keep first, delete others
    primary_device = existing_devices.first()
    for duplicate in existing_devices[1:]:
        logger.warning(f"Deleting duplicate device...")
        duplicate.delete()
```

**Behavior**:
- Checks for multiple devices with same serial number
- Keeps the first device found
- Deletes all duplicates
- Updates the primary device with latest Meraki data
- Logs all duplicate deletions

**Result**: Prevents data inconsistency from duplicate serial numbers.

### 3. Prefix Site Update Detection

**Location**: `netbox_meraki/sync_service.py` - `_sync_prefixes()` method

#### Site Change Detection
```python
existing_prefix = Prefix.objects.filter(prefix=str(network)).first()
site_changed = False

if existing_prefix and existing_prefix.site and existing_prefix.site.id != site.id:
    logger.info(f"Prefix {network} site changed: {existing_prefix.site.name} -> {site.name}")
    site_changed = True
    self.stats['updated_prefixes'] += 1
```

**Behavior**:
- Detects when prefix exists but belongs to different site
- Automatically reassigns prefix to correct site
- Logs site changes
- Increments `updated_prefixes` counter

**Use Case**: When networks are reorganized in Meraki, prefixes follow their networks.

### 4. Enhanced Statistics Tracking

**Location**: `netbox_meraki/models.py` - `SyncLog` model

#### New Fields Added
```python
deleted_sites = models.IntegerField(default=0)
deleted_devices = models.IntegerField(default=0)
deleted_vlans = models.IntegerField(default=0)
deleted_prefixes = models.IntegerField(default=0)
updated_prefixes = models.IntegerField(default=0)
```

**Purpose**: Track all cleanup and update operations for auditing.

### 5. Migration for New Fields

**File**: `netbox_meraki/migrations/0004_add_cleanup_stats.py`

Adds new statistics fields to SyncLog model.

**Required Action**:
```bash
python manage.py migrate netbox_meraki
```

### 6. Updated UI Templates

#### Dashboard Template
**File**: `netbox_meraki/templates/netbox_meraki/dashboard.html`

Shows cleanup summary in latest sync card:
```html
Cleaned: 2 devices, 5 VLANs, 3 prefixes
```

#### Sync Log Detail Template  
**File**: `netbox_meraki/templates/netbox_meraki/synclog.html`

Added "Cleanup & Updates" section showing:
- Sites Deleted
- Devices Deleted
- VLANs Deleted
- Prefixes Deleted
- Prefix Sites Changed

### 7. Comprehensive Documentation

#### New File: `SYNC_BEHAVIOR.md`
Complete guide covering:
- Sync mode behaviors
- Data consistency rules
- Orphaned object cleanup process
- Device serial uniqueness
- Prefix site reassignment
- Statistics tracking
- Best practices
- Troubleshooting
- FAQ section

#### Updated: `README.md`
- Enhanced feature list
- Added link to SYNC_BEHAVIOR.md
- Updated changelog with version 0.3.0
- Migration instructions

### 8. Version Bump

**File**: `netbox_meraki/__init__.py`
- Version: `0.2.0` → `0.3.0`
- Updated description to mention smart cleanup

## Testing Recommendations

### 1. Test Orphaned Object Cleanup
```bash
# Create test environment
1. Sync from Meraki (objects created)
2. Remove device from Meraki Dashboard
3. Run sync again
4. Verify device deleted from NetBox
5. Check stats show deleted_devices = 1
```

### 2. Test Duplicate Serial Handling
```bash
# Create duplicates manually
1. Create two devices with same serial in NetBox
2. Run sync
3. Verify only one device remains
4. Check logs for duplicate deletion message
```

### 3. Test Prefix Site Updates
```bash
# Move prefix between networks
1. Sync network A with prefix 10.0.1.0/24
2. Move prefix to network B in Meraki
3. Run sync
4. Verify prefix now assigned to site B
5. Check stats show updated_prefixes = 1
```

### 4. Test Modes
```bash
# Verify cleanup only in auto mode
python manage.py sync_meraki --mode dry_run    # No cleanup
python manage.py sync_meraki --mode review     # No cleanup
python manage.py sync_meraki --mode auto       # Cleanup runs
```

## Key Behaviors

### Auto Mode
✅ Creates new objects
✅ Updates existing objects
✅ Deletes orphaned objects
✅ Enforces serial uniqueness
✅ Updates prefix sites

### Review Mode
✅ Creates review items
✅ No automatic modifications
❌ No cleanup (review items would show deletions)
✅ Enforces serial uniqueness in proposals

### Dry Run Mode
✅ Shows what would sync
❌ No database changes
❌ No cleanup
✅ Statistics show proposed changes

## Statistics Meaning

| Stat | Meaning |
|------|---------|
| `devices_synced` | Devices created or updated from Meraki |
| `deleted_devices` | Orphaned devices removed (not in Meraki) |
| `updated_prefixes` | Prefixes whose site was changed |
| `deleted_prefixes` | Orphaned prefixes removed |
| `deleted_vlans` | Orphaned VLANs removed |
| `deleted_sites` | Orphaned sites/networks removed |

## Log Messages to Watch

**Orphan Cleanup**:
```
Checking for orphaned objects to clean up...
Deleting orphaned device: Switch-Old (Serial: Q2XX-XXXX-XXXX, ID: 123)
Deleted 2 orphaned device(s)
```

**Duplicate Detection**:
```
Deleting duplicate device with serial Q2XX-XXXX-XXXX: Switch-Duplicate (ID: 456)
```

**Site Changes**:
```
Prefix 10.0.1.0/24 site changed: Office-NY -> Office-LA
Updated prefix site: 10.0.1.0/24 -> Office-LA
```

## Safety Features

1. **Mode-based Control**: Cleanup only in auto mode
2. **Detailed Logging**: Every deletion logged with full details
3. **Statistics Tracking**: All operations counted for auditing
4. **Tag-based Selection**: Only objects with 'meraki' tag affected
5. **Preserve Manual Objects**: Objects without tag untouched

## Files Modified

1. `netbox_meraki/sync_service.py` - Core sync logic
2. `netbox_meraki/models.py` - Added cleanup stats fields
3. `netbox_meraki/migrations/0004_add_cleanup_stats.py` - New migration
4. `netbox_meraki/templates/netbox_meraki/dashboard.html` - UI updates
5. `netbox_meraki/templates/netbox_meraki/synclog.html` - UI updates
6. `netbox_meraki/__init__.py` - Version bump to 0.3.0
7. `README.md` - Documentation updates
8. `SYNC_BEHAVIOR.md` - New comprehensive guide

## Migration Path

For existing installations:

```bash
# 1. Pull latest code
git pull

# 2. Run migration
python manage.py migrate netbox_meraki

# 3. Test with dry run first
python manage.py sync_meraki --mode dry_run

# 4. Review results, then run auto
python manage.py sync_meraki --mode auto

# 5. Check sync log for cleanup stats
# Visit: /plugins/meraki/logs/
```

## Summary

The plugin now provides:
- **Full data consistency** between Meraki and NetBox
- **Automatic cleanup** of orphaned objects
- **Smart updates** for changed data (prefix sites)
- **Duplicate prevention** for device serials
- **Complete audit trail** with detailed statistics
- **Safe operation** through mode-based controls

All implemented with proper error handling, logging, and user feedback through the UI.

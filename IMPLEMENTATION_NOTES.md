# Review Item Edit Feature - Implementation Summary

## Overview
Added capability to edit review items (sites, devices, VLANs, prefixes, SSIDs) before applying them to NetBox.

## Changes Made

### 1. Database Model (models.py)
- **Added field**: `editable_data` (JSONField) to `ReviewItem` model
  - Stores user-edited data that overrides `proposed_data`
  - Optional field (null=True, blank=True)
  
- **Added method**: `get_final_data()` to `ReviewItem` model
  - Returns `editable_data` if it exists, otherwise returns `proposed_data`
  - Used by apply logic to get the final data to apply

### 2. Migration (0008_add_editable_data.py)
- Created new migration to add the `editable_data` field
- Run with: `python manage.py migrate netbox_meraki`

### 3. Views (views.py)
- **Added class**: `ReviewItemEditView` (lines 283-391)
  - GET: Shows edit form pre-filled with current/proposed data
  - POST: Saves edited data to `editable_data` field
  - Handles different item types:
    - **Site**: name, slug, description
    - **Device**: name, serial (readonly), model, manufacturer, role, site, status
    - **VLAN**: name, vid, description
    - **Generic**: JSON editor for other types

### 4. Templates

#### review_item_edit.html (NEW)
- Complete edit form with 193 lines
- Conditional rendering based on item_type
- Shows original Meraki data below the form
- Breadcrumb navigation
- Save/Cancel buttons

#### review_detail_new.html (UPDATED)
- Added Edit button to all sections:
  - Sites
  - Devices
  - VLANs
  - Prefixes
  - SSIDs
- Added "Edited" badge that shows when item has been edited
- Edit button only visible when status is 'pending'

### 5. URL Routing (urls.py)
- Added route: `review/<int:pk>/item/<int:item_pk>/edit/`
- View: `ReviewItemEditView`
- Name: `review_item_edit`

### 6. Apply Logic (sync_service.py)
- **Updated**: `apply_review_item()` method
  - Changed from using `proposed_data` directly to using `item.get_final_data()`
  - Now respects user edits when applying changes
  
- **Updated**: Site description generation
  - Changed from: `f"Meraki Network - {org_name}"`
  - Changed to: `network_name`
  - Now shows just the network name, not organization

## Usage Flow

1. User creates a sync and reviews items
2. User clicks "Edit" button on any pending review item
3. Edit form loads with current/proposed values
4. User modifies fields as needed
5. User clicks "Save" - data is saved to `editable_data` field
6. Review page shows "Edited" badge on modified items
7. User approves the item
8. When sync is applied, `get_final_data()` returns the edited values
9. NetBox is updated with the edited values

## Key Features

- **Non-destructive**: Original `proposed_data` is preserved
- **Visual feedback**: "Edited" badge shows which items were modified
- **Type-specific forms**: Different fields for sites, devices, VLANs
- **Validation**: Form validation before saving
- **Original data display**: Shows Meraki source data for reference

## Testing Checklist

- [ ] Run migration: `python manage.py migrate netbox_meraki`
- [ ] Create a new sync
- [ ] Navigate to review page
- [ ] Click Edit on a site item
- [ ] Modify site name/description
- [ ] Save and verify "Edited" badge appears
- [ ] Approve the item
- [ ] Apply the review
- [ ] Verify NetBox shows the edited values
- [ ] Test with device, VLAN items

## Migration Command

```bash
cd /home/tdebnath/ra_netbox_meraki
python manage.py migrate netbox_meraki
```

## Files Modified

1. `netbox_meraki/models.py` - Added field and helper method
2. `netbox_meraki/views.py` - Added ReviewItemEditView
3. `netbox_meraki/urls.py` - Added edit route
4. `netbox_meraki/sync_service.py` - Updated apply logic and site description
5. `netbox_meraki/templates/netbox_meraki/review_detail_new.html` - Added Edit buttons
6. `netbox_meraki/templates/netbox_meraki/review_item_edit.html` - NEW template
7. `netbox_meraki/migrations/0008_add_editable_data.py` - NEW migration

## Version
This feature should be part of version 0.6.1 or 0.7.0 depending on versioning strategy.

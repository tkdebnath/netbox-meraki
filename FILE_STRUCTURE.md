# NetBox Meraki Plugin - File Structure Summary

This document provides an overview of all files in the NetBox Meraki plugin.

## Core Plugin Files

### Configuration
- `netbox_meraki/__init__.py` - Plugin configuration (PluginConfig)
- `pyproject.toml` - Python package configuration

### Models
- `netbox_meraki/models.py` - Database models:
  - SyncLog: Tracks sync history with sync_mode support
  - PluginSettings: Device role mappings and default sync mode
  - SiteNameRule: Regex-based site name transformation
  - SyncReview: Review sessions for approval workflow
  - ReviewItem: Individual items pending approval

### Views
- `netbox_meraki/views.py` - Web interface views:
  - DashboardView: Main dashboard
  - SyncView: Trigger sync with mode selection
  - SyncLogView: View sync log details
  - ConfigView: Settings and configuration
  - SiteNameRule CRUD views
  - ReviewDetailView: View and manage review sessions
  - ReviewItemActionView: Approve/reject individual items
  - ReviewListView: List all review sessions

### Forms
- `netbox_meraki/forms.py` - Django forms:
  - PluginSettingsForm: Device role mappings
  - SiteNameRuleForm: Site name transformation rules

### Services
- `netbox_meraki/sync_service.py` - Core synchronization logic:
  - MerakiSyncService: Main sync orchestration
  - Support for auto/review/dry_run modes
  - Review item creation and application
  - Organization, network, device, VLAN, prefix sync

### API Client
- `netbox_meraki/meraki_client.py` - Meraki Dashboard API wrapper:
  - MerakiAPIClient: HTTP client for Meraki API
  - Methods for organizations, networks, devices, VLANs, subnets, ports

### URL Routing
- `netbox_meraki/urls.py` - URL patterns:
  - Dashboard, sync, config routes
  - Site name rule CRUD routes
  - Review management routes

### Admin
- `netbox_meraki/admin.py` - Django admin configuration:
  - SyncLog admin
  - PluginSettings admin
  - SiteNameRule admin
  - SyncReview admin
  - ReviewItem admin

## Templates

### Main Templates
- `netbox_meraki/templates/netbox_meraki/dashboard.html` - Main dashboard
- `netbox_meraki/templates/netbox_meraki/sync.html` - Sync trigger with mode selection
- `netbox_meraki/templates/netbox_meraki/synclog.html` - Sync log details
- `netbox_meraki/templates/netbox_meraki/config.html` - Configuration page (tabbed)

### Site Name Rule Templates
- `netbox_meraki/templates/netbox_meraki/sitenamerule_list.html` - List all rules
- `netbox_meraki/templates/netbox_meraki/sitenamerule_form.html` - Create/edit rule
- `netbox_meraki/templates/netbox_meraki/sitenamerule_confirm_delete.html` - Delete confirmation

### Review Templates
- `netbox_meraki/templates/netbox_meraki/review_list.html` - List all reviews
- `netbox_meraki/templates/netbox_meraki/review_detail.html` - Review detail with approve/reject

## REST API

### API Files
- `netbox_meraki/api/serializers.py` - DRF serializers for API
- `netbox_meraki/api/views.py` - API viewsets
- `netbox_meraki/api/urls.py` - API URL routing
- `netbox_meraki/api/__init__.py` - API package init

## Management Commands

- `netbox_meraki/management/commands/sync_meraki.py` - CLI sync command with --mode option
- `netbox_meraki/management/commands/__init__.py` - Commands package init
- `netbox_meraki/management/__init__.py` - Management package init

## Database Migrations

- `netbox_meraki/migrations/0001_initial.py` - Initial schema (SyncLog)
- `netbox_meraki/migrations/0002_add_settings_and_site_rules.py` - PluginSettings and SiteNameRule
- `netbox_meraki/migrations/0003_add_sync_review.py` - SyncReview and ReviewItem, sync_mode fields
- `netbox_meraki/migrations/__init__.py` - Migrations package init

## Documentation

- `README.md` - Complete plugin documentation
- `INSTALL.md` - Installation instructions
- `QUICKSTART.md` - Quick start guide
- `EXAMPLES.md` - Usage examples
- `CHANGELOG.md` - Version history and changes
- `LICENSE` - Apache 2.0 license

## Root Files

- `main.py` - Entry point (if needed)
- `pyproject.toml` - Python project configuration

## Features by File

### Sync Modes (v0.2.0)
**Models**: models.py (SyncReview, ReviewItem, sync_mode fields)
**Views**: views.py (ReviewDetailView, ReviewItemActionView, ReviewListView)
**Templates**: review_detail.html, review_list.html, sync.html (mode selection)
**Service**: sync_service.py (mode support, review item creation/application)
**Command**: sync_meraki.py (--mode option)
**Migration**: 0003_add_sync_review.py

### Device Role Mappings (v0.1.0)
**Models**: models.py (PluginSettings)
**Views**: views.py (ConfigView)
**Forms**: forms.py (PluginSettingsForm)
**Templates**: config.html
**Migration**: 0002_add_settings_and_site_rules.py

### Site Name Transformation (v0.1.0)
**Models**: models.py (SiteNameRule)
**Views**: views.py (SiteNameRule CRUD views)
**Forms**: forms.py (SiteNameRuleForm)
**Templates**: sitenamerule_*.html
**Service**: sync_service.py (applies transformation rules)
**Migration**: 0002_add_settings_and_site_rules.py

### Sync Logging (v0.1.0)
**Models**: models.py (SyncLog)
**Views**: views.py (SyncLogView)
**Templates**: synclog.html, dashboard.html
**Migration**: 0001_initial.py

## Key Integrations

### NetBox Integration
- Uses dcim.models (Device, Site, DeviceType, DeviceRole, Manufacturer)
- Uses ipam.models (VLAN, Prefix, IPAddress)
- Uses extras.models (Tag)
- Follows NetBox plugin architecture

### Meraki Integration
- Uses Meraki Dashboard API v1
- Authenticates with API key
- Retrieves organizations, networks, devices, VLANs, subnets

### Django Integration
- Django ORM for database operations
- Django views and forms
- Django templates with Bootstrap 5
- Django admin interface
- Django management commands
- Django REST Framework for API

## Configuration

### Required
- `meraki_api_key` - Meraki Dashboard API key

### Optional
- `meraki_base_url` - API endpoint (default: https://api.meraki.com/api/v1)
- `sync_interval` - Auto-sync interval
- `auto_create_*` - Auto-creation flags
- `default_device_role` - Default device role name
- `default_manufacturer` - Default manufacturer name

## Dependencies

### Python Packages
- requests >= 2.31.0 - HTTP client
- Django (via NetBox)
- Django REST Framework (via NetBox)

### NetBox Version
- NetBox 4.4.x (4.4.0 - 4.4.99)

## Testing Checklist

### Installation
- [ ] Plugin installs via pip
- [ ] Migrations run successfully
- [ ] Plugin appears in NetBox UI
- [ ] Configuration loads correctly

### Sync Modes
- [ ] Auto sync applies changes immediately
- [ ] Review mode creates review session
- [ ] Dry run previews without changes
- [ ] Mode selection works in UI
- [ ] Management command --mode option works

### Review Workflow
- [ ] Review sessions are created
- [ ] Review items are listed correctly
- [ ] Approve individual items
- [ ] Reject individual items
- [ ] Approve all items
- [ ] Reject all items
- [ ] Apply approved changes

### Core Sync
- [ ] Organizations sync
- [ ] Networks sync as sites
- [ ] Devices sync with correct types
- [ ] VLANs sync
- [ ] Prefixes sync
- [ ] Tags applied correctly

### Settings
- [ ] Device role mappings work
- [ ] Site name rules apply correctly
- [ ] Rules can be created/edited/deleted
- [ ] Rule priority ordering works

### UI
- [ ] Dashboard loads
- [ ] Sync page works
- [ ] Sync logs display
- [ ] Config page accessible
- [ ] Review pages render correctly

### API
- [ ] API endpoints accessible
- [ ] Trigger sync via API
- [ ] List sync logs via API
- [ ] Authentication works

### Admin
- [ ] All models visible in admin
- [ ] Read-only fields enforced
- [ ] List displays configured

## Deployment Notes

1. Install plugin package
2. Add to PLUGINS in configuration.py
3. Configure PLUGINS_CONFIG with API key
4. Run migrations
5. Restart NetBox and RQ
6. Configure device role mappings in UI
7. Add site name transformation rules if needed
8. Trigger initial sync (recommend review mode first)

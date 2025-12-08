# Changelog

All notable changes to the NetBox Meraki Sync Plugin will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.0.1] - 2025-12-08

### Fixed
- Performance improvements for background job execution
- Removed inefficient task polling mechanism

### Changed
- Migrated to NetBox native Job scheduling
- Simplified job infrastructure

## [0.2.0] - 2024-01-XX

### Added
- **Sync Modes**: Three synchronization modes for different use cases
  - Auto Sync: Immediate application of changes (default behavior)
  - Sync with Review: Stage changes for approval before applying
  - Dry Run: Preview changes without modifying NetBox
- **Review Management Interface**: Web UI for reviewing and approving staged changes
  - View all staged items (sites, devices, VLANs, prefixes)
  - Approve or reject individual items
  - Bulk approve/reject all items
  - Apply approved changes with one click
- **Review Models**: Database models for tracking review sessions and items
  - SyncReview: Tracks review sessions with status and counts
  - ReviewItem: Individual items pending approval with proposed/current data
- **Enhanced Sync Service**: Support for creating review items instead of direct DB changes
- **Management Command**: `--mode` option for CLI sync with mode selection
- **Admin Interface**: Django admin for SyncReview and ReviewItem models
- **Navigation**: Added "View Reviews" button to dashboard

### Changed
- Updated SyncLog model with sync_mode field and new status choices
- Updated PluginSettings model with configurable default sync mode
- Enhanced sync UI with radio button selection for sync modes
- Improved documentation with sync mode usage examples

## [0.1.0] - 2024-01-XX

### Added
- Initial plugin implementation
- One-way synchronization from Meraki Dashboard to NetBox
- Support for synchronizing:
  - Organizations
  - Networks (as Sites)
  - Devices (MX, MS, MR, MG, MV, MT)
  - VLANs
  - Prefixes/Subnets
- **Web UI**:
  - Dashboard with sync status and recent logs
  - Manual sync trigger
  - Sync log viewer with detailed results
  - Configuration page with device role mappings
- **Settings Page**:
  - Device role mappings per Meraki product type (MX, MS, MR, MG, MV, MT)
  - Site name transformation rules with regex support
  - CRUD interface for site name rules with priority ordering
- **REST API Endpoints**:
  - List and retrieve sync logs
  - Trigger synchronization via API
- **Management Command**: `sync_meraki` for CLI usage
- **Comprehensive Logging**: Track sync history with detailed statistics
- **Automatic Tagging**: All synced objects tagged with "Meraki"
- **Auto-creation**: Automatic creation of sites, device types, roles, and manufacturers
- **Database Migrations**: Initial schema and settings/rules schema
- **Documentation**:
  - Complete README with installation and usage
  - INSTALL guide with step-by-step instructions
  - QUICKSTART guide for rapid deployment
  - EXAMPLES with real-world use cases
  - Configuration examples and troubleshooting

### Technical Details
- Compatible with NetBox 4.4.x
- Python 3.10+ support
- Django-based plugin architecture
- Bootstrap 5 UI with Material Design Icons
- Idempotent sync operations
- Error handling and partial sync support

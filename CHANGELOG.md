# Changelog

All notable changes to the NetBox Meraki Sync Plugin.

## [1.1.0] - 2025-12-08

### Added
- Built-in scheduled job management interface
- Create, edit, and delete scheduled sync jobs from plugin UI
- Scheduled jobs visible on dashboard with execution history
- Support for custom sync intervals (minimum 5 minutes)
- Job-specific sync mode and network selection
- Job tracking system to identify plugin-created jobs

### Fixed
- NetBox 4.4.x compatibility (removed job.enabled references)
- Migration includes all required fields (reviewed, reviewed_by, sync_mode)
- Edit form now correctly displays selected sync mode and networks
- Form validation for network selection
- JavaScript auto-toggle for "sync all networks" checkbox

### Changed
- Simplified job status display (Active for all scheduled jobs)
- Removed Play/Pause toggle (not supported in NetBox 4.4.x)
- Jobs are now deleted to stop execution

## [1.0.0] - 2024-12-01

### Added
- **Three Sync Modes**:
  - Auto Sync: Apply changes immediately
  - Review Mode: Stage changes for manual approval
  - Dry Run: Preview changes without modifications
- **Review Management**: Web interface for reviewing staged changes
- **Advanced Filtering**:
  - Organization and network selection
  - Prefix include/exclude rules
  - Site name transformation rules
- **Tag Management**: Automatic tagging for synchronized objects
- **API Performance Controls**: Rate limiting and multithreading options
- **Comprehensive Logging**: Detailed sync history and error tracking

### Core Features
- Synchronize organizations, networks, and devices
- Import VLANs from MX security appliances
- Discover IP prefixes with site associations
- Create interfaces (WAN, SVI, wireless)
- Manage wireless LANs (SSIDs)
- Device role mapping based on product type
- Name transformation for standardization
- Cleanup of objects no longer in Meraki
### Technical Details
- Compatible with NetBox 4.4.x
- Python 3.10+ support
- RESTful API endpoints for automation
- Comprehensive error handling
- Database migration system

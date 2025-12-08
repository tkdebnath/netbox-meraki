"""Background jobs for NetBox Meraki plugin"""

try:
    from netbox.jobs import JobRunner
except ImportError:
    try:
        from extras.jobs import JobRunner
    except ImportError:
        from extras.jobs import Job as JobRunner

from .sync_service import MerakiSyncService
from .models import PluginSettings


class MerakiSyncJob(JobRunner):
    class Meta:
        name = "Meraki Dashboard Sync"
        description = "Synchronize networks, devices, VLANs, and prefixes from Meraki Dashboard to NetBox"
        field_order = ['sync_mode', 'organization_id', 'network_ids']
    
    sync_mode = None  # Will use PluginSettings default if not provided
    organization_id = None  # Optional: sync specific organization
    network_ids = None  # Optional: list of network IDs for selective sync
    
    def run(self, *args, **kwargs):
        # Get parameters from job data if provided
        sync_mode = kwargs.get('sync_mode') or self.sync_mode
        organization_id = kwargs.get('organization_id') or self.organization_id
        network_ids = kwargs.get('network_ids') or self.network_ids
        
        # If no sync_mode provided, use PluginSettings default
        if not sync_mode:
            settings = PluginSettings.get_settings()
            sync_mode = settings.sync_mode
        
        self.logger.info(f"Starting Meraki sync (mode: {sync_mode})")
        self.logger.info(f"Job kwargs received: {kwargs}")
        if organization_id:
            self.logger.info(f"Organization filter: {organization_id}")
        if network_ids:
            self.logger.info(f"Network filter: {type(network_ids)} with {len(network_ids) if isinstance(network_ids, list) else 'N/A'} networks")
            self.logger.info(f"Network IDs: {network_ids}")
        
        try:
            sync_service = MerakiSyncService(sync_mode=sync_mode)
            sync_log = sync_service.sync_all(
                organization_id=organization_id if organization_id else None,
                network_ids=network_ids if network_ids else None
            )
            
            self.logger.info(f"Sync completed with status: {sync_log.status}")
            self.logger.info(f"Organizations: {sync_log.organizations_synced}")
            self.logger.info(f"Networks: {sync_log.networks_synced}")
            self.logger.info(f"Devices: {sync_log.devices_synced}")
            self.logger.info(f"VLANs: {sync_log.vlans_synced}")
            self.logger.info(f"Prefixes: {sync_log.prefixes_synced}")
            
            if sync_log.deleted_devices or sync_log.deleted_vlans or sync_log.deleted_prefixes:
                self.logger.warning(
                    f"Cleanup: {sync_log.deleted_devices} devices, "
                    f"{sync_log.deleted_vlans} VLANs, "
                    f"{sync_log.deleted_prefixes} prefixes deleted"
                )
            
            if sync_log.errors:
                self.logger.error(f"{len(sync_log.errors)} errors occurred during sync")
                for error in sync_log.errors[:10]:
                    self.logger.error(f"  - {error}")
            
            return f"Sync completed: {sync_log.devices_synced} devices, {sync_log.vlans_synced} VLANs, {sync_log.prefixes_synced} prefixes"
            
        except Exception as e:
            self.logger.error(f"Sync failed: {str(e)}", exc_info=True)
            raise

jobs = [MerakiSyncJob]

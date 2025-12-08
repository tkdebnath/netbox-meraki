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
    
    def run(self, *args, **kwargs):
        settings = PluginSettings.get_settings()
        sync_mode = settings.sync_mode
        
        self.logger.info(f"Starting Meraki sync (mode: {sync_mode})")
        
        try:
            sync_service = MerakiSyncService(sync_mode=sync_mode)
            sync_log = sync_service.sync_all()
            
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

"""
Background jobs for NetBox Meraki plugin using NetBox's job system
"""
from extras.jobs import Job, JobButtonReceiver
from .sync_service import MerakiSyncService
from .models import PluginSettings


class MerakiSyncJob(Job):
    """
    Synchronize data from Meraki Dashboard to NetBox
    """
    class Meta:
        name = "Meraki Dashboard Sync"
        description = "Synchronize networks, devices, VLANs, and prefixes from Meraki Dashboard"
        commit_default = True
        scheduling_enabled = True
        task_queues = ['default']
    
    def run(self, *args, **kwargs):
        """Execute the sync"""
        settings = PluginSettings.get_settings()
        sync_mode = settings.sync_mode
        
        self.logger.info(f"Starting Meraki sync (mode: {sync_mode})")
        
        try:
            sync_service = MerakiSyncService(sync_mode=sync_mode)
            sync_log = sync_service.sync_all()
            
            # Log results
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
                for error in sync_log.errors[:10]:  # Show first 10 errors
                    self.logger.error(f"  - {error}")
            
            return f"Sync completed: {sync_log.devices_synced} devices, {sync_log.vlans_synced} VLANs, {sync_log.prefixes_synced} prefixes"
            
        except Exception as e:
            self.logger.error(f"Sync failed: {str(e)}", exc_info=True)
            raise


class ScheduledMerakiSyncJob(Job):
    """
    Scheduled Meraki sync job that respects scheduling settings
    """
    class Meta:
        name = "Scheduled Meraki Dashboard Sync"
        description = "Run scheduled Meraki sync (respects scheduling settings)"
        commit_default = True
        scheduling_enabled = True
        task_queues = ['default']
        hidden = False
    
    def run(self, *args, **kwargs):
        """Execute the sync if scheduled"""
        settings = PluginSettings.get_settings()
        
        if not settings.enable_scheduled_sync:
            self.logger.warning("Scheduled sync is disabled in settings")
            return "Scheduled sync is disabled"
        
        if not settings.should_run_scheduled_sync():
            next_sync = settings.next_scheduled_sync
            self.logger.info(f"Sync not due yet. Next sync: {next_sync}")
            return f"Sync not due yet. Next scheduled sync: {next_sync}"
        
        self.logger.info(f"Running scheduled sync (mode: {settings.scheduled_sync_mode})")
        
        try:
            sync_service = MerakiSyncService(sync_mode=settings.scheduled_sync_mode)
            sync_log = sync_service.sync_all()
            
            # Update next sync time
            settings.update_next_sync_time()
            
            # Log results
            self.logger.info(f"Sync completed with status: {sync_log.status}")
            self.logger.info(f"Devices: {sync_log.devices_synced}, VLANs: {sync_log.vlans_synced}, Prefixes: {sync_log.prefixes_synced}")
            
            if sync_log.deleted_devices or sync_log.deleted_vlans or sync_log.deleted_prefixes:
                self.logger.warning(
                    f"Cleanup: {sync_log.deleted_devices} devices, "
                    f"{sync_log.deleted_vlans} VLANs, "
                    f"{sync_log.deleted_prefixes} prefixes"
                )
            
            next_sync = settings.next_scheduled_sync
            return f"Sync completed. Next sync: {next_sync}"
            
        except Exception as e:
            self.logger.error(f"Scheduled sync failed: {str(e)}", exc_info=True)
            raise


# Register jobs
jobs = [MerakiSyncJob, ScheduledMerakiSyncJob]

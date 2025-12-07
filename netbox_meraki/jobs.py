"""
Background jobs for NetBox Meraki plugin using NetBox's job system
"""
from django.utils import timezone

try:
    # NetBox v4.2+ (newer import path)
    from netbox.jobs import JobRunner, system_job
    from core.choices import JobIntervalChoices
except ImportError:
    # Fallback for older NetBox versions
    try:
        from extras.jobs import JobRunner, system_job
        from core.choices import JobIntervalChoices
    except (ImportError, AttributeError):
        # If system_job doesn't exist, we'll handle it differently
        from extras.jobs import Job as JobRunner
        system_job = None
        JobIntervalChoices = None

# JobButtonReceiver may not exist in all versions, try to import it
try:
    from extras.jobs import JobButtonReceiver
except ImportError:
    JobButtonReceiver = None

from .sync_service import MerakiSyncService
from .models import PluginSettings, ScheduledSyncTask


# Only use Job for the manual sync jobs (not system jobs)
try:
    from extras.jobs import ScriptJob as Job
except ImportError:
    try:
        from extras.scripts import Script as Job
    except ImportError:
        Job = JobRunner


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


# Apply system_job decorator if available, otherwise it's a regular Job
if system_job is not None:
    @system_job(interval=1)  # Check every minute for more precise scheduling
    class ExecuteScheduledTasksJob(JobRunner):
        """
        Execute all due scheduled sync tasks
        This system job runs automatically every minute to check for and execute scheduled tasks
        """
        class Meta:
            name = "Execute Scheduled Sync Tasks"
            description = "Check for and execute all scheduled sync tasks that are due"
            hidden = True
        
        def run(self, *args, **kwargs):
            """Find and execute all tasks that are due to run"""
            now = timezone.now()
            
            # Get all enabled tasks that are due
            due_tasks = ScheduledSyncTask.objects.filter(
                enabled=True,
                next_run__lte=now,
                status__in=['pending', 'failed']
            )
            
            if not due_tasks.exists():
                self.logger.info('No scheduled tasks due for execution')
                return 'No tasks due'
            
            self.logger.info(f'Found {due_tasks.count()} task(s) due for execution')
            
            results = []
            for task in due_tasks:
                self.logger.info(f'Executing task: {task.name}')
                result = self.execute_task(task)
                results.append(result)
            
            return '\n'.join(results)
        
        def execute_task(self, task):
            """Execute a single scheduled task"""
            from datetime import timedelta
            
            try:
                # Update task status
                task.status = 'running'
                task.last_run = timezone.now()
                task.save()
                
                self.logger.info(f'  Mode: {task.sync_mode}')
                self.logger.info(f'  Components: Orgs={task.sync_organizations}, Sites={task.sync_sites}, '
                               f'Devices={task.sync_devices}, VLANs={task.sync_vlans}, Prefixes={task.sync_prefixes}')
                
                # Initialize sync service
                sync_service = MerakiSyncService()
                
                # Execute sync based on mode - sync_all handles all modes via network_ids parameter
                if task.sync_mode == 'full':
                    sync_log = sync_service.sync_all()
                
                elif task.sync_mode == 'selective':
                    sync_log = sync_service.sync_all(network_ids=task.selected_networks)
                
                elif task.sync_mode == 'single_network':
                    if not task.selected_networks:
                        raise ValueError('No network selected for single network sync')
                    sync_log = sync_service.sync_all(network_ids=[task.selected_networks[0]])
                
                else:
                    raise ValueError(f'Invalid sync mode: {task.sync_mode}')
                
                # Update task with success status
                task.status = 'completed'
                task.total_runs += 1
                task.successful_runs += 1
                task.last_error = ''
                
                # Calculate next run based on frequency
                task.next_run = self.calculate_next_run(task)
                task.save()
                
                result = (f'✓ {task.name}: Completed successfully. '
                         f'Devices: {sync_log.devices_synced}, VLANs: {sync_log.vlans_synced}, '
                         f'Prefixes: {sync_log.prefixes_synced}. Next run: {task.next_run}')
                self.logger.info(result)
                return result
                
            except Exception as e:
                # Update task with failure status
                task.status = 'failed'
                task.total_runs += 1
                task.failed_runs += 1
                task.last_error = str(e)
                
                # Still calculate next run so task will retry
                task.next_run = self.calculate_next_run(task)
                task.save()
                
                result = f'✗ {task.name}: Failed - {str(e)}'
                self.logger.error(result)
                return result
        
        def calculate_next_run(self, task):
            """Calculate the next run time based on task frequency"""
            from datetime import timedelta
            
            now = timezone.now()
            current_next_run = task.next_run or now
            
            if task.frequency == 'once':
                # One-time task, don't reschedule
                return None
            
            elif task.frequency == 'hourly':
                next_run = current_next_run + timedelta(hours=1)
            
            elif task.frequency == 'daily':
                next_run = current_next_run + timedelta(days=1)
            
            elif task.frequency == 'weekly':
                next_run = current_next_run + timedelta(days=7)
            
            else:
                # Default to daily if unknown
                next_run = current_next_run + timedelta(days=1)
            
            # If the calculated next run is still in the past, set it to now + interval
            if next_run <= now:
                if task.frequency == 'hourly':
                    next_run = now + timedelta(hours=1)
                elif task.frequency == 'daily':
                    next_run = now + timedelta(days=1)
                elif task.frequency == 'weekly':
                    next_run = now + timedelta(days=7)
            
            return next_run

else:
    # Fallback: Regular Job class for older NetBox versions without system_job
    class ExecuteScheduledTasksJob(Job):
        """
        Execute all due scheduled sync tasks
        This job should be manually scheduled to run frequently (e.g., every 1-5 minutes)
        """
        class Meta:
            name = "Execute Scheduled Sync Tasks"
            description = "Check for and execute all scheduled sync tasks that are due"
            commit_default = True
            scheduling_enabled = True
            task_queues = ['default']
            hidden = True
        
        def run(self, *args, **kwargs):
            """Find and execute all tasks that are due to run"""
            now = timezone.now()
            
            # Get all enabled tasks that are due
            due_tasks = ScheduledSyncTask.objects.filter(
                enabled=True,
                next_run__lte=now,
                status__in=['pending', 'failed']
            )
            
            if not due_tasks.exists():
                self.logger.info('No scheduled tasks due for execution')
                return 'No tasks due'
            
            self.logger.info(f'Found {due_tasks.count()} task(s) due for execution')
            
            results = []
            for task in due_tasks:
                self.logger.info(f'Executing task: {task.name}')
                result = self.execute_task(task)
                results.append(result)
            
            return '\n'.join(results)
        
        def execute_task(self, task):
            """Execute a single scheduled task"""
            from datetime import timedelta
            
            try:
                # Update task status
                task.status = 'running'
                task.last_run = timezone.now()
                task.save()
                
                self.logger.info(f'  Mode: {task.sync_mode}')
                self.logger.info(f'  Components: Orgs={task.sync_organizations}, Sites={task.sync_sites}, '
                               f'Devices={task.sync_devices}, VLANs={task.sync_vlans}, Prefixes={task.sync_prefixes}')
                
                # Initialize sync service
                sync_service = MerakiSyncService()
                
                # Execute sync based on mode - sync_all handles all modes via network_ids parameter
                if task.sync_mode == 'full':
                    sync_log = sync_service.sync_all()
                
                elif task.sync_mode == 'selective':
                    sync_log = sync_service.sync_all(network_ids=task.selected_networks)
                
                elif task.sync_mode == 'single_network':
                    if not task.selected_networks:
                        raise ValueError('No network selected for single network sync')
                    sync_log = sync_service.sync_all(network_ids=[task.selected_networks[0]])
                
                else:
                    raise ValueError(f'Invalid sync mode: {task.sync_mode}')
                
                # Update task with success status
                task.status = 'completed'
                task.total_runs += 1
                task.successful_runs += 1
                task.last_error = ''
                
                # Calculate next run based on frequency
                task.next_run = self.calculate_next_run(task)
                task.save()
                
                result = (f'✓ {task.name}: Completed successfully. '
                         f'Devices: {sync_log.devices_synced}, VLANs: {sync_log.vlans_synced}, '
                         f'Prefixes: {sync_log.prefixes_synced}. Next run: {task.next_run}')
                self.logger.info(result)
                return result
                
            except Exception as e:
                # Update task with failure status
                task.status = 'failed'
                task.total_runs += 1
                task.failed_runs += 1
                task.last_error = str(e)
                
                # Still calculate next run so task will retry
                task.next_run = self.calculate_next_run(task)
                task.save()
                
                result = f'✗ {task.name}: Failed - {str(e)}'
                self.logger.error(result)
                return result
        
        def calculate_next_run(self, task):
            """Calculate the next run time based on task frequency"""
            from datetime import timedelta
            
            now = timezone.now()
            current_next_run = task.next_run or now
            
            if task.frequency == 'once':
                # One-time task, don't reschedule
                return None
            
            elif task.frequency == 'hourly':
                next_run = current_next_run + timedelta(hours=1)
            
            elif task.frequency == 'daily':
                next_run = current_next_run + timedelta(days=1)
            
            elif task.frequency == 'weekly':
                next_run = current_next_run + timedelta(days=7)
            
            else:
                # Default to daily if unknown
                next_run = current_next_run + timedelta(days=1)
            
            # If the calculated next run is still in the past, set it to now + interval
            if next_run <= now:
                if task.frequency == 'hourly':
                    next_run = now + timedelta(hours=1)
                elif task.frequency == 'daily':
                    next_run = now + timedelta(days=1)
                elif task.frequency == 'weekly':
                    next_run = now + timedelta(days=7)
            
            return next_run


# Register jobs
jobs = [MerakiSyncJob, ScheduledMerakiSyncJob, ExecuteScheduledTasksJob]

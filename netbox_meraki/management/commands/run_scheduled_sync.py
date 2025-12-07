"""
Management command to execute scheduled sync tasks
"""
import logging
from datetime import timedelta
from django.core.management.base import BaseCommand
from django.utils import timezone
from netbox_meraki.models import ScheduledSyncTask
from netbox_meraki.sync_service import MerakiSyncService

logger = logging.getLogger('netbox_meraki')


class Command(BaseCommand):
    help = 'Execute scheduled Meraki sync tasks that are due'

    def add_arguments(self, parser):
        parser.add_argument(
            '--continuous',
            action='store_true',
            help='Run continuously, checking for tasks every minute',
        )
        parser.add_argument(
            '--interval',
            type=int,
            default=60,
            help='Check interval in seconds for continuous mode (default: 60)',
        )

    def handle(self, *args, **options):
        continuous = options['continuous']
        interval = options['interval']

        if continuous:
            self.stdout.write(
                self.style.SUCCESS(
                    f'Starting continuous task scheduler (checking every {interval} seconds)...'
                )
            )
            import time
            while True:
                self.execute_due_tasks()
                time.sleep(interval)
        else:
            self.execute_due_tasks()

    def execute_due_tasks(self):
        """Find and execute all tasks that are due to run"""
        now = timezone.now()
        
        # Get all enabled tasks that are due
        due_tasks = ScheduledSyncTask.objects.filter(
            enabled=True,
            next_run__lte=now,
            status__in=['pending', 'failed']
        )
        
        if not due_tasks.exists():
            self.stdout.write('No tasks due for execution')
            return
        
        for task in due_tasks:
            self.stdout.write(
                self.style.WARNING(f'Executing task: {task.name}')
            )
            self.execute_task(task)

    def execute_task(self, task):
        """Execute a single scheduled task"""
        try:
            # Update task status
            task.status = 'running'
            task.last_run = timezone.now()
            task.save()
            
            # Initialize sync service
            sync_service = MerakiSyncService()
            
            # Prepare sync options
            sync_options = {
                'sync_organizations': task.sync_organizations,
                'sync_sites': task.sync_sites,
                'sync_devices': task.sync_devices,
                'sync_vlans': task.sync_vlans,
                'sync_prefixes': task.sync_prefixes,
                'cleanup_orphaned': task.cleanup_orphaned,
            }
            
            # Execute sync based on mode
            if task.sync_mode == 'full':
                self.stdout.write('  Running full sync...')
                sync_log = sync_service.sync(**sync_options)
            
            elif task.sync_mode == 'selective':
                self.stdout.write(
                    f'  Running selective sync for {len(task.selected_networks)} networks...'
                )
                sync_log = sync_service.sync_selective_networks(
                    network_ids=task.selected_networks,
                    **sync_options
                )
            
            elif task.sync_mode == 'single_network':
                if not task.selected_networks:
                    raise ValueError('No network selected for single network sync')
                
                network_id = task.selected_networks[0]
                self.stdout.write(f'  Running sync for network {network_id}...')
                sync_log = sync_service.sync_single_network(
                    network_id=network_id,
                    **sync_options
                )
            
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
            
            self.stdout.write(
                self.style.SUCCESS(
                    f'✓ Task completed successfully. Next run: {task.next_run}'
                )
            )
            
        except Exception as e:
            # Update task with failure status
            task.status = 'failed'
            task.total_runs += 1
            task.failed_runs += 1
            task.last_error = str(e)
            
            # Still calculate next run so task will retry
            task.next_run = self.calculate_next_run(task)
            task.save()
            
            self.stdout.write(
                self.style.ERROR(f'✗ Task failed: {e}')
            )
            logger.exception(f'Scheduled task {task.name} failed')

    def calculate_next_run(self, task):
        """Calculate the next run time based on task frequency"""
        now = timezone.now()
        current_next_run = task.next_run or now
        
        if task.frequency == 'once':
            # One-time task, don't reschedule
            return None
        
        elif task.frequency == 'hourly':
            # Add 1 hour
            next_run = current_next_run + timedelta(hours=1)
        
        elif task.frequency == 'daily':
            # Add 1 day
            next_run = current_next_run + timedelta(days=1)
        
        elif task.frequency == 'weekly':
            # Add 7 days
            next_run = current_next_run + timedelta(days=7)
        
        else:
            # Default to daily if unknown
            next_run = current_next_run + timedelta(days=1)
        
        # If the calculated next run is still in the past, set it to now + interval
        # This handles cases where the scheduler was offline for a while
        if next_run <= now:
            if task.frequency == 'hourly':
                next_run = now + timedelta(hours=1)
            elif task.frequency == 'daily':
                next_run = now + timedelta(days=1)
            elif task.frequency == 'weekly':
                next_run = now + timedelta(days=7)
        
        return next_run

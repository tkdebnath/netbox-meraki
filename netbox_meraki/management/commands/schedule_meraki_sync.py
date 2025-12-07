"""
Management command to run scheduled Meraki sync
This command should be called by cron, systemd timer, or a task scheduler
"""
import logging
from django.core.management.base import BaseCommand
from django.utils import timezone

from netbox_meraki.models import PluginSettings
from netbox_meraki.sync_service import MerakiSyncService


logger = logging.getLogger('netbox_meraki')


class Command(BaseCommand):
    help = 'Check and run scheduled Meraki synchronization if due'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--force',
            action='store_true',
            help='Force sync even if not scheduled',
        )
        parser.add_argument(
            '--continuous',
            action='store_true',
            help='Run continuously, checking at regular intervals',
        )
        parser.add_argument(
            '--interval',
            type=int,
            default=60,
            help='Check interval in seconds for continuous mode (default: 60)',
        )
    
    def handle(self, *args, **options):
        force = options['force']
        continuous = options['continuous']
        interval = options['interval']
        
        if continuous:
            self.stdout.write(self.style.SUCCESS(
                f'Starting continuous scheduler (checking every {interval} seconds)...'
            ))
            self.run_continuous(interval)
        else:
            self.run_once(force)
    
    def run_once(self, force=False):
        """Run a single sync check"""
        settings = PluginSettings.get_settings()
        
        if not settings.enable_scheduled_sync and not force:
            self.stdout.write(self.style.WARNING(
                'Scheduled sync is disabled. Use --force to run anyway.'
            ))
            return
        
        if not force and not settings.should_run_scheduled_sync():
            next_sync = settings.next_scheduled_sync
            if next_sync:
                self.stdout.write(self.style.WARNING(
                    f'Next sync scheduled for: {next_sync}'
                ))
            else:
                self.stdout.write(self.style.WARNING(
                    'No sync scheduled'
                ))
            return
        
        # Run the sync
        self.stdout.write(self.style.SUCCESS(
            f'Running scheduled sync (mode: {settings.scheduled_sync_mode})...'
        ))
        
        try:
            sync_service = MerakiSyncService(sync_mode=settings.scheduled_sync_mode)
            sync_log = sync_service.sync_all()
            
            # Update next sync time
            settings.update_next_sync_time()
            
            self.stdout.write(self.style.SUCCESS(
                f'Sync completed: {sync_log.status}'
            ))
            self.stdout.write(f'  Organizations: {sync_log.organizations_synced}')
            self.stdout.write(f'  Networks: {sync_log.networks_synced}')
            self.stdout.write(f'  Devices: {sync_log.devices_synced}')
            self.stdout.write(f'  VLANs: {sync_log.vlans_synced}')
            self.stdout.write(f'  Prefixes: {sync_log.prefixes_synced}')
            
            if sync_log.deleted_devices or sync_log.deleted_vlans or sync_log.deleted_prefixes:
                self.stdout.write(self.style.WARNING(
                    f'  Cleaned: {sync_log.deleted_devices} devices, '
                    f'{sync_log.deleted_vlans} VLANs, '
                    f'{sync_log.deleted_prefixes} prefixes'
                ))
            
            if sync_log.errors:
                self.stdout.write(self.style.ERROR(
                    f'  Errors: {len(sync_log.errors)}'
                ))
                for error in sync_log.errors[:5]:  # Show first 5 errors
                    self.stdout.write(f'    - {error}')
            
            next_sync = settings.next_scheduled_sync
            if next_sync:
                self.stdout.write(self.style.SUCCESS(
                    f'Next sync scheduled for: {next_sync}'
                ))
            
        except Exception as e:
            logger.error(f'Scheduled sync failed: {e}', exc_info=True)
            self.stdout.write(self.style.ERROR(
                f'Sync failed: {str(e)}'
            ))
            raise
    
    def run_continuous(self, interval):
        """Run continuously, checking at regular intervals"""
        import time
        
        self.stdout.write(self.style.SUCCESS(
            'Press Ctrl+C to stop the scheduler'
        ))
        
        try:
            while True:
                try:
                    self.run_once()
                except Exception as e:
                    self.stdout.write(self.style.ERROR(
                        f'Error during sync: {e}'
                    ))
                    logger.error(f'Scheduled sync error: {e}', exc_info=True)
                
                # Wait for next check
                self.stdout.write(f'Waiting {interval} seconds...')
                time.sleep(interval)
                
        except KeyboardInterrupt:
            self.stdout.write(self.style.SUCCESS(
                '\nScheduler stopped'
            ))

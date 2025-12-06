"""
Django management command to sync Meraki data
"""
from django.core.management.base import BaseCommand
from netbox_meraki.sync_service import MerakiSyncService


class Command(BaseCommand):
    help = 'Synchronize data from Meraki Dashboard to NetBox'

    def add_arguments(self, parser):
        parser.add_argument(
            '--api-key',
            type=str,
            help='Meraki API key (overrides configuration)',
        )

    def handle(self, *args, **options):
        api_key = options.get('api_key')
        
        self.stdout.write('Starting Meraki synchronization...')
        
        try:
            sync_service = MerakiSyncService(api_key=api_key)
            sync_log = sync_service.sync_all()
            
            if sync_log.status == 'success':
                self.stdout.write(
                    self.style.SUCCESS(
                        f'✓ Synchronization completed successfully!\n'
                        f'  Organizations: {sync_log.organizations_synced}\n'
                        f'  Networks: {sync_log.networks_synced}\n'
                        f'  Devices: {sync_log.devices_synced}\n'
                        f'  VLANs: {sync_log.vlans_synced}\n'
                        f'  Prefixes: {sync_log.prefixes_synced}\n'
                        f'  Duration: {sync_log.duration_seconds:.2f}s'
                    )
                )
            elif sync_log.status == 'partial':
                self.stdout.write(
                    self.style.WARNING(
                        f'⚠ Synchronization completed with errors\n'
                        f'  Devices synced: {sync_log.devices_synced}\n'
                        f'  Errors: {len(sync_log.errors)}'
                    )
                )
                for error in sync_log.errors:
                    self.stdout.write(f'  - {error}')
            else:
                self.stdout.write(
                    self.style.ERROR(
                        f'✗ Synchronization failed: {sync_log.message}'
                    )
                )
                
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'✗ Synchronization failed: {str(e)}')
            )
            raise

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
        parser.add_argument(
            '--mode',
            type=str,
            choices=['auto', 'review', 'dry_run'],
            default='auto',
            help='Sync mode: auto (immediate), review (stage for approval), or dry_run (preview only)',
        )

    def handle(self, *args, **options):
        api_key = options.get('api_key')
        sync_mode = options.get('mode', 'auto')
        
        mode_desc = {
            'auto': 'Auto (immediate)',
            'review': 'Review (staged for approval)',
            'dry_run': 'Dry Run (preview only)'
        }
        
        self.stdout.write(f'Starting Meraki synchronization in {mode_desc[sync_mode]} mode...')
        
        try:
            sync_service = MerakiSyncService(api_key=api_key, sync_mode=sync_mode)
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
            elif sync_log.status == 'pending_review':
                self.stdout.write(
                    self.style.WARNING(
                        f'⚠ Synchronization staged for review\n'
                        f'  Review ID: {sync_log.review.pk}\n'
                        f'  Total items: {sync_log.review.items_total}\n'
                        f'  Please review changes in the web interface'
                    )
                )
            elif sync_log.status == 'dry_run':
                self.stdout.write(
                    self.style.SUCCESS(
                        f'✓ Dry run completed\n'
                        f'  Organizations: {sync_log.organizations_synced}\n'
                        f'  Networks: {sync_log.networks_synced}\n'
                        f'  Devices: {sync_log.devices_synced}\n'
                        f'  VLANs: {sync_log.vlans_synced}\n'
                        f'  Prefixes: {sync_log.prefixes_synced}\n'
                        f'  No changes applied to NetBox'
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

from netbox.plugins import PluginConfig


class MerakiConfig(PluginConfig):
    name = 'netbox_meraki'
    verbose_name = 'NetBox Meraki Sync'
    description = 'Synchronize Meraki networks, devices, VLANs, and prefixes to NetBox'
    version = '1.0.1'
    author = 'Tarani Debnath'
    base_url = 'meraki'
    required_settings = []
    default_settings = {
        'meraki_api_key': '',
        'meraki_base_url': 'https://api.meraki.com/api/v1',
        'sync_interval': 3600,
        'auto_create_sites': True,
        'auto_create_device_types': True,
        'auto_create_device_roles': True,
        'auto_create_manufacturers': True,
        'default_site_group': None,
        'default_manufacturer': 'Cisco Meraki',
        # Device role name defaults (can be overridden in configuration.py)
        'mx_device_role': 'Meraki Firewall',
        'ms_device_role': 'Meraki Switch',
        'mr_device_role': 'Meraki AP',
        'mg_device_role': 'Meraki Cellular Gateway',
        'mv_device_role': 'Meraki Camera',
        'mt_device_role': 'Meraki Sensor',
        'default_device_role': 'Meraki Unknown',
    }
    min_version = '4.4.0'
    max_version = '4.4.99'
    
    def ready(self):
        super().ready()
        self._cancel_running_tasks()
    
    def _cancel_running_tasks(self):
        """Cancel any running sync tasks from previous NetBox session"""
        try:
            from .models import SyncLog
            from django.utils import timezone
            
            running_syncs = SyncLog.objects.filter(status='running')
            if running_syncs.exists():
                for sync_log in running_syncs:
                    sync_log.status = 'failed'
                    sync_log.message = 'Sync interrupted by NetBox restart'
                    sync_log.add_progress_log('Sync cancelled due to NetBox restart', 'error')
                    sync_log.save()
                print(f"Cancelled {running_syncs.count()} running sync task(s) from previous session")
        except Exception as e:
            print(f"Error cancelling running tasks: {e}")


config = MerakiConfig

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


config = MerakiConfig

from netbox.plugins import PluginConfig


class MerakiConfig(PluginConfig):
    name = 'netbox_meraki'
    verbose_name = 'NetBox Meraki Sync'
    description = 'Synchronize Meraki networks, devices, VLANs, and prefixes to NetBox'
    version = '1.0.0'
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
        'default_device_role': 'Network Device',
        'default_manufacturer': 'Cisco Meraki',
    }
    min_version = '4.4.0'
    max_version = '4.4.99'


config = MerakiConfig

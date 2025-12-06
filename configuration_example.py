# Example NetBox configuration for Meraki plugin

# Add to your configuration.py

PLUGINS = [
    'netbox_meraki',
    # ... other plugins
]

PLUGINS_CONFIG = {
    'netbox_meraki': {
        # Required: Your Meraki Dashboard API key
        'meraki_api_key': 'your-meraki-api-key-here',
        
        # Optional: Meraki API base URL (default shown)
        'meraki_base_url': 'https://api.meraki.com/api/v1',
        
        # Optional: Sync interval in seconds (default: 3600 = 1 hour)
        'sync_interval': 3600,
        
        # Optional: Auto-create objects (all default to True)
        'auto_create_sites': True,
        'auto_create_device_types': True,
        'auto_create_device_roles': True,
        'auto_create_manufacturers': True,
        
        # Optional: Default values for created objects
        'default_site_group': None,  # Site group name or None
        'default_device_role': 'Network Device',
        'default_manufacturer': 'Cisco Meraki',
    }
}

# Using environment variables (recommended for production)
import os

PLUGINS_CONFIG = {
    'netbox_meraki': {
        'meraki_api_key': os.environ.get('MERAKI_API_KEY', ''),
        'meraki_base_url': os.environ.get('MERAKI_BASE_URL', 'https://api.meraki.com/api/v1'),
    }
}

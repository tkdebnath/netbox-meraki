# NetBox Configuration Snippets for Meraki Plugin

## 1. Environment Variable Configuration (.env file)

Add to `/opt/netbox/netbox/netbox/.env`:

```bash
# Meraki Plugin Configuration
MERAKI_API_KEY=your-actual-meraki-api-key-here
```

## 2. Configuration.py Setup

Add to `/opt/netbox/netbox/netbox/configuration.py`:

```python
import os

# ... your existing configuration ...

# Add plugin to PLUGINS list
PLUGINS = [
    'netbox_meraki',
    # ... your other plugins ...
]

# Configure the plugin
PLUGINS_CONFIG = {
    'netbox_meraki': {
        # Get API key from environment variable (recommended)
        'meraki_api_key': os.environ.get('MERAKI_API_KEY', ''),
        
        # Optional: Override default settings
        'meraki_base_url': 'https://api.meraki.com/api/v1',
        'sync_interval': 3600,  # seconds between auto-syncs
        'auto_create_sites': True,
        'auto_create_device_types': True,
        'auto_create_device_roles': True,
        'auto_create_manufacturers': True,
        'default_device_role': 'Network Device',
        'default_manufacturer': 'Cisco Meraki',
    },
    # ... your other plugin configs ...
}
```

## 3. Alternative: Direct Configuration (Not Recommended for Production)

```python
# Direct API key in configuration.py (less secure)
PLUGINS_CONFIG = {
    'netbox_meraki': {
        'meraki_api_key': 'your-actual-meraki-api-key-here',
        # ... other settings ...
    },
}
```

## 4. Complete Example Configuration.py

```python
import os
from pathlib import Path

#########################
#                       #
#   Required settings   #
#                       #
#########################

# This is a list of valid fully-qualified domain names (FQDNs)
ALLOWED_HOSTS = ['netbox.example.com', 'localhost']

# PostgreSQL database configuration
DATABASE = {
    'NAME': 'netbox',
    'USER': 'netbox',
    'PASSWORD': os.environ.get('DB_PASSWORD', ''),
    'HOST': 'localhost',
    'PORT': '',
    'CONN_MAX_AGE': 300,
}

# Redis database settings
REDIS = {
    'tasks': {
        'HOST': 'localhost',
        'PORT': 6379,
        'PASSWORD': '',
        'DATABASE': 0,
        'SSL': False,
    },
    'caching': {
        'HOST': 'localhost',
        'PORT': 6379,
        'PASSWORD': '',
        'DATABASE': 1,
        'SSL': False,
    }
}

# Secret key
SECRET_KEY = os.environ.get('SECRET_KEY', '')

#########################
#                       #
#   Optional settings   #
#                       #
#########################

# Plugins
PLUGINS = [
    'netbox_meraki',
]

PLUGINS_CONFIG = {
    'netbox_meraki': {
        'meraki_api_key': os.environ.get('MERAKI_API_KEY', ''),
        'meraki_base_url': 'https://api.meraki.com/api/v1',
        'sync_interval': 3600,
        'auto_create_sites': True,
        'auto_create_device_types': True,
        'auto_create_device_roles': True,
        'auto_create_manufacturers': True,
        'default_device_role': 'Network Device',
        'default_manufacturer': 'Cisco Meraki',
    },
}

# Additional settings
MEDIA_ROOT = '/opt/netbox/netbox/media'
REPORTS_ROOT = '/opt/netbox/netbox/reports'
SCRIPTS_ROOT = '/opt/netbox/netbox/scripts'
```

## 5. Environment File Example

Create or edit `/opt/netbox/netbox/netbox/.env`:

```bash
# NetBox Configuration
SECRET_KEY=your-secret-key-here
DB_PASSWORD=your-database-password

# Meraki Plugin
MERAKI_API_KEY=your-meraki-api-key-here
```

## 6. Quick Install Commands

```bash
# Navigate to NetBox installation
cd /opt/netbox
source venv/bin/activate

# Install plugin from source
cd /path/to/netbox-meraki
pip install -e .

# Or install from pip (when available)
# pip install netbox-meraki

# Run migrations
cd /opt/netbox/netbox
python manage.py migrate netbox_meraki

# Collect static files
python manage.py collectstatic --no-input

# Restart services
sudo systemctl restart netbox netbox-rq
```

## 7. Verify Installation

```bash
cd /opt/netbox/netbox
source /opt/netbox/venv/bin/activate

# Check migrations
python manage.py showmigrations netbox_meraki

# Expected output:
# netbox_meraki
#  [X] 0001_initial
#  [X] 0002_add_settings_and_site_rules
#  [X] 0003_add_sync_review

# Test dry run
python manage.py sync_meraki --mode dry_run
```

## 8. Configuration Settings Explained

| Setting | Default | Description |
|---------|---------|-------------|
| `meraki_api_key` | (required) | Your Meraki Dashboard API key |
| `meraki_base_url` | `https://api.meraki.com/api/v1` | Meraki API endpoint |
| `sync_interval` | `3600` | Seconds between auto-syncs (if scheduled) |
| `auto_create_sites` | `True` | Auto-create sites from Meraki networks |
| `auto_create_device_types` | `True` | Auto-create device types from Meraki models |
| `auto_create_device_roles` | `True` | Auto-create device roles |
| `auto_create_manufacturers` | `True` | Auto-create manufacturers |
| `default_device_role` | `Network Device` | Default role for devices |
| `default_manufacturer` | `Cisco Meraki` | Default manufacturer name |

## 9. Security Best Practices

1. **Always use environment variables** for API keys in production
2. **Restrict file permissions**:
   ```bash
   chmod 600 /opt/netbox/netbox/netbox/configuration.py
   chmod 600 /opt/netbox/netbox/netbox/.env
   ```
3. **Never commit** API keys to version control
4. **Use NetBox RBAC** to control who can trigger syncs
5. **Start with review mode** for production syncs

## 10. Troubleshooting Configuration

### Test API Key
```bash
curl -H "X-Cisco-Meraki-API-Key: YOUR_API_KEY" \
  https://api.meraki.com/api/v1/organizations
```

### Check Configuration
```python
# In NetBox shell
cd /opt/netbox/netbox
python manage.py shell

>>> from django.conf import settings
>>> settings.PLUGINS
['netbox_meraki']
>>> settings.PLUGINS_CONFIG['netbox_meraki']
{'meraki_api_key': '***', ...}
```

### View Logs
```bash
# NetBox log
tail -f /opt/netbox/netbox/netbox.log

# System log
journalctl -u netbox -f
```

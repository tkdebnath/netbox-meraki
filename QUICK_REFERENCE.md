# Quick Installation Reference Card

## One-Page Installation Guide

### 1️⃣ Install Plugin
```bash
cd /opt/netbox && source venv/bin/activate
cd /path/to/netbox-meraki && pip install -e .
```

### 2️⃣ Add to .env File
```bash
echo "MERAKI_API_KEY=your-api-key-here" >> /opt/netbox/netbox/netbox/.env
```

### 3️⃣ Update configuration.py
```python
import os

PLUGINS = ['netbox_meraki']

PLUGINS_CONFIG = {
    'netbox_meraki': {
        'meraki_api_key': os.environ.get('MERAKI_API_KEY', ''),
        'meraki_base_url': 'https://api.meraki.com/api/v1',
        'auto_create_sites': True,
        'auto_create_device_types': True,
        'auto_create_device_roles': True,
        'default_device_role': 'Network Device',
    }
}
```

### 4️⃣ Run Migrations
```bash
cd /opt/netbox/netbox
python manage.py migrate netbox_meraki
python manage.py collectstatic --no-input
```

### 5️⃣ Restart Services
```bash
sudo systemctl restart netbox netbox-rq
```

### 6️⃣ Test Installation
```bash
cd /opt/netbox/netbox
python manage.py sync_meraki --mode dry_run
```

---

## Usage Quick Reference

### Web Interface
1. Navigate to **Plugins > Meraki Sync**
2. Click **Sync Now**
3. Select mode: **Auto**, **Review**, or **Dry Run**
4. Click **Start Synchronization**

### CLI Commands
```bash
# Dry run (preview only)
python manage.py sync_meraki --mode dry_run

# Review mode (stage for approval)
python manage.py sync_meraki --mode review

# Auto mode (immediate sync)
python manage.py sync_meraki --mode auto
```

### Sync Modes
- **Auto**: Immediate - changes applied instantly
- **Review**: Staged - approve/reject before applying
- **Dry Run**: Preview - no changes made

---

## Configuration Locations

| File | Purpose |
|------|---------|
| `/opt/netbox/netbox/netbox/.env` | Environment variables (API key) |
| `/opt/netbox/netbox/netbox/configuration.py` | Plugin configuration |

---

## Common Commands

```bash
# Activate venv
cd /opt/netbox && source venv/bin/activate

# Check migrations
python manage.py showmigrations netbox_meraki

# View sync logs
tail -f /opt/netbox/netbox/netbox.log

# Restart services
sudo systemctl restart netbox netbox-rq
```

---

## Getting Meraki API Key

1. Login to Meraki Dashboard
2. **Organization > Settings > Dashboard API access**
3. Enable API access
4. **Generate new API key**
5. Copy and save securely

---

## File Permissions (Security)

```bash
chmod 600 /opt/netbox/netbox/netbox/configuration.py
chmod 600 /opt/netbox/netbox/netbox/.env
```

---

## Troubleshooting

❌ **Plugin not visible**
- Check `PLUGINS` list in configuration.py
- Restart NetBox services
- Check logs: `tail -f /opt/netbox/netbox/netbox.log`

❌ **API authentication fails**
- Verify API key in .env file
- Test: `curl -H "X-Cisco-Meraki-API-Key: KEY" https://api.meraki.com/api/v1/organizations`

❌ **Migrations fail**
- Run: `python manage.py migrate netbox_meraki`
- Check database connectivity

---

## URLs

- Dashboard: `/plugins/meraki/`
- Configuration: `/plugins/meraki/config/`
- Reviews: `/plugins/meraki/reviews/`
- API: `/api/plugins/meraki/`

---

## Support Files

- `INSTALLATION_GUIDE.md` - Full installation instructions
- `CONFIGURATION_EXAMPLES.md` - Configuration snippets
- `QUICKSTART.md` - Quick start guide
- `EXAMPLES.md` - Usage examples
- `README.md` - Complete documentation

---

**Version:** 0.2.0  
**NetBox:** 4.4.x  
**Python:** 3.10+

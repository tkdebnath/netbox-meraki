#!/bin/bash
# NetBox Meraki Sync Cron Examples
# Add these to your crontab using: crontab -e

# Run every hour at minute 0
# 0 * * * * cd /opt/netbox/netbox && /opt/netbox/venv/bin/python manage.py schedule_meraki_sync >> /var/log/netbox/meraki-sync.log 2>&1

# Run every 30 minutes
# */30 * * * * cd /opt/netbox/netbox && /opt/netbox/venv/bin/python manage.py schedule_meraki_sync >> /var/log/netbox/meraki-sync.log 2>&1

# Run every 15 minutes
# */15 * * * * cd /opt/netbox/netbox && /opt/netbox/venv/bin/python manage.py schedule_meraki_sync >> /var/log/netbox/meraki-sync.log 2>&1

# Run every 5 minutes
# */5 * * * * cd /opt/netbox/netbox && /opt/netbox/venv/bin/python manage.py schedule_meraki_sync >> /var/log/netbox/meraki-sync.log 2>&1

# Run daily at 2:00 AM
# 0 2 * * * cd /opt/netbox/netbox && /opt/netbox/venv/bin/python manage.py schedule_meraki_sync >> /var/log/netbox/meraki-sync.log 2>&1

# Run on weekdays at 6:00 AM
# 0 6 * * 1-5 cd /opt/netbox/netbox && /opt/netbox/venv/bin/python manage.py schedule_meraki_sync >> /var/log/netbox/meraki-sync.log 2>&1

# Force sync every Sunday at 3:00 AM (ignores schedule settings)
# 0 3 * * 0 cd /opt/netbox/netbox && /opt/netbox/venv/bin/python manage.py schedule_meraki_sync --force >> /var/log/netbox/meraki-sync.log 2>&1

# Example with email notifications on errors
# */30 * * * * cd /opt/netbox/netbox && /opt/netbox/venv/bin/python manage.py schedule_meraki_sync 2>&1 | grep -i error && echo "Meraki sync error detected" | mail -s "NetBox Meraki Sync Error" admin@example.com

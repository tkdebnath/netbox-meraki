# Quick Reference: Version 0.6.0 Features

## Live Progress Tracking

### View Progress
1. Dashboard → "Run Sync Now"
2. Auto-redirected to sync log page
3. Watch progress bar advance
4. See live log entries appear
5. Monitor object counts

### Controls
- **Pause Auto-Refresh**: Stop updates temporarily
- **Resume Auto-Refresh**: Continue live updates
- **Refresh Interval**: Every 3 seconds

### Log Levels
- 🔵 **INFO**: Normal progress
- 🟡 **WARN**: Non-critical issues
- 🔴 **ERROR**: Failures

## Sync Cancellation

### Cancel via UI
1. Go to running sync log page
2. Click "Cancel Sync" (yellow button)
3. Confirm dialog
4. Wait for current operation to complete

### Cancel via API
```bash
curl -X POST \
  http://netbox/api/plugins/netbox-meraki/sync-logs/{id}/cancel/ \
  -H "Authorization: Token YOUR_TOKEN"
```

### What Happens
- Current operation completes
- No new operations started
- Status set to "failed"
- Message: "Sync cancelled by user"

## Enhanced Review Mode

### Object Categories
1. **Sites** (Blue) - Networks as sites
2. **Devices** (Green) - Full device details
3. **VLANs** (Yellow) - VLAN configurations
4. **Prefixes** (Cyan) - IP subnets
5. **SSIDs** (Gray) - Wireless networks

### Actions
- **Individual**: Approve/Reject per item
- **Bulk**: Approve All / Reject All
- **Apply**: Execute approved changes

### Preview Details
Each item shows:
- All field values
- Related objects (badges)
- Current vs. new (for updates)
- Action type (CREATE/UPDATE/SKIP)

## Auto Device Type Creation

### Automatic
- Missing types created during sync
- Part number = model number
- No manual setup required

### Manual Override
1. Device Types → Find type
2. Edit part number
3. Save (won't be overridden)

## SSID Tracking

### Storage
- Custom field: `meraki_ssids`
- Example: "Employee-WiFi, Guest-WiFi, IoT"
- Only on wireless APs (MR devices)

### Statistics
- SSID counter in sync log
- Included in progress updates
- API responses include count

## API Quick Reference

### Get Progress
```bash
GET /api/plugins/netbox-meraki/sync-logs/{id}/progress/
```
Returns: status, progress_percent, current_operation, logs, counters

### Cancel Sync
```bash
POST /api/plugins/netbox-meraki/sync-logs/{id}/cancel/
```
Returns: message, cancelled_at

### Trigger Sync
```bash
POST /api/plugins/netbox-meraki/sync-logs/trigger_sync/
```
Returns: sync log object with ID

## Monitoring Script Example

```python
import requests
import time

NETBOX = "http://netbox"
TOKEN = "your_token"
headers = {"Authorization": f"Token {TOKEN}"}

# Start sync
r = requests.post(f"{NETBOX}/api/plugins/netbox-meraki/sync-logs/trigger_sync/", 
                  headers=headers)
sync_id = r.json()['id']

# Monitor
while True:
    r = requests.get(f"{NETBOX}/api/plugins/netbox-meraki/sync-logs/{sync_id}/progress/", 
                     headers=headers)
    data = r.json()
    
    print(f"{data['progress_percent']}% - {data['current_operation']}")
    
    if data['status'] != 'running':
        print(f"Done: {data['status']}")
        break
    
    time.sleep(3)
```

## Migration

```bash
# Update code
git pull

# Run migration
python manage.py migrate netbox_meraki

# Restart services
sudo systemctl restart netbox netbox-rq

# Verify
python manage.py showmigrations netbox_meraki
```

## Troubleshooting

### Progress Not Updating
- Check browser console for errors
- Verify API endpoint accessible
- Clear browser cache
- Try different browser

### Cancel Not Working
- Wait for current operation (30-60s)
- Verify sync status is "running"
- Check NetBox logs for errors

### Missing Device Types
- Check "Auto-created device type" in logs
- Verify "Cisco Meraki" manufacturer exists
- Check model name is valid

### No SSID Data
- Ensure device is MR (wireless AP)
- Verify SSIDs enabled in Meraki
- Check custom field exists

## Best Practices

✅ **Use Review Mode First** - See what will change  
✅ **Monitor Progress** - Watch for errors  
✅ **Cancel if Needed** - Don't let bad syncs run  
✅ **Verify Device Types** - Check auto-created types  
✅ **Clean Old Logs** - Remove old sync logs periodically  

## Support Resources

- **Full Guide**: ENHANCED_FEATURES.md
- **Implementation**: VERSION_0.6.0_SUMMARY.md
- **Changelog**: README.md
- **NetBox Logs**: `/var/log/netbox/`

## Version Info

**Current**: 0.6.0  
**Released**: December 2025  
**NetBox**: 4.4.x or higher  
**Python**: 3.10 or higher  

---

**Quick Tip**: Start with dry run mode to see what would happen without making changes!

# NetBox Meraki Plugin - Example Usage and Output

## Example 1: First Sync via Web UI

### Step 1: Navigate to Dashboard
Go to: **Plugins > Meraki Sync**

**Dashboard Display:**
```
┌─────────────────────────────────────────────────────────────┐
│ Configuration Status                                         │
│ ✓ API Key Configured                                        │
└─────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│ Latest Sync                                                  │
│ No synchronization performed yet.                           │
└─────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│ Quick Actions                                                │
│ [Sync Now]  [View Configuration]                            │
└─────────────────────────────────────────────────────────────┘
```

### Step 2: Click "Sync Now"

**Confirmation Page:**
```
Sync from Meraki Dashboard

This will start a synchronization from the Meraki Dashboard API to NetBox.

Note: The following data will be synchronized:
• Organizations
• Networks (as Sites)
• Devices
• VLANs
• Prefixes/Subnets

⚠️ Warning: This operation may take several minutes depending on 
   the size of your Meraki deployment.

[Start Synchronization]  [Cancel]
```

### Step 3: View Results

**Success Message:**
```
✓ Synchronization completed successfully. 
  Synced 42 devices, 18 VLANs, 24 prefixes.
```

**Sync Log Details:**
```
┌─────────────────────────────────────────────────────────────┐
│ Synchronization Information                                  │
│                                                              │
│ Timestamp:  2025-12-06 14:30:22                             │
│ Status:     Success                                          │
│ Duration:   45.23 seconds                                    │
│ Message:    Synchronized 3 organizations                     │
└─────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│ Synchronization Statistics                                   │
│                                                              │
│    3              12            42           18         24   │
│ Organizations   Networks     Devices       VLANs    Prefixes │
└─────────────────────────────────────────────────────────────┘
```

## Example 2: CLI Sync

### Command:
```bash
python manage.py sync_meraki
```

### Output:
```
Starting Meraki synchronization...
✓ Synchronization completed successfully!
  Organizations: 3
  Networks: 12
  Devices: 42
  VLANs: 18
  Prefixes: 24
  Duration: 45.23s
```

### With Custom API Key:
```bash
python manage.py sync_meraki --api-key YOUR_CUSTOM_KEY
```

### Partial Success Example:
```bash
python manage.py sync_meraki
```

**Output:**
```
Starting Meraki synchronization...
⚠ Synchronization completed with errors
  Devices synced: 38
  Errors: 4
  - Error syncing device MX-01: Connection timeout
  - Error syncing device MS-Switch-05: Invalid model
  - Error syncing VLAN 100: Invalid subnet format
  - Error syncing prefix 10.0.0.0/8: Overlapping prefix exists
```

## Example 3: API Usage

### Trigger Sync via API:

**Request:**
```bash
curl -X POST \
  https://netbox.example.com/api/plugins/meraki/sync-logs/trigger_sync/ \
  -H "Authorization: Token 0123456789abcdef0123456789abcdef01234567" \
  -H "Content-Type: application/json"
```

**Response:**
```json
{
    "id": 15,
    "timestamp": "2025-12-06T14:30:22.123456Z",
    "status": "success",
    "message": "Synchronized 3 organizations",
    "organizations_synced": 3,
    "networks_synced": 12,
    "devices_synced": 42,
    "vlans_synced": 18,
    "prefixes_synced": 24,
    "errors": [],
    "duration_seconds": 45.23
}
```

### List Sync Logs:

**Request:**
```bash
curl https://netbox.example.com/api/plugins/meraki/sync-logs/ \
  -H "Authorization: Token 0123456789abcdef0123456789abcdef01234567"
```

**Response:**
```json
{
    "count": 10,
    "next": null,
    "previous": null,
    "results": [
        {
            "id": 15,
            "timestamp": "2025-12-06T14:30:22.123456Z",
            "status": "success",
            "message": "Synchronized 3 organizations",
            "organizations_synced": 3,
            "networks_synced": 12,
            "devices_synced": 42,
            "vlans_synced": 18,
            "prefixes_synced": 24,
            "errors": [],
            "duration_seconds": 45.23
        },
        {
            "id": 14,
            "timestamp": "2025-12-06T13:30:15.654321Z",
            "status": "success",
            "message": "Synchronized 3 organizations",
            "organizations_synced": 3,
            "networks_synced": 12,
            "devices_synced": 42,
            "vlans_synced": 18,
            "prefixes_synced": 24,
            "errors": [],
            "duration_seconds": 43.87
        }
    ]
}
```

## Example 4: Cron Job Setup

### Add to crontab:
```bash
crontab -e
```

### Entry (sync every hour):
```cron
# Meraki sync every hour
0 * * * * cd /opt/netbox && source venv/bin/activate && python manage.py sync_meraki >> /var/log/netbox/meraki-sync.log 2>&1
```

### Log file output (`/var/log/netbox/meraki-sync.log`):
```
[2025-12-06 14:00:01] Starting Meraki synchronization...
[2025-12-06 14:00:46] ✓ Synchronization completed successfully!
[2025-12-06 14:00:46]   Organizations: 3
[2025-12-06 14:00:46]   Networks: 12
[2025-12-06 14:00:46]   Devices: 42
[2025-12-06 14:00:46]   VLANs: 18
[2025-12-06 14:00:46]   Prefixes: 24
[2025-12-06 14:00:46]   Duration: 45.23s

[2025-12-06 15:00:01] Starting Meraki synchronization...
[2025-12-06 15:00:43] ✓ Synchronization completed successfully!
[2025-12-06 15:00:43]   Organizations: 3
[2025-12-06 15:00:43]   Networks: 12
[2025-12-06 15:00:43]   Devices: 42
[2025-12-06 15:00:43]   VLANs: 18
[2025-12-06 15:00:43]   Prefixes: 24
[2025-12-06 15:00:43]   Duration: 42.15s
```

## Example 5: What Gets Created in NetBox

### After First Sync:

#### Sites Created:
```
• Headquarters Network
• Branch Office 1
• Branch Office 2
• Remote Site - DC1
• Remote Site - DC2
...
(12 total sites)
```

#### Devices Created:
```
Headquarters Network:
  • MX-HQ-01 (MX250, active)
  • MS-HQ-Core-01 (MS425, active)
  • MS-HQ-Access-01 (MS220, active)
  • MR-HQ-AP-01 (MR56, active)
  ...

Branch Office 1:
  • MX-BR1-01 (MX68, active)
  • MS-BR1-01 (MS120, active)
  • MR-BR1-AP-01 (MR46, active)
  ...

(42 total devices)
```

#### VLANs Created:
```
Headquarters Network VLANs:
  • VLAN 1: Management (10.1.1.0/24)
  • VLAN 10: Data (10.1.10.0/24)
  • VLAN 20: Voice (10.1.20.0/24)
  • VLAN 30: Guest (10.1.30.0/24)
  ...

(18 total VLANs)
```

#### Prefixes Created:
```
Site: Headquarters Network
  • 10.1.1.0/24 (VLAN 1: Management)
  • 10.1.10.0/24 (VLAN 10: Data)
  • 10.1.20.0/24 (VLAN 20: Voice)
  • 10.1.30.0/24 (VLAN 30: Guest)
  ...

(24 total prefixes)
```

#### Tags Applied:
```
All objects tagged with: "Meraki"
```

## Example 6: Configuration Display

### Visit: Plugins > Meraki Sync > Configuration

**Display:**
```
┌─────────────────────────────────────────────────────────────┐
│ Plugin Settings                                              │
│                                                              │
│ Note: Configuration is managed through NetBox's             │
│ configuration file.                                          │
│                                                              │
│ meraki_api_key              ****6789                         │
│ meraki_base_url             https://api.meraki.com/api/v1   │
│ sync_interval               3600                             │
│ auto_create_sites           Enabled                          │
│ auto_create_device_types    Enabled                          │
│ auto_create_device_roles    Enabled                          │
│ auto_create_manufacturers   Enabled                          │
│ default_site_group          Not set                          │
│ default_device_role         Network Device                   │
│ default_manufacturer        Cisco Meraki                     │
└─────────────────────────────────────────────────────────────┘
```

## Example 7: Error Handling

### Scenario: Partial API Failure

**Sync Log Details:**
```
┌─────────────────────────────────────────────────────────────┐
│ Synchronization Information                                  │
│                                                              │
│ Timestamp:  2025-12-06 15:45:12                             │
│ Status:     Partial Success                                  │
│ Duration:   38.45 seconds                                    │
│ Message:    Synchronized 3 organizations                     │
└─────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│ Synchronization Statistics                                   │
│                                                              │
│    3              12            38           16         22   │
│ Organizations   Networks     Devices       VLANs    Prefixes │
└─────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│ Errors                                                       │
│                                                              │
│ • Error syncing device MX-Branch-03: Connection timeout      │
│ • Error syncing device MS-RemoteSite-01: Invalid model MX99 │
│ • Error syncing VLAN 999: Invalid VLAN ID                   │
│ • Could not sync prefix 192.168.1.0/24: Overlapping prefix  │
└─────────────────────────────────────────────────────────────┘
```

## Example 8: Dashboard After Multiple Syncs

```
┌─────────────────────────────────────────────────────────────────────────────┐
│ Recent Sync Logs                                                             │
│                                                                              │
│ Timestamp           Status    Orgs  Networks  Devices  VLANs  Prefixes  Dur │
│ 2025-12-06 15:00   Success    3     12        42       18     24       45s  │
│ 2025-12-06 14:00   Success    3     12        42       18     24       43s  │
│ 2025-12-06 13:00   Partial    3     12        38       16     22       38s  │
│ 2025-12-06 12:00   Success    3     12        42       18     24       44s  │
│ 2025-12-06 11:00   Success    3     12        42       18     24       46s  │
└─────────────────────────────────────────────────────────────────────────────┘
```

## Summary

This plugin provides multiple ways to interact with Meraki data:

1. **Web UI**: Visual dashboard and sync management
2. **CLI**: Command-line automation
3. **REST API**: Programmatic integration
4. **Cron**: Scheduled automation

All methods provide:
- ✅ Detailed statistics
- ✅ Error reporting
- ✅ Status tracking
- ✅ Historical logs
- ✅ Progress monitoring

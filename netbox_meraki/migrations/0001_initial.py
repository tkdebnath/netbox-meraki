# Generated initial migration for NetBox Meraki plugin

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = [
    ]

    operations = [
        # PluginSettings Model
        migrations.CreateModel(
            name='PluginSettings',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False)),
                ('auto_create_sites', models.BooleanField(default=True, help_text='Automatically create sites from Meraki networks')),
                ('auto_create_device_types', models.BooleanField(default=True, help_text='Automatically create device types for Meraki models')),
                ('auto_create_device_roles', models.BooleanField(default=True, help_text='Automatically create device roles if they do not exist')),
                ('auto_create_manufacturers', models.BooleanField(default=True, help_text='Automatically create manufacturers if they do not exist')),
                ('default_site_group', models.CharField(blank=True, help_text='Default site group name for created sites', max_length=100)),
                ('default_manufacturer', models.CharField(default='Cisco Meraki', help_text='Default manufacturer name', max_length=100)),
                ('mx_device_role', models.CharField(default='Meraki Firewall', help_text='Default device role for MX appliances', max_length=100, verbose_name='MX Device Role')),
                ('ms_device_role', models.CharField(default='Meraki Switch', help_text='Default device role for MS switches', max_length=100, verbose_name='MS Device Role')),
                ('mr_device_role', models.CharField(default='Meraki AP', help_text='Default device role for MR access points', max_length=100, verbose_name='MR Device Role')),
                ('mg_device_role', models.CharField(default='Meraki Cellular Gateway', help_text='Default device role for MG gateways', max_length=100, verbose_name='MG Device Role')),
                ('mv_device_role', models.CharField(default='Meraki Camera', help_text='Default device role for MV cameras', max_length=100, verbose_name='MV Device Role')),
                ('mt_device_role', models.CharField(default='Meraki Sensor', help_text='Default device role for MT sensors', max_length=100, verbose_name='MT Device Role')),
                ('default_device_role', models.CharField(default='Meraki Unknown', help_text='Default device role for unknown product types', max_length=100, verbose_name='Default Device Role')),
                ('sync_mode', models.CharField(choices=[('auto', 'Auto Sync'), ('review', 'Sync with Review'), ('dry_run', 'Dry Run Only')], default='review', help_text='Default synchronization mode: Auto (immediate), Review (requires approval), or Dry Run (preview only)', max_length=20, verbose_name='Default Sync Mode')),
                ('device_name_transform', models.CharField(choices=[('keep', 'Keep Original'), ('upper', 'UPPERCASE'), ('lower', 'lowercase'), ('title', 'Title Case')], default='keep', help_text='How to transform device names from Meraki', max_length=20, verbose_name='Device Name Transform')),
                ('site_name_transform', models.CharField(choices=[('keep', 'Keep Original'), ('upper', 'UPPERCASE'), ('lower', 'lowercase'), ('title', 'Title Case')], default='keep', help_text='How to transform site names from Meraki', max_length=20, verbose_name='Site Name Transform')),
                ('vlan_name_transform', models.CharField(choices=[('keep', 'Keep Original'), ('upper', 'UPPERCASE'), ('lower', 'lowercase'), ('title', 'Title Case')], default='keep', help_text='How to transform VLAN names from Meraki', max_length=20, verbose_name='VLAN Name Transform')),
                ('ssid_name_transform', models.CharField(choices=[('keep', 'Keep Original'), ('upper', 'UPPERCASE'), ('lower', 'lowercase'), ('title', 'Title Case')], default='keep', help_text='How to transform SSID names from Meraki', max_length=20, verbose_name='SSID Name Transform')),
                ('site_tags', models.CharField(blank=True, default='Meraki', help_text='Comma-separated list of tags to apply to sites (e.g., "Meraki,Production")', max_length=500, verbose_name='Site Tags')),
                ('device_tags', models.CharField(blank=True, default='Meraki', help_text='Comma-separated list of tags to apply to devices (e.g., "Meraki,Network-Device")', max_length=500, verbose_name='Device Tags')),
                ('vlan_tags', models.CharField(blank=True, default='Meraki', help_text='Comma-separated list of tags to apply to VLANs (e.g., "Meraki,VLAN")', max_length=500, verbose_name='VLAN Tags')),
                ('prefix_tags', models.CharField(blank=True, default='Meraki', help_text='Comma-separated list of tags to apply to prefixes/subnets (e.g., "Meraki,Subnet")', max_length=500, verbose_name='Prefix/Subnet Tags')),
                ('process_unmatched_sites', models.BooleanField(default=False, help_text='If enabled, sites that do not match any name rules will still be processed using their original network name. If disabled, only sites matching name rules will be synced.', verbose_name='Process Sites Not Matching Name Rules')),
                ('enable_api_throttling', models.BooleanField(default=True, help_text='Enable rate limiting to avoid overwhelming Meraki Dashboard API (recommended)', verbose_name='Enable API Throttling')),
                ('api_requests_per_second', models.IntegerField(default=5, help_text='Maximum API requests per second (Meraki limit is 10/sec, recommended: 5)', verbose_name='API Requests Per Second')),
                ('enable_multithreading', models.BooleanField(default=False, help_text='Use multiple threads to fetch data from Meraki API in parallel (faster but may hit rate limits)', verbose_name='Enable Multithreading')),
                ('max_worker_threads', models.IntegerField(default=3, help_text='Maximum number of concurrent threads for API requests (recommended: 2-5)', verbose_name='Max Worker Threads')),
            ],
            options={
                'verbose_name': 'Plugin Settings',
                'verbose_name_plural': 'Plugin Settings',
            },
        ),
        
        # SyncLog Model
        migrations.CreateModel(
            name='SyncLog',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False)),
                ('timestamp', models.DateTimeField(auto_now_add=True)),
                ('status', models.CharField(choices=[('success', 'Success'), ('partial', 'Partial Success'), ('failed', 'Failed'), ('running', 'Running'), ('dry_run', 'Dry Run'), ('pending_review', 'Pending Review')], max_length=20)),
                ('message', models.TextField(blank=True)),
                ('organizations_synced', models.IntegerField(default=0)),
                ('networks_synced', models.IntegerField(default=0)),
                ('devices_synced', models.IntegerField(default=0)),
                ('vlans_synced', models.IntegerField(default=0)),
                ('prefixes_synced', models.IntegerField(default=0)),
                ('ssids_synced', models.IntegerField(default=0)),
                ('deleted_sites', models.IntegerField(default=0)),
                ('deleted_devices', models.IntegerField(default=0)),
                ('deleted_vlans', models.IntegerField(default=0)),
                ('deleted_prefixes', models.IntegerField(default=0)),
                ('updated_prefixes', models.IntegerField(default=0)),
                ('errors', models.JSONField(blank=True, default=list)),
                ('duration_seconds', models.FloatField(blank=True, null=True)),
                ('progress_logs', models.JSONField(blank=True, default=list, help_text='Live progress log entries')),
                ('current_operation', models.CharField(blank=True, help_text='Current sync operation', max_length=255)),
                ('progress_percent', models.IntegerField(default=0, help_text='Overall progress percentage')),
                ('cancel_requested', models.BooleanField(default=False, help_text='Flag to cancel ongoing sync')),
                ('cancelled_at', models.DateTimeField(blank=True, help_text='When sync was cancelled', null=True)),
                ('sync_mode', models.CharField(choices=[('auto', 'Auto Sync'), ('review', 'Sync with Review'), ('dry_run', 'Dry Run')], default='auto', max_length=20)),
            ],
            options={
                'verbose_name': 'Sync Log',
                'verbose_name_plural': 'Sync Logs',
                'ordering': ['-timestamp'],
            },
        ),
        
        # SiteNameRule Model
        migrations.CreateModel(
            name='SiteNameRule',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False)),
                ('name', models.CharField(help_text='Descriptive name for this rule', max_length=100, unique=True)),
                ('regex_pattern', models.CharField(help_text='Regular expression to match network names (e.g., "^(?P<region>NA|EMEA)-(?P<site>[A-Z]{3})$"). Use (?P<name>...) for named groups', max_length=500, verbose_name='Regex Pattern')),
                ('site_name_template', models.CharField(help_text='Template for site name. Use {name} for named groups, {0}/{1} for numbered groups, or {network_name} for full name', max_length=200, verbose_name='Site Name Template')),
                ('priority', models.IntegerField(default=100, help_text='Rule priority (lower values are evaluated first)')),
                ('enabled', models.BooleanField(default=True, help_text='Enable or disable this rule')),
                ('description', models.TextField(blank=True, help_text='Optional description of what this rule does')),
            ],
            options={
                'verbose_name': 'Site Name Rule',
                'verbose_name_plural': 'Site Name Rules',
                'ordering': ['priority', 'name'],
            },
        ),
        
        # PrefixFilterRule Model
        migrations.CreateModel(
            name='PrefixFilterRule',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False)),
                ('name', models.CharField(help_text='Descriptive name for this filter rule', max_length=100, unique=True)),
                ('filter_type', models.CharField(choices=[('exclude', 'Exclude Matching Prefixes'), ('include_only', 'Include Only Matching Prefixes')], default='exclude', help_text='Whether to exclude or include only matching prefixes', max_length=20, verbose_name='Filter Type')),
                ('prefix_pattern', models.CharField(blank=True, help_text='Prefix pattern to match (e.g., "192.168.0.0/16", "10.0.0.0/8"). Leave blank to match all prefixes.', max_length=200, verbose_name='Prefix Pattern')),
                ('prefix_length_filter', models.CharField(choices=[('exact', 'Exact Length'), ('greater', 'Greater Than'), ('less', 'Less Than'), ('range', 'Range')], default='exact', help_text='How to filter by prefix length', max_length=20, verbose_name='Prefix Length Filter')),
                ('min_prefix_length', models.IntegerField(blank=True, help_text='Minimum prefix length (1-32 for IPv4, 1-128 for IPv6). Used for "greater", "less", and "range" filters.', null=True, verbose_name='Minimum Prefix Length')),
                ('max_prefix_length', models.IntegerField(blank=True, help_text='Maximum prefix length (1-32 for IPv4, 1-128 for IPv6). Used for "range" filter only.', null=True, verbose_name='Maximum Prefix Length')),
                ('priority', models.IntegerField(default=100, help_text='Rule priority (lower values are evaluated first)')),
                ('enabled', models.BooleanField(default=True, help_text='Enable or disable this rule')),
                ('description', models.TextField(blank=True, help_text='Optional description of what this rule does')),
            ],
            options={
                'verbose_name': 'Prefix Filter Rule',
                'verbose_name_plural': 'Prefix Filter Rules',
                'ordering': ['priority', 'name'],
            },
        ),
        
        # SyncReview Model
        migrations.CreateModel(
            name='SyncReview',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False)),
                ('created', models.DateTimeField(auto_now_add=True)),
                ('reviewed', models.DateTimeField(blank=True, null=True)),
                ('reviewed_by', models.CharField(blank=True, max_length=100)),
                ('status', models.CharField(choices=[('pending', 'Pending Review'), ('approved', 'Approved'), ('partially_approved', 'Partially Approved'), ('rejected', 'Rejected'), ('applied', 'Applied')], default='pending', max_length=20)),
                ('items_total', models.IntegerField(default=0)),
                ('items_approved', models.IntegerField(default=0)),
                ('items_rejected', models.IntegerField(default=0)),
                ('sync_log', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name='review', to='netbox_meraki.synclog')),
            ],
            options={
                'verbose_name': 'Sync Review',
                'verbose_name_plural': 'Sync Reviews',
                'ordering': ['-created'],
            },
        ),
        
        # ReviewItem Model
        migrations.CreateModel(
            name='ReviewItem',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False)),
                ('item_type', models.CharField(choices=[('site', 'Site'), ('device', 'Device'), ('device_type', 'Device Type'), ('vlan', 'VLAN'), ('prefix', 'Prefix'), ('interface', 'Interface'), ('ip_address', 'IP Address'), ('ssid', 'SSID')], max_length=20)),
                ('action_type', models.CharField(choices=[('create', 'Create'), ('update', 'Update'), ('skip', 'Skip (Already Exists)')], max_length=20)),
                ('object_name', models.CharField(max_length=255)),
                ('object_identifier', models.CharField(help_text='Serial number, network ID, or other unique identifier', max_length=255)),
                ('current_data', models.JSONField(blank=True, help_text='Current data in NetBox (for updates)', null=True)),
                ('proposed_data', models.JSONField(help_text='Data to be synced from Meraki')),
                ('editable_data', models.JSONField(blank=True, help_text='User-edited data to apply (overrides proposed_data if set)', null=True)),
                ('preview_display', models.TextField(blank=True, help_text='Human-readable preview of what will be created/updated')),
                ('related_object_info', models.JSONField(blank=True, help_text='Information about related objects (site, device role, etc.)', null=True)),
                ('status', models.CharField(choices=[('pending', 'Pending'), ('approved', 'Approved'), ('rejected', 'Rejected'), ('applied', 'Applied'), ('failed', 'Failed')], default='pending', max_length=20)),
                ('error_message', models.TextField(blank=True)),
                ('notes', models.TextField(blank=True)),
                ('review', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='items', to='netbox_meraki.syncreview')),
            ],
            options={
                'verbose_name': 'Review Item',
                'verbose_name_plural': 'Review Items',
                'ordering': ['item_type', 'object_name'],
            },
        ),
    ]

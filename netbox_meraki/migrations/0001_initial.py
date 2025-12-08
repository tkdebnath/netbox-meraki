# Initial migration for NetBox Meraki plugin

from django.db import migrations, models
import django.db.models.deletion


def create_default_settings(apps, schema_editor):
    """Create default PluginSettings instance"""
    PluginSettings = apps.get_model('netbox_meraki', 'PluginSettings')
    if not PluginSettings.objects.exists():
        PluginSettings.objects.create(id=1)


class Migration(migrations.Migration):

    initial = True

    dependencies = [
    ]

    operations = [
        # Drop existing tables if they exist (for clean reinstall)
        migrations.RunSQL(
            sql="DROP TABLE IF EXISTS netbox_meraki_scheduledjobtracker CASCADE;",
            reverse_sql=migrations.RunSQL.noop,
        ),
        migrations.RunSQL(
            sql="DROP TABLE IF EXISTS netbox_meraki_reviewitem CASCADE;",
            reverse_sql=migrations.RunSQL.noop,
        ),
        migrations.RunSQL(
            sql="DROP TABLE IF EXISTS netbox_meraki_syncreview CASCADE;",
            reverse_sql=migrations.RunSQL.noop,
        ),
        migrations.RunSQL(
            sql="DROP TABLE IF EXISTS netbox_meraki_scheduledsynctask CASCADE;",
            reverse_sql=migrations.RunSQL.noop,
        ),
        migrations.RunSQL(
            sql="DROP TABLE IF EXISTS netbox_meraki_synclog CASCADE;",
            reverse_sql=migrations.RunSQL.noop,
        ),
        migrations.RunSQL(
            sql="DROP TABLE IF EXISTS netbox_meraki_prefixfilterrule CASCADE;",
            reverse_sql=migrations.RunSQL.noop,
        ),
        migrations.RunSQL(
            sql="DROP TABLE IF EXISTS netbox_meraki_sitenamerule CASCADE;",
            reverse_sql=migrations.RunSQL.noop,
        ),
        migrations.RunSQL(
            sql="DROP TABLE IF EXISTS netbox_meraki_pluginsettings CASCADE;",
            reverse_sql=migrations.RunSQL.noop,
        ),
        
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
                ('process_unmatched_sites', models.BooleanField(default=True, help_text='If enabled, sites that do not match any name rules will still be processed using their original network name. If disabled, only sites matching name rules will be synced.', verbose_name='Process Sites Not Matching Name Rules')),
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
        
        # SiteNameRule Model
        migrations.CreateModel(
            name='SiteNameRule',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False)),
                ('order', models.IntegerField(default=0, help_text='Processing order (lower numbers processed first)')),
                ('pattern', models.CharField(help_text='Regular expression pattern to match Meraki network names', max_length=255)),
                ('site_name_format', models.CharField(help_text='Format for site name (use {group1}, {group2}, etc. for regex groups)', max_length=255)),
                ('site_group', models.CharField(blank=True, help_text='Optional site group name', max_length=100)),
                ('enabled', models.BooleanField(default=True, help_text='Whether this rule is active')),
            ],
            options={
                'verbose_name': 'Site Name Rule',
                'verbose_name_plural': 'Site Name Rules',
                'ordering': ['order', 'id'],
            },
        ),
        
        # PrefixFilterRule Model
        migrations.CreateModel(
            name='PrefixFilterRule',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False)),
                ('order', models.IntegerField(default=0, help_text='Processing order (lower numbers processed first)')),
                ('pattern', models.CharField(help_text='Regular expression pattern to match prefix/network addresses', max_length=255)),
                ('action', models.CharField(choices=[('include', 'Include'), ('exclude', 'Exclude')], default='include', help_text='Whether to include or exclude matching prefixes', max_length=10)),
                ('enabled', models.BooleanField(default=True, help_text='Whether this rule is active')),
            ],
            options={
                'verbose_name': 'Prefix Filter Rule',
                'verbose_name_plural': 'Prefix Filter Rules',
                'ordering': ['order', 'id'],
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
            ],
            options={
                'verbose_name': 'Sync Log',
                'verbose_name_plural': 'Sync Logs',
                'ordering': ['-timestamp'],
            },
        ),
        
        # SyncReview Model
        migrations.CreateModel(
            name='SyncReview',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False)),
                ('created', models.DateTimeField(auto_now_add=True)),
                ('status', models.CharField(choices=[('pending', 'Pending Review'), ('in_progress', 'In Progress'), ('completed', 'Completed'), ('failed', 'Failed')], default='pending', max_length=20)),
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
        
        # ScheduledJobTracker Model
        migrations.CreateModel(
            name='ScheduledJobTracker',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False)),
                ('netbox_job_id', models.IntegerField(unique=True, verbose_name='NetBox Job ID', help_text='ID of the NetBox scheduled job')),
                ('job_name', models.CharField(max_length=200, verbose_name='Job Name', help_text='User-provided name for the job')),
                ('created', models.DateTimeField(auto_now_add=True, verbose_name='Created')),
            ],
            options={
                'verbose_name': 'Scheduled Job Tracker',
                'verbose_name_plural': 'Scheduled Job Trackers',
                'ordering': ['-created'],
            },
        ),
        
        # Create default PluginSettings instance
        migrations.RunPython(create_default_settings, migrations.RunPython.noop),
    ]

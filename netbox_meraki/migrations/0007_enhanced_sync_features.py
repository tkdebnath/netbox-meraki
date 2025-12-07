# Generated migration for enhanced sync features

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('netbox_meraki', '0006_add_name_transforms'),
    ]

    operations = [
        # Add SSID tracking
        migrations.AddField(
            model_name='synclog',
            name='ssids_synced',
            field=models.IntegerField(default=0),
        ),
        
        # Add progress tracking fields
        migrations.AddField(
            model_name='synclog',
            name='progress_logs',
            field=models.JSONField(default=list, blank=True, help_text='Live progress log entries'),
        ),
        migrations.AddField(
            model_name='synclog',
            name='current_operation',
            field=models.CharField(max_length=255, blank=True, help_text='Current sync operation'),
        ),
        migrations.AddField(
            model_name='synclog',
            name='progress_percent',
            field=models.IntegerField(default=0, help_text='Overall progress percentage'),
        ),
        
        # Add cancel capability fields
        migrations.AddField(
            model_name='synclog',
            name='cancel_requested',
            field=models.BooleanField(default=False, help_text='Flag to cancel ongoing sync'),
        ),
        migrations.AddField(
            model_name='synclog',
            name='cancelled_at',
            field=models.DateTimeField(null=True, blank=True, help_text='When sync was cancelled'),
        ),
        
        # Add device_type and ssid to ReviewItem item_types
        migrations.AlterField(
            model_name='reviewitem',
            name='item_type',
            field=models.CharField(
                max_length=20,
                choices=[
                    ('site', 'Site'),
                    ('device', 'Device'),
                    ('device_type', 'Device Type'),
                    ('vlan', 'VLAN'),
                    ('prefix', 'Prefix'),
                    ('interface', 'Interface'),
                    ('ip_address', 'IP Address'),
                    ('ssid', 'SSID'),
                ]
            ),
        ),
        
        # Add preview display and related object info for better UI
        migrations.AddField(
            model_name='reviewitem',
            name='preview_display',
            field=models.TextField(
                blank=True,
                help_text='Human-readable preview of what will be created/updated'
            ),
        ),
        migrations.AddField(
            model_name='reviewitem',
            name='related_object_info',
            field=models.JSONField(
                null=True,
                blank=True,
                help_text='Information about related objects (site, device role, etc.)'
            ),
        ),
    ]

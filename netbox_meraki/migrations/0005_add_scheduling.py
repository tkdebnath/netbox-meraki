# Generated migration for scheduling settings

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('netbox_meraki', '0004_add_cleanup_stats'),
    ]

    operations = [
        migrations.AddField(
            model_name='pluginsettings',
            name='enable_scheduled_sync',
            field=models.BooleanField(default=False, help_text='Enable automatic scheduled synchronization', verbose_name='Enable Scheduled Sync'),
        ),
        migrations.AddField(
            model_name='pluginsettings',
            name='sync_interval_minutes',
            field=models.IntegerField(default=60, help_text='Interval between automatic syncs in minutes (minimum 5)', verbose_name='Sync Interval (minutes)'),
        ),
        migrations.AddField(
            model_name='pluginsettings',
            name='scheduled_sync_mode',
            field=models.CharField(choices=[('auto', 'Auto Sync'), ('review', 'Sync with Review'), ('dry_run', 'Dry Run')], default='auto', help_text='Mode to use for scheduled synchronization', max_length=20, verbose_name='Scheduled Sync Mode'),
        ),
        migrations.AddField(
            model_name='pluginsettings',
            name='last_scheduled_sync',
            field=models.DateTimeField(blank=True, help_text='Timestamp of last scheduled sync execution', null=True, verbose_name='Last Scheduled Sync'),
        ),
        migrations.AddField(
            model_name='pluginsettings',
            name='next_scheduled_sync',
            field=models.DateTimeField(blank=True, help_text='Timestamp of next scheduled sync', null=True, verbose_name='Next Scheduled Sync'),
        ),
    ]

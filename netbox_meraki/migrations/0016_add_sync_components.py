# Generated migration for adding sync_interfaces, sync_ip_addresses, and sync_ssids fields

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('netbox_meraki', '0015_add_execution_mode'),
    ]

    operations = [
        migrations.AddField(
            model_name='scheduledsynctask',
            name='sync_interfaces',
            field=models.BooleanField(default=True, help_text='Sync device interfaces'),
        ),
        migrations.AddField(
            model_name='scheduledsynctask',
            name='sync_ip_addresses',
            field=models.BooleanField(default=True, help_text='Sync IP addresses'),
        ),
        migrations.AddField(
            model_name='scheduledsynctask',
            name='sync_ssids',
            field=models.BooleanField(default=True, help_text='Sync wireless SSIDs'),
        ),
    ]

# Generated migration to allow NULL in selected_networks field

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('netbox_meraki', '0013_add_scheduled_sync_tasks'),
    ]

    operations = [
        migrations.AlterField(
            model_name='scheduledsynctask',
            name='selected_networks',
            field=models.JSONField(blank=True, null=True, default=list, help_text='List of network IDs for selective/single network sync'),
        ),
    ]

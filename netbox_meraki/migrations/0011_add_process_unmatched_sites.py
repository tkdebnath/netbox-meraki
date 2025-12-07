# Generated migration for adding process_unmatched_sites field

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('netbox_meraki', '0010_add_api_performance_settings'),
    ]

    operations = [
        migrations.AddField(
            model_name='pluginsettings',
            name='process_unmatched_sites',
            field=models.BooleanField(
                default=True,
                help_text='If enabled, sites that do not match any name rules will still be processed using their original network name. If disabled, only sites matching name rules will be synced.',
                verbose_name='Process Sites Not Matching Name Rules'
            ),
        ),
    ]

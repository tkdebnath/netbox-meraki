# Migration to add tag configuration fields

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('netbox_meraki', '0008_add_editable_data'),
    ]

    operations = [
        migrations.AddField(
            model_name='pluginsettings',
            name='site_tags',
            field=models.CharField(
                max_length=500,
                blank=True,
                default='Meraki',
                help_text='Comma-separated list of tags to apply to sites (e.g., "Meraki,Production")'
            ),
        ),
        migrations.AddField(
            model_name='pluginsettings',
            name='device_tags',
            field=models.CharField(
                max_length=500,
                blank=True,
                default='Meraki',
                help_text='Comma-separated list of tags to apply to devices (e.g., "Meraki,Network-Device")'
            ),
        ),
        migrations.AddField(
            model_name='pluginsettings',
            name='vlan_tags',
            field=models.CharField(
                max_length=500,
                blank=True,
                default='Meraki',
                help_text='Comma-separated list of tags to apply to VLANs (e.g., "Meraki,VLAN")'
            ),
        ),
        migrations.AddField(
            model_name='pluginsettings',
            name='prefix_tags',
            field=models.CharField(
                max_length=500,
                blank=True,
                default='Meraki',
                help_text='Comma-separated list of tags to apply to prefixes/subnets (e.g., "Meraki,Subnet")'
            ),
        ),
    ]

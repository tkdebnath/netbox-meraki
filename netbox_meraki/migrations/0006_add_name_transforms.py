# Generated migration for name transformation settings

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('netbox_meraki', '0005_add_scheduling'),
    ]

    operations = [
        migrations.AddField(
            model_name='pluginsettings',
            name='device_name_transform',
            field=models.CharField(
                choices=[('keep', 'Keep Original'), ('upper', 'UPPERCASE'), ('lower', 'lowercase'), ('title', 'Title Case')],
                default='keep',
                help_text='How to transform device names from Meraki',
                max_length=10,
                verbose_name='Device Name Transform'
            ),
        ),
        migrations.AddField(
            model_name='pluginsettings',
            name='site_name_transform',
            field=models.CharField(
                choices=[('keep', 'Keep Original'), ('upper', 'UPPERCASE'), ('lower', 'lowercase'), ('title', 'Title Case')],
                default='keep',
                help_text='How to transform site/network names from Meraki',
                max_length=10,
                verbose_name='Site Name Transform'
            ),
        ),
        migrations.AddField(
            model_name='pluginsettings',
            name='vlan_name_transform',
            field=models.CharField(
                choices=[('keep', 'Keep Original'), ('upper', 'UPPERCASE'), ('lower', 'lowercase'), ('title', 'Title Case')],
                default='keep',
                help_text='How to transform VLAN names from Meraki',
                max_length=10,
                verbose_name='VLAN Name Transform'
            ),
        ),
        migrations.AddField(
            model_name='pluginsettings',
            name='ssid_name_transform',
            field=models.CharField(
                choices=[('keep', 'Keep Original'), ('upper', 'UPPERCASE'), ('lower', 'lowercase'), ('title', 'Title Case')],
                default='keep',
                help_text='How to transform SSID names from Meraki',
                max_length=10,
                verbose_name='SSID Name Transform'
            ),
        ),
    ]

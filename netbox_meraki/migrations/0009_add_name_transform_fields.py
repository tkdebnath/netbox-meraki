# Generated migration to add name transformation fields

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('netbox_meraki', '0008_add_editable_data'),
    ]

    operations = [
        migrations.AddField(
            model_name='pluginsettings',
            name='device_name_transform',
            field=models.CharField(
                choices=[
                    ('keep', 'Keep Original'),
                    ('upper', 'UPPERCASE'),
                    ('lower', 'lowercase'),
                    ('title', 'Title Case'),
                ],
                default='keep',
                help_text='How to transform device names from Meraki',
                max_length=20,
                verbose_name='Device Name Transform'
            ),
        ),
        migrations.AddField(
            model_name='pluginsettings',
            name='site_name_transform',
            field=models.CharField(
                choices=[
                    ('keep', 'Keep Original'),
                    ('upper', 'UPPERCASE'),
                    ('lower', 'lowercase'),
                    ('title', 'Title Case'),
                ],
                default='keep',
                help_text='How to transform site names from Meraki',
                max_length=20,
                verbose_name='Site Name Transform'
            ),
        ),
        migrations.AddField(
            model_name='pluginsettings',
            name='vlan_name_transform',
            field=models.CharField(
                choices=[
                    ('keep', 'Keep Original'),
                    ('upper', 'UPPERCASE'),
                    ('lower', 'lowercase'),
                    ('title', 'Title Case'),
                ],
                default='keep',
                help_text='How to transform VLAN names from Meraki',
                max_length=20,
                verbose_name='VLAN Name Transform'
            ),
        ),
        migrations.AddField(
            model_name='pluginsettings',
            name='ssid_name_transform',
            field=models.CharField(
                choices=[
                    ('keep', 'Keep Original'),
                    ('upper', 'UPPERCASE'),
                    ('lower', 'lowercase'),
                    ('title', 'Title Case'),
                ],
                default='keep',
                help_text='How to transform SSID names from Meraki',
                max_length=20,
                verbose_name='SSID Name Transform'
            ),
        ),
    ]

# Generated migration for NetBox Meraki plugin

from django.db import migrations, models
import django.core.validators


class Migration(migrations.Migration):

    dependencies = [
        ('netbox_meraki', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='PluginSettings',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False)),
                ('mx_device_role', models.CharField(default='Security Appliance', help_text='Device role for MX (Security Appliance) devices', max_length=100, verbose_name='MX Device Role')),
                ('ms_device_role', models.CharField(default='Switch', help_text='Device role for MS (Switch) devices', max_length=100, verbose_name='MS Device Role')),
                ('mr_device_role', models.CharField(default='Wireless AP', help_text='Device role for MR (Wireless AP) devices', max_length=100, verbose_name='MR Device Role')),
                ('mg_device_role', models.CharField(default='Cellular Gateway', help_text='Device role for MG (Cellular Gateway) devices', max_length=100, verbose_name='MG Device Role')),
                ('mv_device_role', models.CharField(default='Camera', help_text='Device role for MV (Camera) devices', max_length=100, verbose_name='MV Device Role')),
                ('mt_device_role', models.CharField(default='Sensor', help_text='Device role for MT (Sensor) devices', max_length=100, verbose_name='MT Device Role')),
                ('default_device_role', models.CharField(default='Network Device', help_text='Default device role for unknown product types', max_length=100, verbose_name='Default Device Role')),
                ('auto_create_device_roles', models.BooleanField(default=True, help_text='Automatically create device roles if they do not exist')),
            ],
            options={
                'verbose_name': 'Plugin Settings',
                'verbose_name_plural': 'Plugin Settings',
            },
        ),
        migrations.CreateModel(
            name='SiteNameRule',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False)),
                ('name', models.CharField(help_text='Descriptive name for this rule', max_length=100, unique=True)),
                ('regex_pattern', models.CharField(help_text='Regular expression pattern to match network names (e.g., "asia-south-.*-oil")', max_length=500, verbose_name='Regex Pattern')),
                ('site_name_template', models.CharField(help_text='Template for site name. Use {0}, {1}, etc. for regex groups, or {network_name} for full name', max_length=200, verbose_name='Site Name Template')),
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
    ]

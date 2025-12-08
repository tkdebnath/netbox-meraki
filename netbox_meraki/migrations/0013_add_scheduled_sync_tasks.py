# Migration for ScheduledSyncTask model

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('netbox_meraki', '0012_add_prefix_filter_rules'),
    ]

    operations = [
        migrations.CreateModel(
            name='ScheduledSyncTask',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False)),
                ('name', models.CharField(help_text='Descriptive name for this scheduled task', max_length=200)),
                ('sync_mode', models.CharField(
                    choices=[('full', 'Full Sync'), ('selective', 'Selective Networks'), ('single_network', 'Single Network')],
                    default='full',
                    help_text='Type of sync to perform',
                    max_length=20
                )),
                ('selected_networks', models.JSONField(blank=True, default=list, help_text='List of network IDs for selective/single network sync')),
                ('sync_organizations', models.BooleanField(default=True, help_text='Sync organizations')),
                ('sync_sites', models.BooleanField(default=True, help_text='Sync sites/networks')),
                ('sync_devices', models.BooleanField(default=True, help_text='Sync devices')),
                ('sync_vlans', models.BooleanField(default=True, help_text='Sync VLANs')),
                ('sync_prefixes', models.BooleanField(default=True, help_text='Sync prefixes/subnets')),
                ('cleanup_orphaned', models.BooleanField(default=False, help_text='Remove objects that no longer exist in Meraki')),
                ('frequency', models.CharField(
                    choices=[('once', 'One Time'), ('hourly', 'Hourly'), ('daily', 'Daily'), ('weekly', 'Weekly')],
                    default='daily',
                    help_text='How often to run this task',
                    max_length=20
                )),
                ('scheduled_datetime', models.DateTimeField(help_text='Date and time for first/next execution')),
                ('last_run', models.DateTimeField(blank=True, help_text='Last execution time', null=True)),
                ('next_run', models.DateTimeField(blank=True, help_text='Next scheduled execution time', null=True)),
                ('status', models.CharField(
                    choices=[('pending', 'Pending'), ('running', 'Running'), ('completed', 'Completed'), ('failed', 'Failed'), ('cancelled', 'Cancelled')],
                    default='pending',
                    help_text='Current status of the task',
                    max_length=20
                )),
                ('enabled', models.BooleanField(default=True, help_text='Whether this task is active')),
                ('total_runs', models.IntegerField(default=0, help_text='Total number of times this task has run')),
                ('successful_runs', models.IntegerField(default=0, help_text='Number of successful executions')),
                ('failed_runs', models.IntegerField(default=0, help_text='Number of failed executions')),
                ('last_error', models.TextField(blank=True, help_text='Error message from last failed run')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('created_by', models.CharField(blank=True, max_length=100)),
            ],
            options={
                'verbose_name': 'Scheduled Sync Task',
                'verbose_name_plural': 'Scheduled Sync Tasks',
                'ordering': ['next_run', 'scheduled_datetime'],
            },
        ),
    ]

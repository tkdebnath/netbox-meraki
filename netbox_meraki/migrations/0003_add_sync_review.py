# Generated migration file for sync review functionality

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('netbox_meraki', '0002_add_settings_and_site_rules'),
    ]

    operations = [
        # Add sync_mode field to SyncLog
        migrations.AddField(
            model_name='synclog',
            name='sync_mode',
            field=models.CharField(
                max_length=20,
                choices=[('auto', 'Auto'), ('review', 'Review'), ('dry_run', 'Dry Run')],
                default='auto',
                help_text='Sync mode used for this sync'
            ),
        ),
        
        # Update status choices for SyncLog
        migrations.AlterField(
            model_name='synclog',
            name='status',
            field=models.CharField(
                max_length=20,
                choices=[
                    ('success', 'Success'),
                    ('partial', 'Partial Success'),
                    ('failed', 'Failed'),
                    ('running', 'Running'),
                    ('dry_run', 'Dry Run'),
                    ('pending_review', 'Pending Review'),
                ],
                default='running'
            ),
        ),
        
        # Add sync_mode to PluginSettings
        migrations.AddField(
            model_name='pluginsettings',
            name='sync_mode',
            field=models.CharField(
                max_length=20,
                choices=[('auto', 'Auto'), ('review', 'Review'), ('dry_run', 'Dry Run')],
                default='review',
                help_text='Default sync mode: auto applies changes immediately, review stages changes for approval, dry_run only previews'
            ),
        ),
        
        # Create SyncReview model
        migrations.CreateModel(
            name='SyncReview',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created', models.DateTimeField(auto_now_add=True)),
                ('status', models.CharField(
                    max_length=20,
                    choices=[
                        ('pending', 'Pending'),
                        ('approved', 'Approved'),
                        ('rejected', 'Rejected'),
                        ('partially_approved', 'Partially Approved'),
                        ('applied', 'Applied'),
                    ],
                    default='pending'
                )),
                ('items_total', models.IntegerField(default=0)),
                ('items_approved', models.IntegerField(default=0)),
                ('items_rejected', models.IntegerField(default=0)),
                ('sync_log', models.OneToOneField(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='review',
                    to='netbox_meraki.synclog'
                )),
            ],
            options={
                'ordering': ['-created'],
                'verbose_name': 'Sync Review',
                'verbose_name_plural': 'Sync Reviews',
            },
        ),
        
        # Create ReviewItem model
        migrations.CreateModel(
            name='ReviewItem',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('item_type', models.CharField(
                    max_length=20,
                    choices=[
                        ('site', 'Site'),
                        ('device', 'Device'),
                        ('vlan', 'VLAN'),
                        ('prefix', 'Prefix'),
                    ]
                )),
                ('action_type', models.CharField(
                    max_length=20,
                    choices=[
                        ('create', 'Create'),
                        ('update', 'Update'),
                        ('delete', 'Delete'),
                    ]
                )),
                ('object_name', models.CharField(max_length=255)),
                ('proposed_data', models.JSONField()),
                ('current_data', models.JSONField(null=True, blank=True)),
                ('status', models.CharField(
                    max_length=20,
                    choices=[
                        ('pending', 'Pending'),
                        ('approved', 'Approved'),
                        ('rejected', 'Rejected'),
                        ('applied', 'Applied'),
                    ],
                    default='pending'
                )),
                ('notes', models.TextField(blank=True)),
                ('review', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='items',
                    to='netbox_meraki.syncreview'
                )),
            ],
            options={
                'ordering': ['item_type', 'object_name'],
                'verbose_name': 'Review Item',
                'verbose_name_plural': 'Review Items',
            },
        ),
    ]

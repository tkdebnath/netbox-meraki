# Generated migration for adding execution_mode field to ScheduledSyncTask

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('netbox_meraki', '0014_alter_scheduledsynctask_selected_networks'),
    ]

    operations = [
        migrations.AddField(
            model_name='scheduledsynctask',
            name='execution_mode',
            field=models.CharField(
                choices=[
                    ('auto', 'Auto Sync'),
                    ('review', 'Sync with Review'),
                    ('dry_run', 'Dry Run')
                ],
                default='review',
                help_text='How to execute the sync: auto applies immediately, review requires approval, dry_run only previews',
                max_length=20
            ),
        ),
    ]

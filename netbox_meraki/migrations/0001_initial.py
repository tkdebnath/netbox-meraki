# Generated initial migration for NetBox Meraki plugin

from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='SyncLog',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False)),
                ('timestamp', models.DateTimeField(auto_now_add=True)),
                ('status', models.CharField(choices=[('success', 'Success'), ('partial', 'Partial Success'), ('failed', 'Failed'), ('running', 'Running')], max_length=20)),
                ('message', models.TextField(blank=True)),
                ('organizations_synced', models.IntegerField(default=0)),
                ('networks_synced', models.IntegerField(default=0)),
                ('devices_synced', models.IntegerField(default=0)),
                ('vlans_synced', models.IntegerField(default=0)),
                ('prefixes_synced', models.IntegerField(default=0)),
                ('errors', models.JSONField(blank=True, default=list)),
                ('duration_seconds', models.FloatField(blank=True, null=True)),
            ],
            options={
                'verbose_name': 'Sync Log',
                'verbose_name_plural': 'Sync Logs',
                'ordering': ['-timestamp'],
            },
        ),
    ]

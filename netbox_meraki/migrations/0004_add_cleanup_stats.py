# Generated migration for cleanup statistics

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('netbox_meraki', '0003_add_sync_review'),
    ]

    operations = [
        migrations.AddField(
            model_name='synclog',
            name='deleted_sites',
            field=models.IntegerField(default=0),
        ),
        migrations.AddField(
            model_name='synclog',
            name='deleted_devices',
            field=models.IntegerField(default=0),
        ),
        migrations.AddField(
            model_name='synclog',
            name='deleted_vlans',
            field=models.IntegerField(default=0),
        ),
        migrations.AddField(
            model_name='synclog',
            name='deleted_prefixes',
            field=models.IntegerField(default=0),
        ),
        migrations.AddField(
            model_name='synclog',
            name='updated_prefixes',
            field=models.IntegerField(default=0),
        ),
    ]

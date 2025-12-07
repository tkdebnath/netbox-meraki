# Generated migration to add editable_data field for review item editing

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('netbox_meraki', '0007_enhanced_sync_features'),
    ]

    operations = [
        migrations.AddField(
            model_name='reviewitem',
            name='editable_data',
            field=models.JSONField(
                null=True,
                blank=True,
                help_text='User-edited data to apply (overrides proposed_data if set)'
            ),
        ),
    ]

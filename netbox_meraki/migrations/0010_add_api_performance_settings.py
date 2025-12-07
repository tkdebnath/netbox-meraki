# Generated migration to add API performance settings

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('netbox_meraki', '0009_add_tag_configuration'),
    ]

    operations = [
        migrations.AddField(
            model_name='pluginsettings',
            name='enable_api_throttling',
            field=models.BooleanField(
                default=True,
                verbose_name='Enable API Throttling',
                help_text='Enable rate limiting to avoid overwhelming Meraki Dashboard API (recommended)'
            ),
        ),
        migrations.AddField(
            model_name='pluginsettings',
            name='api_requests_per_second',
            field=models.IntegerField(
                default=5,
                verbose_name='API Requests Per Second',
                help_text='Maximum API requests per second (Meraki limit is 10/sec, recommended: 5)'
            ),
        ),
        migrations.AddField(
            model_name='pluginsettings',
            name='enable_multithreading',
            field=models.BooleanField(
                default=False,
                verbose_name='Enable Multithreading',
                help_text='Use multiple threads to fetch data from Meraki API in parallel (faster but may hit rate limits)'
            ),
        ),
        migrations.AddField(
            model_name='pluginsettings',
            name='max_worker_threads',
            field=models.IntegerField(
                default=3,
                verbose_name='Max Worker Threads',
                help_text='Maximum number of concurrent threads for API requests (recommended: 2-5)'
            ),
        ),
    ]

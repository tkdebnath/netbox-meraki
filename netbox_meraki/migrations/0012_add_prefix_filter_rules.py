# Migration for adding PrefixFilterRule model

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('netbox_meraki', '0011_add_process_unmatched_sites'),
    ]

    operations = [
        migrations.CreateModel(
            name='PrefixFilterRule',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False)),
                ('name', models.CharField(help_text='Descriptive name for this filter rule', max_length=100, unique=True)),
                ('filter_type', models.CharField(
                    choices=[('exclude', 'Exclude Matching Prefixes'), ('include_only', 'Include Only Matching Prefixes')],
                    default='exclude',
                    help_text='Whether to exclude or include only matching prefixes',
                    max_length=20,
                    verbose_name='Filter Type'
                )),
                ('prefix_pattern', models.CharField(
                    blank=True,
                    help_text='Prefix pattern to match (e.g., "192.168.0.0/16", "10.0.0.0/8"). Leave blank to match all prefixes.',
                    max_length=200,
                    verbose_name='Prefix Pattern'
                )),
                ('prefix_length_filter', models.CharField(
                    choices=[('exact', 'Exact Length'), ('greater', 'Greater Than'), ('less', 'Less Than'), ('range', 'Range')],
                    default='exact',
                    help_text='How to filter by prefix length',
                    max_length=20,
                    verbose_name='Prefix Length Filter'
                )),
                ('min_prefix_length', models.IntegerField(
                    blank=True,
                    help_text='Minimum prefix length (1-32 for IPv4, 1-128 for IPv6). Used for "greater", "less", and "range" filters.',
                    null=True,
                    verbose_name='Minimum Prefix Length'
                )),
                ('max_prefix_length', models.IntegerField(
                    blank=True,
                    help_text='Maximum prefix length (1-32 for IPv4, 1-128 for IPv6). Used for "range" filter only.',
                    null=True,
                    verbose_name='Maximum Prefix Length'
                )),
                ('priority', models.IntegerField(default=100, help_text='Rule priority (lower values are evaluated first)')),
                ('enabled', models.BooleanField(default=True, help_text='Enable or disable this rule')),
                ('description', models.TextField(blank=True, help_text='Optional description of what this rule does')),
            ],
            options={
                'verbose_name': 'Prefix Filter Rule',
                'verbose_name_plural': 'Prefix Filter Rules',
                'ordering': ['priority', 'name'],
            },
        ),
    ]

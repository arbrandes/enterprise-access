# Generated by Django 5.0.6 on 2024-06-12 12:00

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('subsidy_access_policy', '0027_historicalsubsidyaccesspolicy_retired_at_and_more'),
    ]

    operations = [
        migrations.AlterField(
            model_name='historicalsubsidyaccesspolicy',
            name='retired_at',
            field=models.DateTimeField(blank=True, help_text='The date and time when this policy is considered retired.', null=True),
        ),
        migrations.AlterField(
            model_name='subsidyaccesspolicy',
            name='retired_at',
            field=models.DateTimeField(blank=True, help_text='The date and time when this policy is considered retired.', null=True),
        ),
    ]

# Generated by Django 3.2.16 on 2023-02-21 13:28

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('subsidy_access_policy', '0003_cappedenrollmentlearnercreditaccesspolicy_historicalsubsidyaccesspolicy_perlearnerenrollmentcreditac'),
    ]

    operations = [
        migrations.AlterField(
            model_name='historicalsubsidyaccesspolicy',
            name='policy_type',
            field=models.CharField(editable=False, max_length=64),
        ),
        migrations.AlterField(
            model_name='subsidyaccesspolicy',
            name='policy_type',
            field=models.CharField(editable=False, max_length=64),
        ),
    ]

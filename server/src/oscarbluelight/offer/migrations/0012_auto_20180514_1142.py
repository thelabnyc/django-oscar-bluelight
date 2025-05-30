# Generated by Django 1.10.7 on 2018-05-14 11:42

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("offer", "0011_auto_20170710_1442"),
    ]

    operations = [
        migrations.AddField(
            model_name="range",
            name="cache_version",
            field=models.PositiveIntegerField(
                default=1, editable=False, verbose_name="Cache Version"
            ),
        ),
        migrations.AlterField(
            model_name="conditionaloffer",
            name="end_datetime",
            field=models.DateTimeField(
                blank=True,
                help_text="Offers are active until the end date. Leave this empty if the offer has no expiry date.",
                null=True,
                verbose_name="End date",
            ),
        ),
        migrations.AlterField(
            model_name="conditionaloffer",
            name="start_datetime",
            field=models.DateTimeField(
                blank=True,
                help_text="Offers are active from the start date. Leave this empty if the offer has no start date.",
                null=True,
                verbose_name="Start date",
            ),
        ),
    ]

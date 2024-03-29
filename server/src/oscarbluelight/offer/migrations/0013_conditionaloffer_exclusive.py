# Generated by Django 2.0.6 on 2018-06-01 13:48

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("offer", "0012_auto_20180514_1142"),
    ]

    operations = [
        migrations.AddField(
            model_name="conditionaloffer",
            name="exclusive",
            field=models.BooleanField(
                default=True,
                help_text="Exclusive offers cannot be combined on the same items",
                verbose_name="Exclusive offer",
            ),
        ),
    ]

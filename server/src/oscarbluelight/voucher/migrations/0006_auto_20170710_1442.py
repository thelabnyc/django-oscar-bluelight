# Generated by Django 1.10.7 on 2017-07-10 14:42

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("voucher", "0005_auto_20170613_1245"),
    ]

    operations = [
        migrations.AlterModelOptions(
            name="voucher",
            options={
                "base_manager_name": "objects",
                "ordering": (
                    "-offers__offer_group__priority",
                    "-offers__priority",
                    "pk",
                ),
            },
        ),
        migrations.AlterField(
            model_name="voucher",
            name="date_created",
            field=models.DateTimeField(auto_now_add=True),
        ),
        migrations.AlterField(
            model_name="voucherapplication",
            name="date_created",
            field=models.DateTimeField(auto_now_add=True),
        ),
    ]

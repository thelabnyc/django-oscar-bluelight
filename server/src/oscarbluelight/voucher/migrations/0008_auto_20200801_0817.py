# Generated by Django 3.0.8 on 2020-08-01 07:17

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("voucher", "0008_auto_20190926_1547"),
    ]

    operations = [
        migrations.AlterModelOptions(
            name="voucher",
            options={
                "get_latest_by": "date_created",
                "ordering": ["-date_created"],
                "verbose_name": "Voucher",
                "verbose_name_plural": "Vouchers",
            },
        ),
        migrations.AlterModelOptions(
            name="voucherapplication",
            options={
                "ordering": ["-date_created"],
                "verbose_name": "Voucher Application",
                "verbose_name_plural": "Voucher Applications",
            },
        ),
        migrations.AlterModelOptions(
            name="voucherset",
            options={
                "get_latest_by": "date_created",
                "ordering": ["-date_created"],
                "verbose_name": "VoucherSet",
                "verbose_name_plural": "VoucherSets",
            },
        ),
        migrations.AlterField(
            model_name="voucher",
            name="date_created",
            field=models.DateTimeField(auto_now_add=True, db_index=True),
        ),
        migrations.AlterField(
            model_name="voucherapplication",
            name="date_created",
            field=models.DateTimeField(auto_now_add=True, db_index=True),
        ),
        migrations.AlterField(
            model_name="voucherset",
            name="date_created",
            field=models.DateTimeField(auto_now_add=True, db_index=True),
        ),
    ]
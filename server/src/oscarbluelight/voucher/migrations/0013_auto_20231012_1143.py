# Generated by Django 3.2.22 on 2023-10-12 11:43

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("voucher", "0012_voucher_status"),
    ]

    operations = [
        migrations.AlterField(
            model_name="voucher",
            name="id",
            field=models.BigAutoField(
                auto_created=True, primary_key=True, serialize=False, verbose_name="ID"
            ),
        ),
        migrations.AlterField(
            model_name="voucherapplication",
            name="id",
            field=models.BigAutoField(
                auto_created=True, primary_key=True, serialize=False, verbose_name="ID"
            ),
        ),
        migrations.AlterField(
            model_name="voucherset",
            name="id",
            field=models.BigAutoField(
                auto_created=True, primary_key=True, serialize=False, verbose_name="ID"
            ),
        ),
    ]

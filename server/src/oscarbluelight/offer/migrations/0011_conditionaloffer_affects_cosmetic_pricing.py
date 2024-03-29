# Generated by Django 3.1.6 on 2021-02-25 11:50

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("offer", "0010_conditionaloffer_combinations"),
    ]

    operations = [
        migrations.AddField(
            model_name="conditionaloffer",
            name="affects_cosmetic_pricing",
            field=models.BooleanField(
                default=True,
                help_text="Controls whether or not this offer will affect advertised product prices. Turn off for offers which should only apply once the product is in a customer's basket.",
                verbose_name="Affects Cosmetic Pricing?",
            ),
        ),
    ]

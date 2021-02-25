# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("offer", "0001_initial"),
    ]

    operations = [
        migrations.CreateModel(
            name="CompoundCondition",
            fields=[
                (
                    "condition_ptr",
                    models.OneToOneField(
                        parent_link=True,
                        to="offer.Condition",
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        on_delete=models.CASCADE,
                    ),
                ),
                (
                    "conjunction",
                    models.CharField(
                        verbose_name="Subcondition conjunction type",
                        choices=[("AND", "Logical AND"), ("OR", "Logical OR")],
                        default="AND",
                        max_length=10,
                    ),
                ),  # NOQA
                (
                    "subconditions",
                    models.ManyToManyField(
                        related_name="parent_conditions", to="offer.Condition"
                    ),
                ),
            ],
            options={
                "verbose_name": "Compound condition",
                "verbose_name_plural": "Compound conditions",
            },
            bases=("offer.condition",),
        ),
    ]

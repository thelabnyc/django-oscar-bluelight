# -*- coding: utf-8 -*-
# Generated by Django 1.10.7 on 2017-07-10 14:42
from __future__ import unicode_literals

from django.db import migrations, models
import django.db.models.deletion
import oscar.models.fields.autoslugfield


class Migration(migrations.Migration):

    dependencies = [
        ('offer', '0010_auto_20170613_1245'),
    ]

    operations = [
        migrations.AddField(
            model_name='offergroup',
            name='is_system_group',
            field=models.BooleanField(default=False, editable=False),
        ),
        migrations.AddField(
            model_name='offergroup',
            name='slug',
            field=oscar.models.fields.autoslugfield.AutoSlugField(blank=True, default=None, editable=False, null=True, populate_from='name', unique=True),
        ),
        migrations.AlterField(
            model_name='conditionaloffer',
            name='benefit',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='offers', to='offer.Benefit', verbose_name='Benefit'),
        ),
        migrations.AlterField(
            model_name='conditionaloffer',
            name='condition',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='offers', to='offer.Condition', verbose_name='Condition'),
        ),
        migrations.CreateModel(
            name='BluelightTaxInclusiveValueCondition',
            fields=[
            ],
            options={
                'verbose_name': 'Tax-Inclusive Value Condition',
                'verbose_name_plural': 'Tax-Inclusive Value Conditions',
                'proxy': True,
            },
            bases=('offer.bluelightvaluecondition',),
        ),
    ]
# -*- coding: utf-8 -*-
# Generated by Django 1.9.6 on 2016-07-19 12:38
from django.db import migrations
from oscar.models import fields


def benefit_to_proxy_classes(apps, schema_editor):
    Benefit = apps.get_model("offer", "Benefit")
    mapping = {
        'Percentage': 'oscar.apps.offer.benefits.PercentageDiscountBenefit',
        'Absolute': 'oscar.apps.offer.benefits.AbsoluteDiscountBenefit',
        'Multibuy': 'oscar.apps.offer.benefits.MultibuyDiscountBenefit',
        'Fixed price': 'oscar.apps.offer.benefits.FixedPriceBenefit',
        'Shipping absolute': 'oscar.apps.offer.benefits.ShippingAbsoluteDiscountBenefit',
        'Shipping fixed price': 'oscar.apps.offer.benefits.ShippingFixedPriceBenefit',
        'Shipping percentage': 'oscar.apps.offer.benefits.ShippingPercentageDiscountBenefit',
    }
    for benefit in Benefit.objects.all():
        if benefit.type in mapping:
            benefit.proxy_class = mapping[benefit.type]
            benefit.type = ''
            benefit.save()


def benefit_from_proxy_classes(apps, schema_editor):
    Benefit = apps.get_model("offer", "Benefit")
    mapping = {
        'oscar.apps.offer.benefits.PercentageDiscountBenefit': 'Percentage',
        'oscar.apps.offer.benefits.AbsoluteDiscountBenefit': 'Absolute',
        'oscar.apps.offer.benefits.MultibuyDiscountBenefit': 'Multibuy',
        'oscar.apps.offer.benefits.FixedPriceBenefit': 'Fixed price',
        'oscar.apps.offer.benefits.ShippingAbsoluteDiscountBenefit': 'Shipping absolute',
        'oscar.apps.offer.benefits.ShippingFixedPriceBenefit': 'Shipping fixed price',
        'oscar.apps.offer.benefits.ShippingPercentageDiscountBenefit': 'Shipping percentage',
    }
    for benefit in Benefit.objects.all():
        if benefit.proxy_class in mapping:
            benefit.type = mapping[benefit.proxy_class]
            benefit.proxy_class = None
            benefit.save()


def condition_to_proxy_classes(apps, schema_editor):
    Condition = apps.get_model("offer", "Condition")
    mapping = {
        'Count': 'oscar.apps.offer.conditions.CountCondition',
        'Value': 'oscar.apps.offer.conditions.ValueCondition',
        'Coverage': 'oscar.apps.offer.conditions.CoverageCondition',
    }
    for condition in Condition.objects.all():
        if condition.type in mapping:
            condition.proxy_class = mapping[condition.type]
            condition.type = ''
            condition.save()


def condition_from_proxy_classes(apps, schema_editor):
    Condition = apps.get_model("offer", "Condition")
    mapping = {
        'oscar.apps.offer.conditions.CountCondition': 'Count',
        'oscar.apps.offer.conditions.ValueCondition': 'Value',
        'oscar.apps.offer.conditions.CoverageCondition': 'Coverage',
    }
    for condition in Condition.objects.all():
        if condition.proxy_class in mapping:
            condition.type = mapping[condition.proxy_class]
            condition.proxy_class = None
            condition.save()


class Migration(migrations.Migration):
    dependencies = [
        ('offer', '0004_conditionaloffer_groups'),
    ]

    operations = [
        migrations.AlterField(
            model_name='condition',
            name='proxy_class',
            field=fields.NullCharField(default=None, max_length=255, verbose_name='Custom class'),
        ),
        migrations.RunPython(benefit_to_proxy_classes, benefit_from_proxy_classes),
        migrations.RunPython(condition_to_proxy_classes, condition_from_proxy_classes),
    ]
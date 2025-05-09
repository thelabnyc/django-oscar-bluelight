# Generated by Django 1.9.6 on 2016-11-15 11:15

from django.db import migrations


def use_bluelight_forward(apps, schema_editor):
    Benefit = apps.get_model("offer", "Benefit")
    Benefit.objects.filter(
        proxy_class="oscar.apps.offer.benefits.AbsoluteDiscountBenefit"
    ).update(
        proxy_class="oscarbluelight.offer.benefits.BluelightAbsoluteDiscountBenefit"
    )
    Benefit.objects.filter(
        proxy_class="oscar.apps.offer.benefits.FixedPriceBenefit"
    ).update(proxy_class="oscarbluelight.offer.benefits.BluelightFixedPriceBenefit")
    Benefit.objects.filter(
        proxy_class="oscar.apps.offer.benefits.MultibuyDiscountBenefit"
    ).update(
        proxy_class="oscarbluelight.offer.benefits.BluelightMultibuyDiscountBenefit"
    )
    Benefit.objects.filter(
        proxy_class="oscar.apps.offer.benefits.PercentageDiscountBenefit"
    ).update(
        proxy_class="oscarbluelight.offer.benefits.BluelightPercentageDiscountBenefit"
    )
    Benefit.objects.filter(
        proxy_class="oscar.apps.offer.benefits.ShippingAbsoluteDiscountBenefit"
    ).update(
        proxy_class="oscarbluelight.offer.benefits.BluelightShippingAbsoluteDiscountBenefit"
    )
    Benefit.objects.filter(
        proxy_class="oscar.apps.offer.benefits.ShippingBenefit"
    ).update(proxy_class="oscarbluelight.offer.benefits.BluelightShippingBenefit")
    Benefit.objects.filter(
        proxy_class="oscar.apps.offer.benefits.ShippingFixedPriceBenefit"
    ).update(
        proxy_class="oscarbluelight.offer.benefits.BluelightShippingFixedPriceBenefit"
    )
    Benefit.objects.filter(
        proxy_class="oscar.apps.offer.benefits.ShippingPercentageDiscountBenefit"
    ).update(
        proxy_class="oscarbluelight.offer.benefits.BluelightShippingPercentageDiscountBenefit"
    )
    Condition = apps.get_model("offer", "Condition")
    Condition.objects.filter(
        proxy_class="oscar.apps.offer.conditions.CountCondition"
    ).update(proxy_class="oscarbluelight.offer.conditions.BluelightCountCondition")
    Condition.objects.filter(
        proxy_class="oscar.apps.offer.conditions.CoverageCondition"
    ).update(proxy_class="oscarbluelight.offer.conditions.BluelightCoverageCondition")
    Condition.objects.filter(
        proxy_class="oscar.apps.offer.conditions.ValueCondition"
    ).update(proxy_class="oscarbluelight.offer.conditions.BluelightValueCondition")


def use_bluelight_reverse(apps, schema_editor):
    Benefit = apps.get_model("offer", "Benefit")
    Benefit.objects.filter(
        proxy_class="oscarbluelight.offer.benefits.BluelightAbsoluteDiscountBenefit"
    ).update(proxy_class="oscar.apps.offer.benefits.AbsoluteDiscountBenefit")
    Benefit.objects.filter(
        proxy_class="oscarbluelight.offer.benefits.BluelightFixedPriceBenefit"
    ).update(proxy_class="oscar.apps.offer.benefits.FixedPriceBenefit")
    Benefit.objects.filter(
        proxy_class="oscarbluelight.offer.benefits.BluelightMultibuyDiscountBenefit"
    ).update(proxy_class="oscar.apps.offer.benefits.MultibuyDiscountBenefit")
    Benefit.objects.filter(
        proxy_class="oscarbluelight.offer.benefits.BluelightPercentageDiscountBenefit"
    ).update(proxy_class="oscar.apps.offer.benefits.PercentageDiscountBenefit")
    Benefit.objects.filter(
        proxy_class="oscarbluelight.offer.benefits.BluelightShippingAbsoluteDiscountBenefit"
    ).update(proxy_class="oscar.apps.offer.benefits.ShippingAbsoluteDiscountBenefit")
    Benefit.objects.filter(
        proxy_class="oscarbluelight.offer.benefits.BluelightShippingBenefit"
    ).update(proxy_class="oscar.apps.offer.benefits.ShippingBenefit")
    Benefit.objects.filter(
        proxy_class="oscarbluelight.offer.benefits.BluelightShippingFixedPriceBenefit"
    ).update(proxy_class="oscar.apps.offer.benefits.ShippingFixedPriceBenefit")
    Benefit.objects.filter(
        proxy_class="oscarbluelight.offer.benefits.BluelightShippingPercentageDiscountBenefit"
    ).update(proxy_class="oscar.apps.offer.benefits.ShippingPercentageDiscountBenefit")
    Condition = apps.get_model("offer", "Condition")
    Condition.objects.filter(
        proxy_class="oscarbluelight.offer.conditions.BluelightCountCondition"
    ).update(proxy_class="oscar.apps.offer.conditions.CountCondition")
    Condition.objects.filter(
        proxy_class="oscarbluelight.offer.conditions.BluelightCoverageCondition"
    ).update(proxy_class="oscar.apps.offer.conditions.CoverageCondition")
    Condition.objects.filter(
        proxy_class="oscarbluelight.offer.conditions.BluelightValueCondition"
    ).update(proxy_class="oscar.apps.offer.conditions.ValueCondition")


class Migration(migrations.Migration):
    dependencies = [
        ("offer", "0005_auto_20160719_1238"),
    ]

    operations = [
        migrations.CreateModel(
            name="BluelightAbsoluteDiscountBenefit",
            fields=[],
            options={
                "verbose_name": "Absolute discount benefit",
                "verbose_name_plural": "Absolute discount benefits",
                "proxy": True,
            },
            bases=("offer.absolutediscountbenefit",),
        ),
        migrations.CreateModel(
            name="BluelightCountCondition",
            fields=[],
            options={
                "verbose_name": "Count condition",
                "verbose_name_plural": "Count conditions",
                "proxy": True,
            },
            bases=("offer.countcondition",),
        ),
        migrations.CreateModel(
            name="BluelightCoverageCondition",
            fields=[],
            options={
                "verbose_name": "Coverage Condition",
                "verbose_name_plural": "Coverage Conditions",
                "proxy": True,
            },
            bases=("offer.coveragecondition",),
        ),
        migrations.CreateModel(
            name="BluelightFixedPriceBenefit",
            fields=[],
            options={
                "verbose_name": "Fixed price benefit",
                "verbose_name_plural": "Fixed price benefits",
                "proxy": True,
            },
            bases=("offer.fixedpricebenefit",),
        ),
        migrations.CreateModel(
            name="BluelightMultibuyDiscountBenefit",
            fields=[],
            options={
                "verbose_name": "Multibuy discount benefit",
                "verbose_name_plural": "Multibuy discount benefits",
                "proxy": True,
            },
            bases=("offer.multibuydiscountbenefit",),
        ),
        migrations.CreateModel(
            name="BluelightPercentageDiscountBenefit",
            fields=[],
            options={
                "verbose_name": "Percentage discount benefit",
                "verbose_name_plural": "Percentage discount benefits",
                "proxy": True,
            },
            bases=("offer.percentagediscountbenefit",),
        ),
        migrations.CreateModel(
            name="BluelightShippingAbsoluteDiscountBenefit",
            fields=[],
            options={
                "verbose_name": "Shipping absolute discount benefit",
                "verbose_name_plural": "Shipping absolute discount benefits",
                "proxy": True,
            },
            bases=("offer.shippingabsolutediscountbenefit",),
        ),
        migrations.CreateModel(
            name="BluelightShippingBenefit",
            fields=[],
            options={
                "proxy": True,
            },
            bases=("offer.shippingbenefit",),
        ),
        migrations.CreateModel(
            name="BluelightShippingFixedPriceBenefit",
            fields=[],
            options={
                "verbose_name": "Fixed price shipping benefit",
                "verbose_name_plural": "Fixed price shipping benefits",
                "proxy": True,
            },
            bases=("offer.shippingfixedpricebenefit",),
        ),
        migrations.CreateModel(
            name="BluelightShippingPercentageDiscountBenefit",
            fields=[],
            options={
                "verbose_name": "Shipping percentage discount benefit",
                "verbose_name_plural": "Shipping percentage discount benefits",
                "proxy": True,
            },
            bases=("offer.shippingpercentagediscountbenefit",),
        ),
        migrations.CreateModel(
            name="BluelightValueCondition",
            fields=[],
            options={
                "verbose_name": "Value condition",
                "verbose_name_plural": "Value conditions",
                "proxy": True,
            },
            bases=("offer.valuecondition",),
        ),
        migrations.RunPython(use_bluelight_forward, use_bluelight_reverse),
    ]

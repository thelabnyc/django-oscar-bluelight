from decimal import Decimal as D

from django.test import TransactionTestCase
from django_redis import get_redis_connection

from oscarbluelight.offer.models import (
    Benefit,
    CompoundBenefit,
    CompoundCondition,
    Condition,
    Range,
)

COMPOUND_BENEFIT_CPATH = "oscarbluelight.offer.benefits.CompoundBenefit"
COMPOUND_CONDITION_CPATH = "oscarbluelight.offer.conditions.CompoundCondition"
PERCENTAGE_BENEFIT_CPATH = (
    "oscarbluelight.offer.benefits.BluelightPercentageDiscountBenefit"
)
COUNT_CONDITION_CPATH = "oscarbluelight.offer.conditions.BluelightCountCondition"


class BenefitCompoundChildAutoCreateTest(TransactionTestCase):
    """
    Regression tests: when a Benefit's proxy_class names the
    (non-proxy, MTI) CompoundBenefit class and no child row exists, save() must
    actually create the CompoundBenefit child row instead of silently no-oping
    and leaving an orphaned base row that 500s the dashboard.
    """

    def setUp(self):
        conn = get_redis_connection("redis")
        conn.flushall()
        self.range = Range.objects.create(
            name="All products", includes_all_products=True
        )

    def test_create_with_compound_proxy_class_creates_child_row(self):
        benefit = Benefit.objects.create(proxy_class=COMPOUND_BENEFIT_CPATH)
        self.assertTrue(CompoundBenefit.objects.filter(pk=benefit.pk).exists())

    def test_flip_existing_benefit_to_compound_creates_child_and_keeps_values(self):
        benefit = Benefit.objects.create(
            proxy_class=PERCENTAGE_BENEFIT_CPATH,
            value=D("15.00"),
            range=self.range,
            max_affected_items=3,
        )
        # Reload as a fresh instance, as the dashboard edit path would.
        benefit = Benefit.objects.get(pk=benefit.pk)
        benefit.proxy_class = COMPOUND_BENEFIT_CPATH
        benefit.save()

        self.assertTrue(CompoundBenefit.objects.filter(pk=benefit.pk).exists())
        # The MTI parent-table UPDATE must not clobber the original values.
        benefit.refresh_from_db()
        self.assertEqual(benefit.value, D("15.00"))
        self.assertEqual(benefit.range_id, self.range.pk)
        self.assertEqual(benefit.max_affected_items, 3)


class ConditionCompoundChildAutoCreateTest(TransactionTestCase):
    """
    Regression tests: the Condition.save() equivalent of the above.
    On current code this raises CompoundCondition.DoesNotExist mid-insert.
    """

    def setUp(self):
        conn = get_redis_connection("redis")
        conn.flushall()
        self.range = Range.objects.create(
            name="All products", includes_all_products=True
        )

    def test_create_with_compound_proxy_class_creates_child_row(self):
        condition = Condition.objects.create(proxy_class=COMPOUND_CONDITION_CPATH)
        self.assertTrue(CompoundCondition.objects.filter(pk=condition.pk).exists())

    def test_flip_existing_condition_to_compound_creates_child_and_keeps_values(self):
        condition = Condition.objects.create(
            proxy_class=COUNT_CONDITION_CPATH,
            value=D("5"),
            range=self.range,
        )
        condition = Condition.objects.get(pk=condition.pk)
        condition.proxy_class = COMPOUND_CONDITION_CPATH
        condition.save()

        self.assertTrue(CompoundCondition.objects.filter(pk=condition.pk).exists())
        condition.refresh_from_db()
        self.assertEqual(condition.value, D("5"))
        self.assertEqual(condition.range_id, self.range.pk)

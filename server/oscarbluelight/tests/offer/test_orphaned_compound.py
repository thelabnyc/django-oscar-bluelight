from django.contrib.auth.models import User
from django.test import Client, TestCase
from django.urls import reverse
from django_redis import get_redis_connection

from oscarbluelight.offer.models import Benefit, Condition, Range

COMPOUND_BENEFIT_CPATH = "oscarbluelight.offer.benefits.CompoundBenefit"
COMPOUND_CONDITION_CPATH = "oscarbluelight.offer.conditions.CompoundCondition"
PERCENTAGE_BENEFIT_CPATH = (
    "oscarbluelight.offer.benefits.BluelightPercentageDiscountBenefit"
)
COUNT_CONDITION_CPATH = "oscarbluelight.offer.conditions.BluelightCountCondition"


class OrphanedCompoundTest(TestCase):
    """
    Regression tests: a base Benefit/Condition row whose proxy_class
    names the (non-proxy, MTI) compound class but has no child row must not
    500 the dashboard. proxy() should leave such an orphan as its base class
    (and log a warning) instead of class-swapping to an instance whose pk
    dereferences a missing child row.
    """

    def setUp(self):
        conn = get_redis_connection("redis")
        conn.flushall()
        self.client = Client()
        self.range = Range.objects.create(
            name="All products", includes_all_products=True
        )
        self.user = User.objects.create_user(
            "admin",
            "admin@test.com",
            "password",
            is_staff=True,
            is_superuser=True,
        )

    def _orphan_benefit(self):
        benefit = Benefit.objects.create(
            proxy_class=PERCENTAGE_BENEFIT_CPATH, value=10, range=self.range
        )
        # Bypass save() so the child row is never created.
        Benefit.objects.filter(pk=benefit.pk).update(proxy_class=COMPOUND_BENEFIT_CPATH)
        return Benefit.objects.get(pk=benefit.pk)

    def _orphan_condition(self):
        condition = Condition.objects.create(
            proxy_class=COUNT_CONDITION_CPATH, value=1, range=self.range
        )
        Condition.objects.filter(pk=condition.pk).update(
            proxy_class=COMPOUND_CONDITION_CPATH
        )
        return Condition.objects.get(pk=condition.pk)

    def test_orphaned_benefit_proxy_does_not_raise(self):
        orphan = self._orphan_benefit()
        with self.assertLogs("oscarbluelight.offer.models", level="WARNING") as cm:
            proxy = orphan.proxy()
        self.assertEqual(proxy.pk, orphan.pk)
        self.assertIn("no child row", "".join(cm.output))

    def test_orphaned_condition_proxy_does_not_raise(self):
        orphan = self._orphan_condition()
        proxy = orphan.proxy()
        self.assertEqual(proxy.pk, orphan.pk)

    def test_orphaned_benefit_list_renders(self):
        self._orphan_benefit()
        self.client.login(username="admin", password="password")
        response = self.client.get(reverse("dashboard:benefit-list"))
        self.assertEqual(response.status_code, 200)

    def test_orphaned_condition_list_renders(self):
        self._orphan_condition()
        self.client.login(username="admin", password="password")
        response = self.client.get(reverse("dashboard:condition-list"))
        self.assertEqual(response.status_code, 200)

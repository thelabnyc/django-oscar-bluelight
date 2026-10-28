from decimal import Decimal

from django.contrib.auth.models import User
from django.test import Client, RequestFactory, TestCase, TransactionTestCase
from django.urls import reverse
from django.utils import timezone
from django_redis import get_redis_connection
from oscar.test.factories import create_product, create_stockrecord

from oscarbluelight.dashboard.offers.serializers import OfferSerializer
from oscarbluelight.offer.models import Benefit, Condition, ConditionalOffer, Range
from oscarbluelight.voucher.models import Voucher


def _create_voucher(code: str, parent: Voucher | None = None) -> Voucher:
    return Voucher.objects.create(
        parent=parent,
        name=code,
        code=code,
        usage=Voucher.MULTI_USE,
        start_datetime=timezone.now(),
        end_datetime=timezone.now(),
        limit_usage_by_group=False,
    )


class OfferVoucherLookupTest(TestCase):
    def setUp(self):
        self.range = Range.objects.create(
            name="All products", includes_all_products=True
        )
        self.condition = Condition.objects.create(
            proxy_class="oscarbluelight.offer.conditions.BluelightCountCondition",
            value=1,
            range=self.range,
        )
        self.benefit = Benefit.objects.create(
            proxy_class="oscarbluelight.offer.benefits.BluelightPercentageDiscountBenefit",
            value=10,
            range=self.range,
        )
        self.voucher_offer = ConditionalOffer.objects.create(
            name="Voucher offer",
            condition=self.condition,
            benefit=self.benefit,
            offer_type=ConditionalOffer.VOUCHER,
        )
        self.parent = _create_voucher("parent")
        self.child = _create_voucher("child", parent=self.parent)
        self.other = _create_voucher("other")
        self.parent.offers.add(self.voucher_offer)
        self.child.offers.add(self.voucher_offer)

    def test_benefit_vouchers_excludes_children(self):
        self.assertEqual([v.pk for v in self.benefit.vouchers], [self.parent.pk])

    def test_offer_serializer_vouchers_excludes_children(self):
        request = RequestFactory().get("/")
        data = OfferSerializer(self.voucher_offer, context={"request": request}).data
        self.assertEqual([v["code"] for v in data["vouchers"]], ["PARENT"])


class RangePriceListViewTest(TransactionTestCase):
    def setUp(self):
        get_redis_connection("redis").flushall()
        self.range = Range.objects.create(name="Prices")
        self.product = create_product()
        self.stockrecord = create_stockrecord(
            self.product, price=Decimal("10.00"), num_in_stock=5
        )
        self.range.add_product(self.product)
        User.objects.create_user(
            "admin", "admin@test.com", "password", is_staff=True, is_superuser=True
        )
        self.client = Client()
        self.client.login(username="admin", password="password")
        self.url = reverse("dashboard:range-prices", args=(self.range.pk,))
        self.form_data = {"operation_type": "ABSOLUTE", "amount": "5.00"}

    def test_get_renders_range(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["range"], self.range)

    def test_preview_does_not_change_prices(self):
        response = self.client.post(self.url, self.form_data)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.context["changes"][self.stockrecord.pk]["price"], Decimal("15.00")
        )
        self.stockrecord.refresh_from_db()
        self.assertEqual(self.stockrecord.price, Decimal("10.00"))

    def test_apply_changes_prices(self):
        response = self.client.post(self.url, {**self.form_data, "apply": "1"})
        self.assertRedirects(response, self.url, fetch_redirect_response=False)
        self.stockrecord.refresh_from_db()
        self.assertEqual(self.stockrecord.price, Decimal("15.00"))

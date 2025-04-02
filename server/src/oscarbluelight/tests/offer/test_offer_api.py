from datetime import timedelta
from urllib.parse import urlencode

from django.contrib.auth.models import User
from django.test import Client, TestCase
from django.urls import reverse
from django.utils import timezone

from oscarbluelight.offer.models import (
    BluelightCountCondition,
    BluelightPercentageDiscountBenefit,
    ConditionalOffer,
    Range,
)


class OfferAPIViewTest(TestCase):
    def test_get(self):
        User.objects.create_user(
            "john", "john@example.com", "password", is_staff=True, is_superuser=True
        )
        client = Client()
        client.login(username="john", password="password")
        base_url = reverse("dashboard:offer-api-list")

        start_dt = timezone.now() - timedelta(days=1)
        end_dt = timezone.now() + timedelta(days=1)

        rng = Range.objects.create(name="Product", includes_all_products=True)
        condition = BluelightCountCondition.objects.create(
            range=rng,
            proxy_class="oscarbluelight.offer.conditions.BluelightCountCondition",
            value=1,
        )
        benefit = BluelightPercentageDiscountBenefit.objects.create(
            range=rng,
            proxy_class="oscarbluelight.offer.benefits.BluelightPercentageDiscountBenefit",
            value=20,
        )
        for i in range(23):
            ConditionalOffer.objects.create(
                name=f"Product voucher offer{i}",
                start_datetime=start_dt,
                end_datetime=end_dt,
                condition=condition,
                benefit=benefit,
                status=ConditionalOffer.OPEN,
                offer_type=ConditionalOffer.VOUCHER,
            )
        for i in range(4):
            ConditionalOffer.objects.create(
                name=f"Product site offer{i}",
                start_datetime=start_dt,
                end_datetime=end_dt,
                condition=condition,
                benefit=benefit,
                status=ConditionalOffer.OPEN,
                offer_type=ConditionalOffer.SITE,
            )

        resp = client.get(base_url)
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(len(data["results"]), 10)
        self.assertTrue(data["pagination"]["more"])

        url = f"{base_url}?{urlencode({'page': 5})}"
        resp = client.get(url)
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(len(data["results"]), 7)
        self.assertFalse(data["pagination"]["more"])

        query_kwargs = {
            "q": "Product voucher",
            "page": 2,
            "items_per_page": 8,
        }
        url = f"{base_url}?{urlencode(query_kwargs)}"
        resp = client.get(url)
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(len(data["results"]), 8)
        self.assertTrue(
            all(
                [r["text"].startswith("Product voucher offer") for r in data["results"]]
            )
        )
        self.assertTrue(data["pagination"]["more"])

        query_kwargs = {
            "q": "product SITE",
            "page": 1,
            "items_per_page": 8,
        }
        url = f"{base_url}?{urlencode(query_kwargs)}"
        resp = client.get(url)
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(len(data["results"]), 4)
        self.assertFalse(data["pagination"]["more"])

        query_kwargs = {
            "page": 2,
            "items_per_page": 20,
            "offer_type": ConditionalOffer.VOUCHER,
        }
        url = f"{base_url}?{urlencode(query_kwargs)}"
        resp = client.get(url)
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(len(data["results"]), 3)
        self.assertFalse(data["pagination"]["more"])

        query_kwargs = {
            "page": 1,
            "offer_type": ConditionalOffer.SITE,
        }
        url = f"{base_url}?{urlencode(query_kwargs)}"
        resp = client.get(url)
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(len(data["results"]), 4)
        self.assertFalse(data["pagination"]["more"])

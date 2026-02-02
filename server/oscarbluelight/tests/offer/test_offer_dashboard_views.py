from django.contrib.auth.models import User
from django.db import connection
from django.test import Client, TestCase
from django.test.utils import CaptureQueriesContext
from django.urls import reverse
from django.utils import timezone
from django_redis import get_redis_connection

from oscarbluelight.offer.models import (
    Benefit,
    Condition,
    ConditionalOffer,
    OfferGroup,
    Range,
)
from oscarbluelight.voucher.models import Voucher


class OfferListViewTest(TestCase):
    """
    Tests for the optimized OfferListView that computes voucher_count after pagination
    and supports sorting without breaking performance.
    """

    def setUp(self):
        # Flush the cache
        conn = get_redis_connection("redis")
        conn.flushall()

        self.client = Client()

        # Create a range that includes all products
        self.all_products = Range()
        self.all_products.name = "All Products"
        self.all_products.includes_all_products = True
        self.all_products.save()

        # Create condition
        self.condition = Condition()
        self.condition.proxy_class = (
            "oscarbluelight.offer.conditions.BluelightCountCondition"
        )
        self.condition.value = 1
        self.condition.range = self.all_products
        self.condition.save()

        # Create benefit
        self.benefit = Benefit()
        self.benefit.proxy_class = (
            "oscarbluelight.offer.benefits.BluelightPercentageDiscountBenefit"
        )
        self.benefit.value = 10
        self.benefit.range = self.all_products
        self.benefit.save()

        # Create offer groups with different priorities
        self.high_priority_group = OfferGroup.objects.create(
            name="High Priority Group", priority=100
        )
        self.low_priority_group = OfferGroup.objects.create(
            name="Low Priority Group", priority=10
        )

        # Create test offers with different priorities and groups
        self.offers = []
        for i in range(24):
            offer = ConditionalOffer.objects.create(
                name=f"Test Offer {i:02d}",
                short_name=f"Offer{i:02d}",
                condition=self.condition,
                benefit=self.benefit,
                offer_type=ConditionalOffer.SITE,
                status=ConditionalOffer.OPEN,
                priority=i,
            )
            # Assign to groups alternately
            if i % 2 == 0:
                offer.offer_group = self.high_priority_group
            else:
                offer.offer_group = self.low_priority_group
            offer.save()
            self.offers.append(offer)

        self.offers.append(
            ConditionalOffer.objects.create(
                name="Test Offer 25",
                short_name="Offer25",
                condition=self.condition,
                benefit=self.benefit,
                offer_type=ConditionalOffer.VOUCHER,
                status=ConditionalOffer.OPEN,
                priority=25,
                offer_group=self.low_priority_group,
            )
        )
        self.offers.append(
            ConditionalOffer.objects.create(
                name="Test Offer 26",
                short_name="Offer26",
                condition=self.condition,
                benefit=self.benefit,
                offer_type=ConditionalOffer.VOUCHER,
                status=ConditionalOffer.SUSPENDED,
                priority=26,
                offer_group=self.low_priority_group,
            )
        )
        # Create vouchers for some offers to test voucher_count
        start_dt = timezone.make_aware(timezone.datetime(2020, 1, 1))
        end_dt = timezone.make_aware(timezone.datetime(2030, 1, 1))

        self.voucher1 = Voucher.objects.create(
            name="Voucher 1",
            code="VOUCHER1",
            usage=Voucher.SINGLE_USE,
            start_datetime=start_dt,
            end_datetime=end_dt,
        )
        self.voucher1.offers.add(self.offers[0], self.offers[1])

        self.voucher2 = Voucher.objects.create(
            name="Voucher 2",
            code="VOUCHER2",
            usage=Voucher.SINGLE_USE,
            start_datetime=start_dt,
            end_datetime=end_dt,
        )
        self.voucher2.offers.add(self.offers[0])  # offers[0] should have count=2

        self.voucher3 = Voucher.objects.create(
            name="Voucher 3",
            code="VOUCHER3",
            usage=Voucher.SINGLE_USE,
            start_datetime=start_dt,
            end_datetime=end_dt,
        )
        self.voucher3.offers.add(self.offers[2])  # offers[2] should have count=1

        # Create admin user
        self.user = User.objects.create_user(
            "admin",
            "admin@test.com",
            "password",
            is_staff=True,
            is_superuser=True,
        )

    def test_offer_list_view_returns_200(self):
        """Test that the offer list view returns HTTP 200"""
        self.client.login(username="admin", password="password")
        response = self.client.get(reverse("dashboard:offer-list"))
        self.assertEqual(response.status_code, 200)

    def test_offer_list_view_default_ordering(self):
        """
        Test that offers are ordered by offer_group__priority DESC, priority DESC, pk ASC
        when no sort parameter is provided.
        """
        self.client.login(username="admin", password="password")
        response = self.client.get(reverse("dashboard:offer-list"))
        self.assertEqual(response.status_code, 200)

        offers = list(response.context["object_list"])
        self.assertTrue(len(offers) > 0)

        # First offer should be from high_priority_group (priority=100)
        # with highest priority value
        first_offer = offers[0]
        self.assertEqual(first_offer.offer_group, self.high_priority_group)

        # Verify ordering is maintained
        # High priority group offers should come first
        for i in range(len(offers) - 1):
            curr = offers[i]
            next_offer = offers[i + 1]

            # Compare by group priority first (DESC)
            if curr.offer_group and next_offer.offer_group:
                curr_group_priority = curr.offer_group.priority
                next_group_priority = next_offer.offer_group.priority
                self.assertGreaterEqual(curr_group_priority, next_group_priority)

                # If same group, compare by offer priority (DESC)
                if curr_group_priority == next_group_priority:
                    self.assertGreaterEqual(curr.priority, next_offer.priority)

    def test_offer_list_view_voucher_count_computation(self):
        """
        Test that voucher_count is correctly computed for each offer after pagination.
        This verifies the optimization works correctly.
        """
        self.client.login(username="admin", password="password")
        response = self.client.get(reverse("dashboard:offer-list"))
        self.assertEqual(response.status_code, 200)

        offers = list(response.context["object_list"])
        self.assertTrue(len(offers) > 0)

        # Find our test offers in the results
        offer_dict = {offer.id: offer for offer in offers}

        # offers[0] should have 2 vouchers
        if self.offers[0].id in offer_dict:
            offer = offer_dict[self.offers[0].id]
            self.assertTrue(hasattr(offer, "voucher_count"))
            self.assertEqual(offer.voucher_count, 2)

        # offers[1] should have 1 voucher
        if self.offers[1].id in offer_dict:
            offer = offer_dict[self.offers[1].id]
            self.assertTrue(hasattr(offer, "voucher_count"))
            self.assertEqual(offer.voucher_count, 1)

        # offers[2] should have 1 voucher
        if self.offers[2].id in offer_dict:
            offer = offer_dict[self.offers[2].id]
            self.assertTrue(hasattr(offer, "voucher_count"))
            self.assertEqual(offer.voucher_count, 1)

        # offers[3+] should have 0 vouchers
        if self.offers[3].id in offer_dict:
            offer = offer_dict[self.offers[3].id]
            self.assertTrue(hasattr(offer, "voucher_count"))
            self.assertEqual(offer.voucher_count, 0)

    def test_offer_list_view_voucher_count_not_in_main_query(self):
        """
        Test that voucher_count is NOT computed via subquery in the main queryset.
        This ensures the performance optimization is in place.
        """
        self.client.login(username="admin", password="password")

        with CaptureQueriesContext(connection) as queries:
            response = self.client.get(reverse("dashboard:offer-list"))
            self.assertEqual(response.status_code, 200)

            # Check the main offer SELECT query
            main_query = None
            for query in queries:
                sql = query["sql"]
                if (
                    'FROM "offer_conditionaloffer"' in sql
                    and "LIMIT" in sql
                    and "OFFSET" not in sql
                ):
                    main_query = sql
                    break

            self.assertIsNotNone(main_query, "Could not find main offer query")

            # Verify voucher_count is NOT computed in the main query
            # (no subquery with voucher_voucher_offers in the SELECT clause)
            self.assertNotIn("voucher_voucher_offers", main_query)

    def test_offer_list_view_sorting_by_name(self):
        """Test that sorting by name works correctly"""
        self.client.login(username="admin", password="password")
        response = self.client.get(
            reverse("dashboard:offer-list"), data={"sort": "name"}
        )
        self.assertEqual(response.status_code, 200)

        offers = list(response.context["object_list"])
        self.assertTrue(len(offers) > 0)

        # Verify ascending name order
        names = [offer.name for offer in offers]
        self.assertEqual(names, sorted(names))

    def test_offer_list_view_sorting_by_offer_type(self):
        """Test that sorting by offer_type works correctly"""
        self.client.login(username="admin", password="password")
        response = self.client.get(
            reverse("dashboard:offer-list"), data={"sort": "offer_type", "dir": "desc"}
        )
        self.assertEqual(response.status_code, 200)

        offers = list(response.context["object_list"])
        self.assertTrue(len(offers) > 0)

        # Verify descending offer type order
        offer_types = [offer.offer_type for offer in offers]
        self.assertEqual(offer_types, sorted(offer_types, reverse=True))

    def test_offer_list_view_sorting_by_num_applications(self):
        """Test that sorting by num_applications works correctly"""
        # Set different application counts for testing
        self.offers[0].num_applications = 100
        self.offers[0].save()
        self.offers[1].num_applications = 50
        self.offers[1].save()
        self.offers[2].num_applications = 25
        self.offers[2].save()

        self.client.login(username="admin", password="password")
        response = self.client.get(
            reverse("dashboard:offer-list"), data={"sort": "num_applications"}
        )
        self.assertEqual(response.status_code, 200)

        offers = list(response.context["object_list"])
        self.assertTrue(len(offers) > 0)

        # Verify ascending order (lowest to highest)
        applications = [offer.num_applications for offer in offers]
        self.assertEqual(applications, sorted(applications))

    def test_offer_list_view_sorting_by_total_discount(self):
        """Test that sorting by total_discount works correctly"""
        # Set different discount totals for testing
        self.offers[0].total_discount = 1000
        self.offers[0].save()
        self.offers[1].total_discount = 500
        self.offers[1].save()
        self.offers[2].total_discount = 250
        self.offers[2].save()

        self.client.login(username="admin", password="password")
        response = self.client.get(
            reverse("dashboard:offer-list"), data={"sort": "total_discount"}
        )
        self.assertEqual(response.status_code, 200)

        offers = list(response.context["object_list"])
        self.assertTrue(len(offers) > 0)

        # Verify ascending order
        discounts = [offer.total_discount for offer in offers]
        self.assertEqual(discounts, sorted(discounts))

    def test_offer_list_view_pagination(self):
        """Test that pagination works correctly with the optimization"""
        self.client.login(username="admin", password="password")

        # Get page 1
        response = self.client.get(reverse("dashboard:offer-list"))
        self.assertEqual(response.status_code, 200)
        page1_offers = list(response.context["object_list"])
        self.assertEqual(len(page1_offers), 20)  # Default page size

        # Get page 2
        response = self.client.get(reverse("dashboard:offer-list"), data={"page": "2"})
        self.assertEqual(response.status_code, 200)
        page2_offers = list(response.context["object_list"])
        self.assertEqual(len(page2_offers), 6)  # Remaining offers

        # Verify no overlap between pages
        page1_ids = {offer.id for offer in page1_offers}
        page2_ids = {offer.id for offer in page2_offers}
        self.assertEqual(len(page1_ids & page2_ids), 0)

    def test_offer_list_view_pagination_with_voucher_count(self):
        """
        Test that voucher_count is correctly computed on page 2.
        This verifies the key performance optimization.
        """
        self.client.login(username="admin", password="password")

        # Get page 2
        response = self.client.get(reverse("dashboard:offer-list"), data={"page": "2"})
        self.assertEqual(response.status_code, 200)

        offers = list(response.context["object_list"])
        self.assertTrue(len(offers) > 0)

        # All offers on page 2 should have voucher_count attribute
        for offer in offers:
            self.assertTrue(
                hasattr(offer, "voucher_count"),
                f"Offer {offer.id} missing voucher_count",
            )
            # Should be 0 or a positive integer
            self.assertGreaterEqual(offer.voucher_count, 0)

    def test_offer_list_view_filtering_active_offers(self):
        """Test filtering by is_active parameter"""
        self.client.login(username="admin", password="password")

        # All our test offers are active (status=OPEN)
        for page in [1, 2]:
            response = self.client.get(
                reverse("dashboard:offer-list"),
                data={"is_active": "true", "page": page},
            )
            self.assertEqual(response.status_code, 200)

            offers = list(response.context["object_list"])
            self.assertTrue(len(offers) > 0)

            # All returned offers should be active
            for offer in offers:
                self.assertEqual(offer.status, ConditionalOffer.OPEN)

    def test_offer_list_view_filtering_by_offer_group(self):
        """Test filtering by offer_group parameter"""
        self.client.login(username="admin", password="password")

        response = self.client.get(
            reverse("dashboard:offer-list"),
            data={"offer_group": self.high_priority_group.slug},
        )
        self.assertEqual(response.status_code, 200)

        offers = list(response.context["object_list"])
        self.assertTrue(len(offers) > 0)

        # All returned offers should be in the high priority group
        for offer in offers:
            self.assertEqual(offer.offer_group_id, self.high_priority_group.id)

    def test_offer_list_view_sorting_preserves_voucher_count(self):
        """
        Test that sorting still allows voucher_count to be computed correctly.
        This ensures sorting doesn't break the optimization.
        """
        self.client.login(username="admin", password="password")

        response = self.client.get(
            reverse("dashboard:offer-list"), data={"sort": "name"}
        )
        self.assertEqual(response.status_code, 200)

        offers = list(response.context["object_list"])
        offer_dict = {offer.id: offer for offer in offers}

        # Verify voucher counts are still correct even with sorting
        if self.offers[0].id in offer_dict:
            offer = offer_dict[self.offers[0].id]
            self.assertEqual(offer.voucher_count, 2)

    def test_offer_list_view_query_count_for_voucher_count(self):
        """
        Test that voucher_count is computed with a single query for all offers on the page,
        not N queries (one per offer).
        """
        self.client.login(username="admin", password="password")

        with CaptureQueriesContext(connection) as queries:
            response = self.client.get(reverse("dashboard:offer-list"))
            self.assertEqual(response.status_code, 200)

            # Count queries that access voucher_voucher_offers for counting
            voucher_count_queries = [
                q
                for q in queries
                if 'FROM "voucher_voucher_offers"' in q["sql"] and "COUNT" in q["sql"]
            ]

            # Should be exactly 1 query to count vouchers for all offers on the page
            self.assertEqual(
                len(voucher_count_queries),
                1,
                f"Expected 1 voucher count query, got {len(voucher_count_queries)}",
            )

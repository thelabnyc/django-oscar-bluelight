from decimal import Decimal as D
from django.test import TestCase, override_settings
from oscar.core.loading import get_model
from oscar.test import factories

Range = get_model("offer", "Range")
BluelightAbsoluteDiscountBenefit = get_model(
    "offer", "BluelightAbsoluteDiscountBenefit"
)
BluelightCountCondition = get_model("offer", "BluelightCountCondition")
ConditionalOffer = get_model("offer", "ConditionalOffer")
OrderDiscount = get_model("order", "OrderDiscount")


class ConditionalOfferModelTest(TestCase):
    def setUp(self):
        self.product = factories.ProductFactory()
        self.all_products_range = Range.objects.create(
            name="All products", includes_all_products=True
        )
        self.condition = BluelightCountCondition.objects.create(
            range=self.all_products_range,
            proxy_class="oscarbluelight.offer.conditions.BluelightCountCondition",
            value=1,
        )
        self.benefit = BluelightAbsoluteDiscountBenefit.objects.create(
            range=self.all_products_range,
            proxy_class="oscarbluelight.offer.benefits.BluelightAbsoluteDiscountBenefit",
            value=D("1.00"),
        )
        self.offer = ConditionalOffer(
            id=1, condition=self.condition, benefit=self.benefit
        )

        # Create orders that have different statuses
        self.order1 = factories.create_order(
            number="0000000000001",
            status="Delivered",
        )
        self.order2 = factories.create_order(
            number="0000000000002",
            status="Shipped",
        )
        self.order3 = factories.create_order(
            number="0000000000003",
            status="Acknowledged by ERP",
        )
        self.order_canceled = factories.create_order(
            number="0000000000004",
            status="Canceled",
        )
        self.order_retired = factories.create_order(
            number="0000000000005",
            status="Retired",
        )

    def test_recalculate_offer_total_discount(self):
        self.offer.total_discount = D("7.00")
        self.offer.save()

        OrderDiscount.objects.create(
            order=self.order1,
            category=OrderDiscount.BASKET,
            offer_id=self.offer.id,
            amount=D("1.00"),
            message="$1 off some things",
            frequency=1,
        )
        OrderDiscount.objects.create(
            order=self.order2,
            category=OrderDiscount.BASKET,
            offer_id=self.offer.id,
            amount=D("2.00"),
            message="$2 off some things",
            frequency=1,
        )
        OrderDiscount.objects.create(
            order=self.order2,
            category=OrderDiscount.BASKET,
            offer_id=self.offer.id,
            amount=D("3.00"),
            message="$3 off some things",
            frequency=1,
        )

        # Run the recalculation method
        ConditionalOffer.recalculate_offer_application_totals()
        # Get the most recent object of this offer to check the update query is executed correctly
        offer = ConditionalOffer.objects.get(pk=self.offer.pk)

        # Total discount should be updated as 1.00 + 2.00 + 3.00 = 6.00
        self.assertEqual(offer.total_discount, D("6.00"))

    def test_recalculate_offer_num_applications(self):
        self.offer.num_applications = 6
        self.offer.save()

        OrderDiscount.objects.create(
            order=self.order1,
            category=OrderDiscount.BASKET,
            offer_id=self.offer.id,
            amount=D("1.00"),
            message="$1 off some things",
            frequency=3,
        )
        OrderDiscount.objects.create(
            order=self.order2,
            category=OrderDiscount.BASKET,
            offer_id=self.offer.id,
            amount=D("2.00"),
            message="$2 off some things",
            frequency=2,
        )

        # Run the recalculation method
        ConditionalOffer.recalculate_offer_application_totals()
        # Get the most recent object of this offer to check the update query is executed correctly
        offer = ConditionalOffer.objects.get(pk=self.offer.pk)

        # Number of applications should be updated as the sum of the order discounts' frequency values: 3 + 2 = 5
        self.assertEqual(offer.num_applications, 5)

    def test_recalculate_offer_num_orders(self):
        self.offer.num_orders = 4
        self.offer.save()

        OrderDiscount.objects.create(
            order=self.order1,
            category=OrderDiscount.BASKET,
            offer_id=self.offer.id,
            amount=D("1.00"),
            message="$1 off some things",
            frequency=1,
        )
        OrderDiscount.objects.create(
            order=self.order2,
            category=OrderDiscount.BASKET,
            offer_id=self.offer.id,
            amount=D("2.00"),
            message="$2 off some things",
            frequency=2,
        )
        OrderDiscount.objects.create(
            order=self.order3,
            category=OrderDiscount.BASKET,
            offer_id=self.offer.id,
            amount=D("3.00"),
            message="$3 off some things",
            frequency=1,
        )

        # Run the recalculation method
        ConditionalOffer.recalculate_offer_application_totals()
        # Get the most recent object of this offer to check the update query is executed correctly
        offer = ConditionalOffer.objects.get(pk=self.offer.pk)

        # Number of orders should be updated as the count of the distinct orders
        # having a relation to the discounts that apply this offer: 3 distinct orders
        self.assertEqual(offer.num_orders, 3)

    def test_recalculate_offer_application_totals_with_no_status_filter(self):
        self.offer.total_discount = D("18.00")
        self.offer.num_applications = 10
        self.offer.num_orders = 7
        self.offer.save()

        OrderDiscount.objects.create(
            order=self.order1,
            category=OrderDiscount.BASKET,
            offer_id=self.offer.id,
            amount=D("1.00"),
            message="$1 off some things",
            frequency=1,
        )
        OrderDiscount.objects.create(
            order=self.order2,
            category=OrderDiscount.BASKET,
            offer_id=self.offer.id,
            amount=D("2.00"),
            message="$2 off some things",
            frequency=2,
        )
        OrderDiscount.objects.create(
            order=self.order3,
            category=OrderDiscount.BASKET,
            offer_id=self.offer.id,
            amount=D("3.00"),
            message="$3 off some things",
            frequency=3,
        )
        OrderDiscount.objects.create(
            order=self.order_canceled,
            category=OrderDiscount.BASKET,
            offer_id=self.offer.id,
            amount=D("4.00"),
            message="$4 off some things",
            frequency=1,
        )
        OrderDiscount.objects.create(
            order=self.order_retired,
            category=OrderDiscount.BASKET,
            offer_id=self.offer.id,
            amount=D("5.00"),
            message="$5 off some things",
            frequency=2,
        )

        # Run the recalculation method
        ConditionalOffer.recalculate_offer_application_totals()
        # Get the most recent object of this offer to check the update query is executed correctly
        offer = ConditionalOffer.objects.get(pk=self.offer.pk)

        # Total discount should be updated as 1.00 + 2.00 + 3.00 + 4.00 + 5.00 = 15.00
        self.assertEqual(offer.total_discount, D("15.00"))
        # Number of applications should be updated as the sum of the order discounts' frequency values: 1 + 2 + 3 + 1 + 2 = 9
        self.assertEqual(offer.num_applications, 9)
        # Number of orders should be updated as the count of the distinct orders
        # having a relation to the discounts that apply this offer: 5 distinct orders
        self.assertEqual(offer.num_orders, 5)

    @override_settings(BLUELIGHT_IGNORED_ORDER_STATUSES=["Canceled", "Retired"])
    def test_recalculate_offer_application_totals_with_status_filter(self):
        self.offer.total_discount = D("15.00")
        self.offer.num_applications = 8
        self.offer.num_orders = 4
        self.offer.save()

        OrderDiscount.objects.create(
            order=self.order1,
            category=OrderDiscount.BASKET,
            offer_id=self.offer.id,
            amount=D("1.00"),
            message="$1 off some things",
            frequency=1,
        )
        OrderDiscount.objects.create(
            order=self.order2,
            category=OrderDiscount.BASKET,
            offer_id=self.offer.id,
            amount=D("2.00"),
            message="$2 off some things",
            frequency=2,
        )
        OrderDiscount.objects.create(
            order=self.order3,
            category=OrderDiscount.BASKET,
            offer_id=self.offer.id,
            amount=D("3.00"),
            message="$3 off some things",
            frequency=3,
        )
        OrderDiscount.objects.create(
            order=self.order_canceled,
            category=OrderDiscount.BASKET,
            offer_id=self.offer.id,
            amount=D("4.00"),
            message="$4 off some things",
            frequency=1,
        )
        OrderDiscount.objects.create(
            order=self.order_retired,
            category=OrderDiscount.BASKET,
            offer_id=self.offer.id,
            amount=D("5.00"),
            message="$5 off some things",
            frequency=2,
        )

        # Run the recalculation method
        ConditionalOffer.recalculate_offer_application_totals()
        # Get the most recent object of this offer to check the update query is executed correctly
        offer = ConditionalOffer.objects.get(pk=self.offer.pk)

        # Total discount should be updated as 1.00 + 2.00 + 3.00 = 6.00
        # The last two discount amounts, 4.00 and 5.00, should not be counted since their orders statuses exist in BLUELIGHT_IGNORED_ORDER_STATUSES
        self.assertEqual(offer.total_discount, D("6.00"))
        # Number of applications should be updated as the sum of the order discounts' frequency values: 1 + 2 + 3 = 6
        # The last two number of applications, 1.00 and 2.00, should not be counted since their orders statuses exist in BLUELIGHT_IGNORED_ORDER_STATUSES
        self.assertEqual(offer.num_applications, 6)
        # Number of orders should be updated as the count of the distinct orders
        # having a relation to the discounts that apply this offer: 3 distinct orders
        # The last two discounts' orders should not be counted since their orders statuses exist in BLUELIGHT_IGNORED_ORDER_STATUSES
        self.assertEqual(offer.num_orders, 3)

    @override_settings(BLUELIGHT_IGNORED_ORDER_STATUSES=["Canceled", "Retired"])
    def test_recalculate_offer_application_totals_with_no_orders(self):
        self.offer.total_discount = D("15.00")
        self.offer.num_applications = 8
        self.offer.num_orders = 4
        self.offer.save()

        # Run the recalculation method
        ConditionalOffer.recalculate_offer_application_totals()

        # Get the most recent object of this offer to check the update query is executed correctly
        offer = ConditionalOffer.objects.get(pk=self.offer.pk)

        # Total discount should be updated as 1.00 + 2.00 + 3.00 = 6.00
        # The last two discount amounts, 4.00 and 5.00, should not be counted since their orders statuses exist in BLUELIGHT_IGNORED_ORDER_STATUSES
        self.assertEqual(offer.total_discount, D("0.00"))
        # Number of applications should be updated as the sum of the order discounts' frequency values: 1 + 2 + 3 = 6
        # The last two number of applications, 1.00 and 2.00, should not be counted since their orders statuses exist in BLUELIGHT_IGNORED_ORDER_STATUSES
        self.assertEqual(offer.num_applications, 0)
        # Number of orders should be updated as the count of the distinct orders
        # having a relation to the discounts that apply this offer: 3 distinct orders
        # The last two discounts' orders should not be counted since their orders statuses exist in BLUELIGHT_IGNORED_ORDER_STATUSES
        self.assertEqual(offer.num_orders, 0)

from datetime import UTC, datetime
from decimal import Decimal as D
from typing import Any

from django.contrib.auth.models import User
from django.db import connection
from django.test import TransactionTestCase
from django.test.utils import CaptureQueriesContext
from django_redis import get_redis_connection
from oscar.core.loading import get_class, get_model
from oscar.test.factories import create_product

from oscarbluelight.offer.applicator import Applicator
from oscarbluelight.offer.constants import Conjunction
from oscarbluelight.offer.models import (
    Benefit,
    CompoundCondition,
    Condition,
    ConditionalOffer,
    OfferGroup,
    Range,
)
from oscarbluelight.voucher.models import Voucher

Basket = get_model("basket", "Basket")
Selector = get_class("partner.strategy", "Selector")

COND = "oscarbluelight.offer.conditions."
BEN = "oscarbluelight.offer.benefits."

SCENARIOS: list[tuple[str, list[tuple[str, int]], bool]] = [
    ("1 line in A", [("a1", 3)], False),
    ("1 line in A, voucher", [("a1", 3)], True),
    ("1 line outside ranges, voucher", [("x", 1)], True),
    ("1 line non-discountable", [("nd", 2)], False),
    ("2 lines A and B", [("a2", 1), ("b1", 2)], False),
    ("2 lines overlap and outside, voucher", [("ab", 2), ("x", 1)], True),
    ("3 lines mixed, voucher", [("a1", 2), ("b1", 1), ("x", 1)], True),
    ("3 lines all in ranges", [("ab", 2), ("a2", 1), ("b1", 1)], False),
]

EXPECTED: dict[str, Any] = {
    "1 line in A": {
        "lines": [
            {
                "product": "Product A1",
                "quantity": 3,
                "discount": "3.00",
                "price_excl_tax_incl_discounts": "27.00",
                "discounts": [("3.00", "Two from A", None)],
                "breakdown": [("9.00", 3)],
            }
        ],
        "applications": [("Two from A", 1, "3.00", None)],
        "upsells": [
            " or  to qualify for the A or B and coverage special offer.",
            " to qualify for the Tax-inclusive 60 special offer.",
            "Buy 1 more product from Everything to qualify for the Deep nest special offer.",
        ],
        "total_excl_tax": "27.00",
        "total_excl_tax_excl_discounts": "30.00",
    },
    "1 line in A, voucher": {
        "lines": [
            {
                "product": "Product A1",
                "quantity": 3,
                "discount": "4.35",
                "price_excl_tax_incl_discounts": "25.65",
                "discounts": [
                    ("3.00", "Two from A", None),
                    ("1.35", "Voucher offer", "SAVE5"),
                ],
                "breakdown": [("8.55", 3)],
            }
        ],
        "applications": [
            ("Two from A", 1, "3.00", None),
            ("Voucher offer", 1, "1.35", "SAVE5"),
        ],
        "upsells": [
            " or  to qualify for the A or B and coverage special offer.",
            " to qualify for the Tax-inclusive 60 special offer.",
            "Buy 1 more product from Everything to qualify for the Deep nest special offer.",
        ],
        "total_excl_tax": "25.65",
        "total_excl_tax_excl_discounts": "30.00",
    },
    "1 line outside ranges, voucher": {
        "lines": [
            {
                "product": "Product X",
                "quantity": 1,
                "discount": "0.00",
                "price_excl_tax_incl_discounts": "100.00",
                "discounts": [],
                "breakdown": [("100.00", 1)],
            }
        ],
        "applications": [],
        "upsells": [
            "Buy 1 more product from Everything to qualify for the Deep nest special offer."
        ],
        "total_excl_tax": "100.00",
        "total_excl_tax_excl_discounts": "100.00",
    },
    "1 line non-discountable": {
        "lines": [
            {
                "product": "Product ND",
                "quantity": 2,
                "discount": "0.00",
                "price_excl_tax_incl_discounts": "60.00",
                "discounts": [],
                "breakdown": [("30.00", 2)],
            }
        ],
        "applications": [],
        "upsells": [],
        "total_excl_tax": "60.00",
        "total_excl_tax_excl_discounts": "60.00",
    },
    "2 lines A and B": {
        "lines": [
            {
                "product": "Product A2",
                "quantity": 1,
                "discount": "5.00",
                "price_excl_tax_incl_discounts": "20.00",
                "discounts": [("5.00", "A and B", None)],
                "breakdown": [("20.00", 1)],
            },
            {
                "product": "Product B1",
                "quantity": 2,
                "discount": "51.00",
                "price_excl_tax_incl_discounts": "29.00",
                "discounts": [
                    ("5.00", "Spend 50 on B", None),
                    ("15.00", "A and B", None),
                    ("2.00", "Tax-inclusive 60", None),
                    ("29.00", "Deep nest", None),
                ],
                "breakdown": [("0.00", 1), ("29.00", 1)],
            },
        ],
        "applications": [
            ("Spend 50 on B", 1, "5.00", None),
            ("A and B", 1, "20.00", None),
            ("Tax-inclusive 60", 1, "2.00", None),
            ("Deep nest", 1, "29.00", None),
        ],
        "upsells": [
            " to qualify for the Tax-inclusive 60 special offer.",
            "Buy 1 more product from Everything to qualify for the Deep nest special offer.",
            "Buy 1 more product from Range A to qualify for the Two from A special offer.",
        ],
        "total_excl_tax": "49.00",
        "total_excl_tax_excl_discounts": "105.00",
    },
    "2 lines overlap and outside, voucher": {
        "lines": [
            {
                "product": "Product AB",
                "quantity": 2,
                "discount": "11.38",
                "price_excl_tax_incl_discounts": "18.62",
                "discounts": [
                    ("3.00", "Two from A", None),
                    ("5.40", "A and B", None),
                    ("2.00", "Tax-inclusive 60", None),
                    ("0.98", "Voucher offer", "SAVE5"),
                ],
                "breakdown": [("9.31", 2)],
            },
            {
                "product": "Product X",
                "quantity": 1,
                "discount": "5.00",
                "price_excl_tax_incl_discounts": "95.00",
                "discounts": [("5.00", "Voucher offer", "SAVE5")],
                "breakdown": [("95.00", 1)],
            },
        ],
        "applications": [
            ("Two from A", 1, "3.00", None),
            ("A and B", 1, "5.40", None),
            ("Tax-inclusive 60", 1, "2.00", None),
            ("Voucher offer", 1, "5.98", "SAVE5"),
        ],
        "upsells": [" to qualify for the Deep nest special offer."],
        "total_excl_tax": "113.62",
        "total_excl_tax_excl_discounts": "130.00",
    },
    "3 lines mixed, voucher": {
        "lines": [
            {
                "product": "Product A1",
                "quantity": 2,
                "discount": "12.80",
                "price_excl_tax_incl_discounts": "7.20",
                "discounts": [
                    ("2.00", "Two from A", None),
                    ("3.60", "A and B", None),
                    ("7.20", "Deep nest", None),
                ],
                "breakdown": [("0.00", 1), ("7.20", 1)],
            },
            {
                "product": "Product B1",
                "quantity": 1,
                "discount": "10.00",
                "price_excl_tax_incl_discounts": "30.00",
                "discounts": [
                    ("8.00", "A and B", None),
                    ("2.00", "Tax-inclusive 60", None),
                ],
                "breakdown": [("30.00", 1)],
            },
            {
                "product": "Product X",
                "quantity": 1,
                "discount": "0.00",
                "price_excl_tax_incl_discounts": "100.00",
                "discounts": [],
                "breakdown": [("100.00", 1)],
            },
        ],
        "applications": [
            ("Two from A", 1, "2.00", None),
            ("A and B", 1, "11.60", None),
            ("Tax-inclusive 60", 1, "2.00", None),
            ("Deep nest", 1, "7.20", None),
        ],
        "upsells": [
            " to qualify for the Spend 50 on B special offer.",
            " to qualify for the Tax-inclusive 60 special offer.",
            "Buy 1 more product from Everything to qualify for the Deep nest special offer.",
        ],
        "total_excl_tax": "137.20",
        "total_excl_tax_excl_discounts": "160.00",
    },
    "3 lines all in ranges": {
        "lines": [
            {
                "product": "Product AB",
                "quantity": 2,
                "discount": "9.20",
                "price_excl_tax_incl_discounts": "20.80",
                "discounts": [
                    ("3.00", "Two from A", None),
                    ("5.40", "A and B", None),
                    ("0.80", "Tax-inclusive 60", None),
                ],
                "breakdown": [("10.40", 2)],
            },
            {
                "product": "Product A2",
                "quantity": 1,
                "discount": "25.00",
                "price_excl_tax_incl_discounts": "0",
                "discounts": [
                    ("2.50", "Two from A", None),
                    ("4.50", "A and B", None),
                    ("18.00", "Deep nest", None),
                ],
                "breakdown": [("0.00", 1)],
            },
            {
                "product": "Product B1",
                "quantity": 1,
                "discount": "9.20",
                "price_excl_tax_incl_discounts": "30.80",
                "discounts": [
                    ("8.00", "A and B", None),
                    ("1.20", "Tax-inclusive 60", None),
                ],
                "breakdown": [("30.80", 1)],
            },
        ],
        "applications": [
            ("Two from A", 1, "5.50", None),
            ("A and B", 1, "17.90", None),
            ("Tax-inclusive 60", 1, "2.00", None),
            ("Deep nest", 1, "18.00", None),
        ],
        "upsells": [
            " to qualify for the Spend 50 on B special offer.",
            "Buy 1 more product from Everything to qualify for the Deep nest special offer.",
        ],
        "total_excl_tax": "51.60",
        "total_excl_tax_excl_discounts": "95.00",
    },
}

EXPECTED_DESCRIPTIONS: dict[str, Any] = {
    "Two from A": (
        "Cart includes 2 item(s) from range a",
        'Cart includes 2 item(s) from <a href="/dashboard/ranges/1/">Range A</a>',
        '10.00% discount on <a href="/dashboard/ranges/1/">Range A</a>, maximum 3 items',
    ),
    "Spend 50 on B": (
        "Basket includes $50.00 (tax-exclusive) from range b",
        'Basket includes $50.00 (tax-exclusive) from <a href="/dashboard/ranges/2/">Range B</a>',
        '$5.00 discount on <a href="/dashboard/ranges/2/">Range B</a>, no maximum',
    ),
    "A and B": (
        "Cart includes 1 item(s) from range a and Cart includes 1 item(s) from range b",
        "Cart includes 1 item(s) from range a and Cart includes 1 item(s) from range b",
        '20.00% discount on <a href="/dashboard/ranges/3/">Range C</a>, no maximum',
    ),
    "A or B and coverage": (
        "Basket includes $30.00 (tax-exclusive) from range a or Cart includes 1 item(s) from range b and Cart includes 2 distinct item(s) from range c",
        "Basket includes $30.00 (tax-exclusive) from range a or Cart includes 1 item(s) from range b and Cart includes 2 distinct item(s) from range c",
        '$3.00 discount on <a href="/dashboard/ranges/4/">Everything</a>, no maximum',
    ),
    "Tax-inclusive 60": (
        "Basket includes $60.00 (tax-inclusive) from everything",
        'Basket includes $60.00 (tax-inclusive) from <a href="/dashboard/ranges/4/">Everything</a>',
        '$2.00 discount on <a href="/dashboard/ranges/2/">Range B</a>, no maximum',
    ),
    "Deep nest": (
        "Cart includes 2 distinct item(s) from everything and Cart includes 3 item(s) from range a or Basket includes $20.00 (tax-exclusive) from range b and Cart includes 1 item(s) from range c",
        "Cart includes 2 distinct item(s) from everything and Cart includes 3 item(s) from range a or Basket includes $20.00 (tax-exclusive) from range b and Cart includes 1 item(s) from range c",
        'Second most expensive product from <a href="/dashboard/ranges/3/">Range C</a> is free',
    ),
    "Voucher offer": (
        "Cart includes 1 item(s) from range c",
        'Cart includes 1 item(s) from <a href="/dashboard/ranges/3/">Range C</a>',
        '5.00% discount on <a href="/dashboard/ranges/4/">Everything</a>, no maximum',
    ),
}


class OfferApplicationRegressionTest(TransactionTestCase):
    """
    Pins the discounts a fixed offer catalogue gives a set of baskets, so that
    changes to how offers are evaluated can't silently change what customers pay.
    """

    # Offer descriptions link to ranges by pk.
    reset_sequences = True

    def setUp(self) -> None:
        get_redis_connection("redis").flushall()
        OfferGroup.objects.all().delete()
        self.user = User.objects.create_user(username="shopper", password="x")

        self.products = {}
        for key, price, discountable in [
            ("a1", "10.00", True),
            ("a2", "25.00", True),
            ("b1", "40.00", True),
            ("ab", "15.00", True),
            ("x", "100.00", True),
            ("nd", "30.00", False),
        ]:
            self.products[key] = create_product(
                title=f"Product {key.upper()}",
                price=D(price),
                num_in_stock=100,
                is_discountable=discountable,
            )

        range_a = Range.objects.create(name="Range A")
        for key in ("a1", "a2", "ab", "nd"):
            range_a.add_product(self.products[key])
        range_b = Range.objects.create(name="Range B")
        for key in ("b1", "ab"):
            range_b.add_product(self.products[key])
        range_c = Range.objects.create(name="Range C", includes_all_products=True)
        range_c.excluded_products.add(self.products["x"])
        everything = Range.objects.create(name="Everything", includes_all_products=True)

        primary = OfferGroup.objects.create(name="Primary Offers", priority=30)
        secondary = OfferGroup.objects.create(name="Secondary Offers", priority=20)
        post_tax = OfferGroup.objects.create(
            name="post-tax-offers", priority=10, is_system_group=True
        )

        def cond(kind: str, rng: Range, value: str) -> Condition:
            return Condition.objects.create(
                proxy_class=COND + kind, range=rng, value=D(value)
            )

        def compound(conjunction: str, *children: Condition) -> CompoundCondition:
            c = CompoundCondition.objects.create(conjunction=conjunction)
            c.subconditions.set(children)
            return c

        def benefit(
            kind: str,
            rng: Range | None,
            value: str | None,
            max_affected_items: int | None = None,
        ) -> Benefit:
            return Benefit.objects.create(
                proxy_class=BEN + kind,
                range=rng,
                value=D(value) if value else None,
                max_affected_items=max_affected_items,
            )

        def offer(
            name: str,
            condition: Condition,
            benefit: Benefit,
            priority: int,
            group: OfferGroup | None,
            offer_type: str = ConditionalOffer.SITE,
        ) -> ConditionalOffer:
            return ConditionalOffer.objects.create(
                name=name,
                condition=condition,
                benefit=benefit,
                priority=priority,
                offer_group=group,
                offer_type=offer_type,
            )

        offer(
            "Two from A",
            cond("BluelightCountCondition", range_a, "2"),
            benefit("BluelightPercentageDiscountBenefit", range_a, "10", 3),
            5,
            primary,
        )
        offer(
            "Spend 50 on B",
            cond("BluelightValueCondition", range_b, "50"),
            benefit("BluelightAbsoluteDiscountBenefit", range_b, "5"),
            3,
            primary,
        )
        offer(
            "A and B",
            compound(
                Conjunction.AND,
                cond("BluelightCountCondition", range_a, "1"),
                cond("BluelightCountCondition", range_b, "1"),
            ),
            benefit("BluelightPercentageDiscountBenefit", range_c, "20"),
            5,
            secondary,
        )
        offer(
            "A or B and coverage",
            compound(
                Conjunction.OR,
                cond("BluelightValueCondition", range_a, "30"),
                compound(
                    Conjunction.AND,
                    cond("BluelightCountCondition", range_b, "1"),
                    cond("BluelightCoverageCondition", range_c, "2"),
                ),
            ),
            benefit("BluelightAbsoluteDiscountBenefit", everything, "3"),
            3,
            secondary,
        )
        offer(
            "Tax-inclusive 60",
            cond("BluelightTaxInclusiveValueCondition", everything, "60"),
            benefit("BluelightAbsoluteDiscountBenefit", range_b, "2"),
            1,
            post_tax,
        )
        offer(
            "Deep nest",
            compound(
                Conjunction.AND,
                cond("BluelightCoverageCondition", everything, "2"),
                compound(
                    Conjunction.OR,
                    cond("BluelightCountCondition", range_a, "3"),
                    compound(
                        Conjunction.AND,
                        cond("BluelightValueCondition", range_b, "20"),
                        cond("BluelightCountCondition", range_c, "1"),
                    ),
                ),
            ),
            benefit("BluelightMultibuyDiscountBenefit", range_c, None),
            2,
            None,
        )
        voucher_offer = offer(
            "Voucher offer",
            cond("BluelightCountCondition", range_c, "1"),
            benefit("BluelightPercentageDiscountBenefit", everything, "5"),
            1,
            None,
            ConditionalOffer.VOUCHER,
        )
        self.voucher = Voucher.objects.create(
            name="Save Five",
            code="SAVE5",
            usage=Voucher.MULTI_USE,
            start_datetime=datetime(2000, 1, 1, tzinfo=UTC),
            end_datetime=datetime(2100, 1, 1, tzinfo=UTC),
            limit_usage_by_group=False,
        )
        self.voucher.offers.add(voucher_offer)

    def _fresh_basket(self, items: list[tuple[str, int]], voucher: bool) -> Any:
        basket = Basket.objects.create(owner=self.user)
        basket.strategy = Selector().strategy()
        for key, qty in items:
            basket.add_product(self.products[key], quantity=qty)
        if voucher:
            basket.vouchers.add(self.voucher)
        basket = Basket.objects.get(pk=basket.pk)
        basket.strategy = Selector().strategy()
        return basket

    def _snapshot(self, basket: Any) -> dict[str, Any]:
        lines = [
            {
                "product": line.product.title,
                "quantity": line.quantity,
                "discount": str(line.discount_value),
                "price_excl_tax_incl_discounts": str(
                    line.line_price_excl_tax_incl_discounts
                ),
                "discounts": [
                    (str(d.amount), d.offer_name, d.voucher_code)
                    for d in line.get_discount_descriptions()
                ],
                "breakdown": (
                    [
                        (str(p.unit_price_excl_tax), p.quantity)
                        for p in line.get_price_breakdown()
                    ]
                    if line.is_tax_known
                    else None
                ),
            }
            for line in basket.all_lines()
        ]
        applications = [
            (
                a["name"],
                a["freq"],
                str(a["discount"]),
                a["voucher"].code if a["voucher"] else None,
            )
            for a in basket.offer_applications.applications.values()
        ]
        return {
            "lines": lines,
            "applications": applications,
            "upsells": sorted(str(u.get_summary()) for u in basket.get_offer_upsells()),
            "total_excl_tax": str(basket.total_excl_tax),
            "total_excl_tax_excl_discounts": str(basket.total_excl_tax_excl_discounts),
        }

    def test_applied_discounts(self) -> None:
        self.maxDiff = None
        actual = {}
        for name, items, voucher in SCENARIOS:
            basket = self._fresh_basket(items, voucher)
            Applicator().apply(basket, self.user)
            actual[name] = self._snapshot(basket)
        self.assertEqual(actual, EXPECTED)

    def test_offer_descriptions(self) -> None:
        self.maxDiff = None
        actual = {
            o.name: (
                str(o.condition.proxy().name),
                str(o.condition.proxy().description),
                str(o.benefit.proxy().description),
            )
            for o in ConditionalOffer.objects.order_by("pk")
        }
        self.assertEqual(actual, EXPECTED_DESCRIPTIONS)

    def test_range_edits_visible_on_next_apply(self) -> None:
        items = [("a1", 3)]
        basket = self._fresh_basket(items, False)
        Applicator().apply(basket, self.user)
        before = self._snapshot(basket)

        Range.objects.get(name="Range A").remove_product(self.products["a1"])

        basket = self._fresh_basket(items, False)
        Applicator().apply(basket, self.user)
        after = self._snapshot(basket)

        def offer_names(snapshot: dict[str, Any]) -> set[str]:
            return {d[1] for d in snapshot["lines"][0]["discounts"]}

        self.assertIn("Two from A", offer_names(before))
        self.assertNotIn("Two from A", offer_names(after))

    def test_condition_edits_visible_to_reused_offers(self) -> None:
        def applied(basket: Any) -> set[str]:
            return {a["name"] for a in basket.offer_applications.applications.values()}

        applicator = Applicator()
        basket = self._fresh_basket([("a1", 3)], False)
        offers = applicator.get_offers(basket, self.user)
        applicator.apply_offers(basket, offers)
        self.assertNotIn("A and B", applied(basket))

        compound = CompoundCondition.objects.get(offers__name="A and B")
        compound.subconditions.remove(
            *compound.subconditions.filter(range__name="Range B")
        )

        basket = self._fresh_basket([("a1", 3)], False)
        applicator.apply_offers(basket, offers)
        self.assertIn("A and B", applied(basket))

    def test_query_counts(self) -> None:
        for items, bound in [
            ([("a1", 3)], 23),
            ([("a2", 1), ("b1", 2)], 29),
            ([("a1", 2), ("b1", 1), ("x", 1)], 35),
        ]:
            basket = self._fresh_basket(items, True)
            with CaptureQueriesContext(connection) as ctx:
                Applicator().apply(basket, self.user)
            with self.subTest(num_lines=len(items)):
                self.assertLessEqual(len(ctx.captured_queries), bound)

from contextlib import contextmanager
from django.conf import settings
from django.core.cache import cache
from django.db import transaction
from django.db.models import Q
from django.utils.timezone import now
from itertools import groupby, chain
from oscar.apps.offer.applicator import Applicator as BaseApplicator
from oscar.core.loading import get_model
from oscar.apps.offer import results
from .signals import (
    pre_offers_apply,
    post_offers_apply,
    pre_offer_group_apply,
    post_offer_group_apply,
)
from ..caching import CacheNamespace, FluentCache


pricing_cache_ns = CacheNamespace(cache, "oscarbluelight.pricing")
cosmetic_price_cache = (
    FluentCache(cache, "oscarbluelight.applicator.cosmetic_price")
    .timeout(getattr(settings, "BLUELIGHT_COSMETIC_PRICE_CACHE_TTL", 86400))
    .namespaces(pricing_cache_ns)
    .key_parts("product", "quantity")
)


def group_offers(offers):
    # Figure out the priority for the "null-group", the implicit group of offers which don't belong to
    # any other group. This group is applied last, and is therefore given the lowest priority.
    offer_group_priorities = [
        o.offer_group.priority for o in offers if o.offer_group is not None
    ]
    min_offer_group_priority = (
        min(offer_group_priorities) if len(offer_group_priorities) else 0
    )
    null_group_priority = min_offer_group_priority - 1

    def get_offer_group_priority(offer):
        return offer.offer_group.priority if offer.offer_group else null_group_priority

    # Sort the list of offers by their offer group's priority, descending
    offers = sorted(
        offers, key=lambda offer: (-get_offer_group_priority(offer), -offer.priority)
    )

    # Group the sorted list by the offer group priority
    return groupby(offers, key=get_offer_group_priority)


class Applicator(BaseApplicator):
    _is_applying_cosmetic_prices = False
    _offer_select_related_fields = [
        "offer_group",
        "benefit",
        "benefit__range",
        "condition",
        "condition__range",
    ]

    def get_site_offers(self):
        ConditionalOffer = get_model("offer", "ConditionalOffer")
        qs = ConditionalOffer.active.filter(offer_type=ConditionalOffer.SITE)
        return qs.select_related(*self._offer_select_related_fields)

    def get_basket_offers(self, basket, user):
        offers = []
        if not basket.id or not user:
            return offers

        for voucher in basket.vouchers.all():
            available_to_user, __ = voucher.is_available_to_user(user=user)
            if voucher.is_active() and available_to_user:
                basket_offers = voucher.offers.select_related(
                    *self._offer_select_related_fields
                ).all()
                for offer in basket_offers:
                    offer.set_voucher(voucher)
                offers = list(chain(offers, basket_offers))
        return offers

    def get_user_offers(self, user):
        """
        Return user offers that are available to current user
        """
        if not user or user.is_anonymous:
            return []
        ConditionalOffer = get_model("offer", "ConditionalOffer")
        cutoff = now()
        date_based = Q(
            Q(start_datetime__lte=cutoff),
            Q(end_datetime__gte=cutoff) | Q(end_datetime=None),
        )
        nondate_based = Q(start_datetime=None, end_datetime=None)
        groups = [g for g in user.groups.all()]

        qs = ConditionalOffer.objects.filter(
            date_based | nondate_based,
            offer_type=ConditionalOffer.USER,
            groups__in=groups,
            status=ConditionalOffer.OPEN,
        )
        return qs.select_related(*self._offer_select_related_fields)

    def get_session_offers(self, request):
        return []

    def apply_offers(self, basket, offers):
        """
        Apply offers to the basket in priority order

        Group the given flat list of offers into groups based on their offer group. Then, apply
        the offers in order of (1) offer group priority and (2) offer priority. Within each group,
        an item in a line is limited to being consumed by a single offer, but this limitation is
        reset for each group. This makes it possible to apply multiple offers to a single line item.
        """
        pre_offers_apply.send(sender=self.__class__, basket=basket, offers=offers)
        applications = results.OfferApplications()

        # If this is a cosmetic application, filter out offers that shouldn't apply.
        if self._is_applying_cosmetic_prices:
            offers = [offer for offer in offers if offer.affects_cosmetic_pricing]

        for group_priority, offers_in_group in group_offers(offers):
            # Get the OfferGroup object from the list of offers
            offers_in_group = list(offers_in_group)
            group = offers_in_group[0].offer_group if len(offers_in_group) > 0 else None

            # Signal the lines that we're about to start applying an offer group
            pre_offer_group_apply.send(
                sender=self.__class__,
                basket=basket,
                group=group,
                offers=offers_in_group,
            )
            for line in basket.all_lines():
                line.begin_offer_group_application()

            # Apply each offer in the group
            for offer in offers_in_group:
                num_applications = 0
                # Keep applying the offer until either
                # (a) We reach the max number of applications for the offer.
                # (b) The benefit can't be applied successfully.
                max_applications = offer.get_max_applications(basket.owner)
                while num_applications < max_applications:
                    result = offer.apply_benefit(basket)
                    num_applications += 1
                    if not result.is_successful:
                        break
                    applications.add(offer, result)
                    if result.is_final:
                        break

            # Signal the lines that we've finished applying an offer group
            for line in basket.all_lines():
                line.end_offer_group_application()
            post_offer_group_apply.send(
                sender=self.__class__,
                basket=basket,
                group=group,
                offers=offers_in_group,
            )

        # Signal the lines that we've finished applying all offer groups
        for line in basket.all_lines():
            line.finalize_offer_group_applications()

        # Store this list of discounts with the basket so it can be rendered in templates
        basket.offer_applications = applications
        post_offers_apply.send(sender=self.__class__, basket=basket, offers=offers)

    @contextmanager
    def _cosmetic_pricing(self):
        self._is_applying_cosmetic_prices = True
        try:
            yield
        finally:
            self._is_applying_cosmetic_prices = False

    def get_cosmetic_price(self, strategy, product, quantity=1):
        price_cache = cosmetic_price_cache.concrete(
            product=product.pk, quantity=quantity
        )

        def _inner():
            Basket = get_model("basket", "Basket")
            # Calculate the price by simulating adding the product to the basket and comparing
            # the basket's total price before and after the new line item
            total_excl_tax_before = None
            total_excl_tax_after = None
            try:
                with transaction.atomic():
                    with self._cosmetic_pricing():
                        basket = Basket()
                        basket.strategy = strategy
                        # Capture the total_excl_tax before altering the basket line
                        total_excl_tax_before = basket.total_excl_tax
                        # Add the product to the basket and re-apply offers and coupons.
                        line, _ = basket.add_product(product, quantity=quantity)
                        self.apply(basket)
                        # Get the price difference
                        total_excl_tax_after = basket.total_excl_tax
                    # Intentionally rollback the transaction to that the line item isn't actually saved
                    raise RuntimeError("rollback")
            except RuntimeError:
                pass
            # Use the before/after price difference to calculate the unit price for the product
            unit_cosmetic_excl_tax = (
                total_excl_tax_after - total_excl_tax_before
            ) / quantity
            return unit_cosmetic_excl_tax

        return price_cache.get_or_set(_inner)

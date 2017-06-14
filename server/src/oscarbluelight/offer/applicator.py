from django.db.models import Q
from django.utils.timezone import now
from itertools import groupby
from oscar.apps.offer.applicator import Applicator as BaseApplicator
from oscar.core.loading import get_model
from oscar.apps.offer import results

ConditionalOffer = get_model('offer', 'ConditionalOffer')
OfferGroup = get_model('offer', 'OfferGroup')



def group_offers(offers):
    # Figure out the priority for the "null-group", the implicit group of offers which don't belong to
    # any other group. This group is applied last, and is therefore given the lowest priority.
    offer_group_priorities = [o.offer_group.priority for o in offers if o.offer_group is not None]
    min_offer_group_priority = min(offer_group_priorities) if len(offer_group_priorities) else 0
    null_group_priority = min_offer_group_priority - 1

    def get_offer_group_priority(offer):
        return offer.offer_group.priority if offer.offer_group else null_group_priority

    # Sort the list of offers by their offer group's priority, descending
    offers = sorted(offers, key=lambda offer: (-get_offer_group_priority(offer), -offer.priority))

    # Group the sorted list by the offer group priority
    return groupby(offers, key=get_offer_group_priority)



class Applicator(BaseApplicator):
    def get_user_offers(self, user):
        """
        Return user offers that are available to current user
        """
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
            status=ConditionalOffer.OPEN)
        return qs.select_related('condition', 'benefit')


    def apply_offers(self, basket, offers):
        """
        Apply offers to the basket in priority order

        Group the given flat list of offers into groups based on their offer_group_id. Then, apply
        the offers in order of (1) offer group priority and (2) offer priority. Within each group,
        an item in a line is limited to being consumed by a single offer, but this limitation is
        reset for each group. This makes it possible to apply multiple offers to a single line item.
        """
        applications = results.OfferApplications()

        for group_id, group in group_offers(offers):
            # Signal the lines that we're about to start applying an offer group
            for line in basket.all_lines():
                line.begin_offer_group_application()

            # Apply each offer in the group
            for offer in group:
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

        # Signal the lines that we've finished applying all offer groups
        for line in basket.all_lines():
            line.finalize_offer_group_applications()

        # Store this list of discounts with the basket so it can be rendered in templates
        basket.offer_applications = applications


    def get_cosmetic_price(self, product, price_excl_tax):
        offers = ConditionalOffer.active.filter(apply_to_displayed_prices=True).all()
        for group_id, group in group_offers(offers):
            for offer in group:
                benefit = offer.benefit.proxy()
                rng = benefit.range
                if not rng:
                    continue
                if not rng.contains_product(product):
                    continue
                if not hasattr(benefit, 'apply_cosmetic_discount'):
                    continue
                price_excl_tax = benefit.apply_cosmetic_discount(price_excl_tax)
        return price_excl_tax

from django.db.models import Q
from django.utils.timezone import now
from itertools import groupby
from oscar.apps.offer.applicator import Applicator as BaseApplicator
from oscar.core.loading import get_model
from oscar.apps.offer import results
from collections import Counter
from itertools import chain

ConditionalOffer = get_model('offer', 'ConditionalOffer')
OfferGroup = get_model('offer', 'OfferGroup')


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
        '''
        Want to apply offers within offer group
        when offer group's offers applied, move to the next offer group
        with offers
        have to reset affected quanity to 0 per offergroup
        '''
        affected_quantities = Counter()
        offer_group = OfferGroup.objects.all()
        applications = results.OfferApplications()

        max_offer_group_priority = max([o.offer_group_id for o in offers if o.offer_group_id is not None])
        offers = sorted(offers, key=lambda s: s.offer_group_id or max_offer_group_priority + 1)
        grouped_offers = groupby(offers, key=lambda s: s.offer_group_id)

        for group_id, group in grouped_offers:
            for offer in group:
                num_applications = 0
                # Keep applying the offer until either
                # (a) We reach the max number of applications for the offer.
                # (b) The benefit can't be applied successfully.
                while num_applications < offer.get_max_applications(basket.owner):
                    result = offer.apply_benefit(basket)
                    num_applications += 1
                    if not result.is_successful:
                        break
                    applications.add(offer, result)
                    if result.is_final:
                        break
                for line in basket.all_lines():
                    affected_quantities[line.id] += line._affected_quantity
                    # want affected lines per offer group, not globally
                    line._affected_quantity = 0

        for line in basket.all_lines():
            line._affected_quantity = min(line.quantity, affected_quantities[line.id])


        # Store this list of discounts with the basket so it can be
        # rendered in templates

        basket.offer_applications = applications

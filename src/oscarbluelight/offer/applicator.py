from django.db.models import Q, Max, Min
from django.utils.timezone import now
from oscar.apps.offer.applicator import Applicator as BaseApplicator
from oscar.core.loading import get_model
from collections import defaultdict

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
        '''
        offer_groups = OfferGroup.objects.all()
        applications = results.OfferApplications()

        for offer_group in offer_groups:
            for offer in offer_group.offers & offers:
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

        # Store this list of discounts with the basket so it can be
        # rendered in templates
        basket.offer_applications = applications


        # applicable_offers = set()
        # p = defaultdict(list)
        # cutoff = now()
        # date_based = Q(
        #     Q(start_datetime__lte=cutoff),
        #     Q(end_datetime__gte=cutoff) | Q(end_datetime=None),
        # )
        # nondate_based = Q(start_datetime=None, end_datetime=None)

        # # get all offers that are open, with valid date, that have an offer group
        # qs = ConditionalOffer.objects.filter(
        #     date_based | nondate_based,
        #     status=ConditionalOffer.OPEN, offer_group__isnull=False)  # .order_by('priority')

        # # all those offers, but excude given offer's offer group
        # offers = qs.exclude(offer_group=this_offer.offer_group).order_by('priority')

        # min_og_pri = OfferGroup.objects.aggregate(Min('priority'))

        # for elem in qs:
        #     p[elem.priority].append(elem.name)

        # seq = sorted(p.keys())
        # for other_offer in offers:
        #     if offer.offer_group == other_offers.offer_group and other_offers.offer_group.priority == min_og_pri:
        #         applicable_offers.add(other_offer)
        #     elif ( offer.offer_group.offers.count() == 1 and other_offers.offer_group.offers.count() == 1):
        #         if (offer.offer_group.priority, other_offers.offer_group.priority) in zip(seq[:-1], seq[1:]) or \
        #                 (other_offer.offer_group.priority, offer.offer_group.priority) in zip(seq[:-1], seq[1:]):
        #                 applicable_offers.add(other_offer)
        # return applicable_offers

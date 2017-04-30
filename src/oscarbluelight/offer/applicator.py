from django.db.models import Q, Max, Min
from django.utils.timezone import now
from oscar.apps.offer.applicator import Applicator as BaseApplicator
from oscar.core.loading import get_model
# from oscarbluelight.utils.ordered_set import OrderedSet
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


def get_applicaple_offers(offer1, offer2):
    '''
    if either offer is NOT in higest priority og -> error
    use offer_x iff
        offer_y in same og and og has min priority
        OR offer_x only offer in OG AND offer_y in NEXT priority og
    '''
    p = defaultdict(list)
    cutoff = now()
    date_based = Q(
        Q(start_datetime__lte=cutoff),
        Q(end_datetime__gte=cutoff) | Q(end_datetime=None),
    )
    nondate_based = Q(start_datetime=None, end_datetime=None)

    qs = ConditionalOffer.objects.filter(
        date_based | nondate_based,
        status=ConditionalOffer.OPEN, offer_group__isnull=False).order_by('priority')
    cos = qs.filter(Q(offer_group=offer1.offer_group) | Q(offer_group=offer2.offer_group)).order_by('priority')

    min_og_pri = OfferGroup.objects.aggregate(Min('priority'))

    # Select priority from offer_groups order by priority

    for elem in qs:
        p[elem.priority].append(elem.name)

    seq = sorted(p.keys())
    idx = 0
    if offer1.offer_group == offer2.offer_group and offer2.offer_group.priority == min_og_pri:
        return True

    if offer1 in cos and offer2 in cos:
        if ( offer1.offer_group.offers.count() == 1 or offer2.offer_group.offers.count() == 1):
            if (offer1.offer_group.priority, offer2.offer_group.priority) in zip(seq[:-1], seq[1:]) or \
                    (offer2.offer_group.priority, offer1.offer_group.priority) in zip(seq[:-1], seq[1:]):
                return True
    else:
        return False

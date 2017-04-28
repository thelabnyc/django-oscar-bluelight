from django.db.models import Q
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
    restrict usage to offers in available highest priority
    offergroup
    '''
    priorities = defaultdict(list)
    cutoff = now()
    date_based = Q(
        Q(start_datetime__lte=cutoff),
        Q(end_datetime__gte=cutoff) | Q(end_datetime=None),
    )
    nondate_based = Q(start_datetime=None, end_datetime=None)

    qs = ConditionalOffer.objects.filter(
        date_based | nondate_based,
        status=ConditionalOffer.OPEN)
    ogs = OfferGroup.objects.filter(offers__in=[offer1, offer2]).order_by('priority')

    for og in ogs:
        priorities[og.priority].extend(og.offers.all())

    return priorities

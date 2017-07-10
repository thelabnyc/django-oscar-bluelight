from oscar.apps.basket.abstract_models import AbstractLine
from oscarbluelight.mixins import BluelightBasketLineMixin
from oscarbluelight.offer.groups import register_system_offer_group

# Create a system offer group for post-tax offers. Then we'll use signals to
# make sure tax is applied before this offer group's offers are evaluated.
OFFER_GROUP_POST_TAX_OFFERS = register_system_offer_group('post-tax-offers')


class Line(BluelightBasketLineMixin, AbstractLine):
    pass


from oscar.apps.basket.models import *  # noqa

from oscar.apps.basket.abstract_models import AbstractLine
from oscarbluelight.mixins import BluelightBasketLineMixin


class Line(BluelightBasketLineMixin, AbstractLine):
    pass


from oscar.apps.basket.models import *  # noqa

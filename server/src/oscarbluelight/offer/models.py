from django.conf import settings
from django.core import exceptions
from django.db import models, IntegrityError
from django.utils.translation import ugettext_lazy as _
from oscar.apps.offer.abstract_models import (
    AbstractBenefit,
    AbstractCondition,
    AbstractConditionalOffer,
    AbstractRange,
    AbstractRangeProduct,
    AbstractRangeProductFileUpload
)
from oscar.apps.offer.results import (
    SHIPPING_DISCOUNT,
    ZERO_DISCOUNT,
    BasketDiscount,
    PostOrderAction,
    ShippingDiscount
)
from oscar.apps.offer.utils import load_proxy
import copy
import logging

logger = logging.getLogger(__name__)


def _init_proxy_class(obj, Klass):
    # Check if we're already the correct class
    if obj.__class__ == Klass:
        return obj

    # Check if we're using multi-table inheritance
    model_name = Klass._meta.model_name
    if hasattr(obj, model_name):
        return getattr(obj, model_name)

    # Else, it's just a proxy model
    proxy = copy.deepcopy(obj)
    proxy.__class__ = Klass
    return proxy


class OfferGroup(models.Model):
    """
    Ordered group of Offers
    """
    name = models.CharField(max_length=64, null=False)
    priority = models.IntegerField(null=False, unique=True)

    class Meta:
        verbose_name = _('OfferGroup')
        ordering = ('-priority', )

    def __str__(self):
        return '{} (priority {})'.format(self.name, self.priority)


class ConditionalOffer(AbstractConditionalOffer):
    """
    groups  -- user groups
    offer_group -- FK to OfferGroup
    offerGroupA => [ o1, v2, o3 ], priority 1
    offerGroupB => [ o4, v3 ], priority 2
    To consume offers, loop through offers in offer group based on priority
    to consume OfferGroup -> only move to next (greater priority val) when previous
    offerGroup is consumed
    """
    short_name = models.CharField(
        _("Short Name"), max_length=50,
        help_text=_("Abbreviated version of offer name"))

    # When offer_type == "User", we use groups to determine which users get the offer
    groups = models.ManyToManyField('auth.Group', verbose_name=_("User Groups"), blank=True)
    offer_group = models.ForeignKey(OfferGroup, related_name='offers', null=True)
    apply_to_displayed_prices = models.BooleanField(default=False,
        help_text=_("If enabled, cosmetic product prices displayed on product display pages will be discounted by this offer’s benefit."))

    class Meta:
        ordering = ('-offer_group__priority', '-priority', 'pk')

    def availability_restrictions(self):
        restrictions = super().availability_restrictions()
        if self.offer_type == self.USER:
            restrictions.append({
                'description': _("Offer is limited to user groups: %s") % ', '.join(g.name for g in self.groups.all()),
                'is_satisfied': True,
            })
        return restrictions

    def apply_benefit(self, basket):
        try:
            return super().apply_benefit(basket)
        except exceptions.ValidationError as e:
            logger.exception(e)
            return ZERO_DISCOUNT


class Benefit(AbstractBenefit):
    def proxy(self):
        if self.proxy_class:
            Klass = load_proxy(self.proxy_class)
            return _init_proxy_class(self, Klass)
        return super().proxy()

    # TODO: Compatibility Hack. Remove once Oscar 1.5 is minimum supported version.
    # In Oscar 1.5, they added a related name to this relationship. So what was
    # ``conditionaloffer_set`` became ``offers``. This is a hack to make calls to ``offers``
    # work in Oscar 1.3 and 1.4. In Oscar 1.5, Django's model metaclass overrides this so that
    # it never gets called.
    @property
    def offers(self):
        return self.conditionaloffer_set
    # END TEMP

    @property
    def type_name(self):
        benefit_classes = getattr(settings, 'BLUELIGHT_BENEFIT_CLASSES', [])
        names = dict(benefit_classes)
        return names.get(self.proxy_class, self.proxy_class)

    @property
    def non_voucher_offers(self):
        return self.offers.exclude(offer_type=ConditionalOffer.VOUCHER).all()

    @property
    def vouchers(self):
        vouchers = []
        for offer in self.offers.filter(offer_type=ConditionalOffer.VOUCHER).all():
            for voucher in offer.vouchers.filter(parent=None).all():
                vouchers.append(voucher)
        return vouchers

    def clean(self):
        if self.type:
            raise exceptions.ValidationError(_("Benefit should not have a type field. Use proxy class instead."))
        proxy_instance = self.proxy()
        cleaner = getattr(proxy_instance, '_clean', None)
        if cleaner and callable(cleaner):
            return cleaner()
        return super().clean()

    def save(self, *args, **kwargs):
        ret = super().save(*args, **kwargs)
        # If the elected proxy_class isn't a proxy model, it has it's own table where a row needs to exist.
        if self.proxy_class:
            Klass = load_proxy(self.proxy_class)
            if self.__class__ != Klass and not Klass._meta.proxy and not Klass.objects.filter(pk=self.pk).exists():
                proxy = copy.deepcopy(self)
                proxy.__class__ = Klass
                proxy.save()
        return ret


class Condition(AbstractCondition):
    def proxy(self):
        if self.proxy_class:
            Klass = load_proxy(self.proxy_class)
            return _init_proxy_class(self, Klass)
        return super().proxy()

    # TODO: Compatibility Hack. Remove once Oscar 1.5 is minimum supported version.
    # In Oscar 1.5, they added a related name to this relationship. So what was
    # ``conditionaloffer_set`` became ``offers``. This is a hack to make calls to ``offers``
    # work in Oscar 1.3 and 1.4. In Oscar 1.5, Django's model metaclass overrides this so that
    # it never gets called.
    @property
    def offers(self):
        return self.conditionaloffer_set
    # END TEMP

    @property
    def type_name(self):
        condition_classes = getattr(settings, 'BLUELIGHT_CONDITION_CLASSES', [])
        names = dict(condition_classes)
        names['oscarbluelight.offer.conditions.CompoundCondition'] = _("Compound condition")
        return names.get(self.proxy_class, self.proxy_class)

    @property
    def non_voucher_offers(self):
        return self.offers.exclude(offer_type=ConditionalOffer.VOUCHER).all()

    @property
    def vouchers(self):
        vouchers = []
        for offer in self.offers.filter(offer_type=ConditionalOffer.VOUCHER).all():
            for voucher in offer.vouchers.filter(parent=None).all():
                vouchers.append(voucher)
        return vouchers

    def clean(self):
        if self.type:
            raise exceptions.ValidationError(_("Condition should not have a type field. Use proxy class instead."))
        proxy_instance = self.proxy()
        cleaner = getattr(proxy_instance, '_clean', None)
        if cleaner and callable(cleaner):
            return cleaner()

    def save(self, *args, **kwargs):
        ret = super().save(*args, **kwargs)
        # If the elected proxy_class isn't a proxy model, it has it's own table where a row needs to exist.
        if self.proxy_class:
            Klass = load_proxy(self.proxy_class)
            if self.__class__ != Klass and not Klass._meta.proxy and not Klass.objects.filter(pk=self.pk).exists():
                proxy_instance = copy.deepcopy(self)
                proxy_instance.__class__ = Klass
                proxy_instance.save(force_insert=True)
        return ret


class Range(AbstractRange):
    def delete(self, *args, **kwargs):
        # Disallow deleting a range with any dependents
        if self.benefit_set.exists() or self.condition_set.exists():
            raise IntegrityError('Can not delete range with a dependent benefit or condition.')
        return super().delete(*args, **kwargs)


class RangeProduct(AbstractRangeProduct):
    pass


class RangeProductFileUpload(AbstractRangeProductFileUpload):
    pass


# Make proxy_class field not unique.
Condition._meta.get_field('proxy_class')._unique = False


__all__ = [
    'BasketDiscount', 'ShippingDiscount', 'PostOrderAction',
    'SHIPPING_DISCOUNT', 'ZERO_DISCOUNT', 'ConditionalOffer',
    'Benefit', 'Condition', 'Range', 'RangeProduct',
    'RangeProductFileUpload', 'OfferGroup',
]


from .benefits import *  # NOQA
from .conditions import *  # NOQA

from .benefits import __all__ as benefit_classes  # NOQA
from .conditions import __all__ as condition_classes  # NOQA

__all__.extend(benefit_classes)
__all__.extend(condition_classes)

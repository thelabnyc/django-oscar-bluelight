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


class ConditionalOffer(AbstractConditionalOffer):
    # When offer_type == "User", we use groups to determine which users get the offer
    groups = models.ManyToManyField('auth.Group', verbose_name=_("User Groups"), blank=True)

    def availability_restrictions(self):
        restrictions = super().availability_restrictions()
        if self.offer_type == self.USER:
            restrictions.append({
                'description': _("Offer is limited to user groups: %s") % ', '.join(g.name for g in self.groups.all()),
                'is_satisfied': True,
            })
        return restrictions


class Benefit(AbstractBenefit):
    def proxy(self):
        if self.proxy_class:
            Klass = load_proxy(self.proxy_class)
            return _init_proxy_class(self, Klass)
        return super().proxy()

    @property
    def type_name(self):
        benefit_classes = getattr(settings, 'BLUELIGHT_BENEFIT_CLASSES', [])
        names = dict(benefit_classes)
        return names.get(self.proxy_class, self.proxy_class)

    @property
    def offers(self):
        return self.conditionaloffer_set.exclude(offer_type=ConditionalOffer.VOUCHER).all()

    @property
    def vouchers(self):
        for offer in self.conditionaloffer_set.filter(offer_type=ConditionalOffer.VOUCHER).all():
            for voucher in offer.vouchers.filter(parent=None).all():
                yield voucher

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

    @property
    def type_name(self):
        condition_classes = getattr(settings, 'BLUELIGHT_CONDITION_CLASSES', [])
        names = dict(condition_classes)
        names['oscarbluelight.offer.conditions.CompoundCondition'] = _("Compound condition")
        return names.get(self.proxy_class, self.proxy_class)

    @property
    def offers(self):
        return self.conditionaloffer_set.exclude(offer_type=ConditionalOffer.VOUCHER).all()

    @property
    def vouchers(self):
        for offer in self.conditionaloffer_set.filter(offer_type=ConditionalOffer.VOUCHER).all():
            for voucher in offer.vouchers.filter(parent=None).all():
                yield voucher

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
    'RangeProductFileUpload',
]


from .benefits import *  # NOQA
from .conditions import *  # NOQA

from .benefits import __all__ as benefit_classes  # NOQA
from .conditions import __all__ as condition_classes  # NOQA

__all__.extend(benefit_classes)
__all__.extend(condition_classes)

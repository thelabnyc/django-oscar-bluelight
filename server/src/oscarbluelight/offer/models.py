from django.conf import settings
from django.core import exceptions
from django.core.cache import caches
from django.db import models, IntegrityError
from django.db.models import F
from django.utils.translation import ugettext_lazy as _
from django_redis import get_redis_connection
from oscar.models.fields import AutoSlugField
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
import random

logger = logging.getLogger(__name__)

cache = caches[settings.REDIS_CACHE_ALIAS]


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
    slug = AutoSlugField(populate_from='name', unique=True, null=True, default=None)
    priority = models.IntegerField(null=False, unique=True)
    is_system_group = models.BooleanField(default=False, editable=False)

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
    short_name = models.CharField(_("Short Name"),
        max_length=50,
        help_text=_("Abbreviated version of offer name"))
    desktop_image = models.ImageField(_("Ad Image (Desktop)"),
        null=True,
        blank=True,
        upload_to=getattr(settings, 'BLUELIGHT_OFFER_IMAGE_FOLDER'),
        help_text=_("Desktop image used for promo display."))
    mobile_image = models.ImageField(_("Ad Image (Mobile)"),
        null=True,
        blank=True,
        upload_to=getattr(settings, 'BLUELIGHT_OFFER_IMAGE_FOLDER'),
        help_text=_("Mobile image used for promo display."))
    # When offer_type == "User", we use groups to determine which users get the offer
    groups = models.ManyToManyField('auth.Group',
        verbose_name=_("User Groups"),
        blank=True,
        help_text=_("Select which User Groups are eligible for this offer. If none are selected, all "
                    "users are eligible."))
    offer_group = models.ForeignKey(OfferGroup,
        verbose_name=_("Offer Group"),
        related_name='offers',
        null=True,
        on_delete=models.CASCADE,
        help_text=_("Select the Offer Group that this offer belongs to. Offer Group controls the order "
                    "offers are applied in and which offers may be combined together."))

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

    def record_usage(self, discount):
        ConditionalOffer.objects\
                        .filter(pk=self.pk)\
                        .update(num_applications=(F('num_applications') + discount['freq']),
                                total_discount=(F('total_discount') + discount['discount']),
                                num_orders=(F('num_orders') + 1))
    record_usage.alters_data = True


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
        names['oscarbluelight.offer.benefits.CompoundBenefit'] = _("Compound benefit")
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
    cache_version = models.PositiveIntegerField(_("Cache Version"),
        editable=False,
        default=1)

    def delete(self, *args, **kwargs):
        # Disallow deleting a range with any dependents
        if self.benefit_set.exists() or self.condition_set.exists():
            raise IntegrityError(_('Can not delete range with a dependent benefit or condition.'))
        return super().delete(*args, **kwargs)

    @property
    def _cache_ttl(self):
        center = getattr(settings, 'BLUELIGHT_RANGE_CACHE_TTL', 86400 * 7)
        entropy = 86400 / 2
        return random.randrange(
            max(0, center - entropy),
            (center + entropy))

    @property
    def _cache_key(self):
        return cache.make_key('oscarbluelight.models.Range.{}-{}.products'.format(self.pk, self.cache_version))

    _member_cache = None

    def contains_product(self, product):
        # If this range contains everything, short-circuit the normal (slower) logic
        if self.includes_all_products:
            excluded_product_ids = self._excluded_product_ids()
            if product.id in excluded_product_ids:
                return False
            return True
        key = self._cache_key
        conn = get_redis_connection(settings.REDIS_CACHE_ALIAS)
        # Populate redis cache if it doesn't exist, then get the set of included product IDs
        if self._member_cache is None:
            if conn.exists(key):
                self._member_cache = { int(pk) for pk in conn.smembers(key) }
            else:
                self._member_cache = { int(pk) for pk in self.populate_member_cache() }
        # Check if the given product is in the set of included product IDs
        product_ids = { product.pk }
        if product.is_child:
            product_ids.add(product.parent.pk)
        return len(self._member_cache & product_ids) > 0

    # Shorter alias for contains_product
    contains = contains_product

    def populate_member_cache(self):
        # Get all products for the set
        product_ids = self.all_products().values_list('pk', flat=True)
        if len(product_ids) <= 0:
            product_ids = [0]
        product_ids = set(product_ids)
        # Store the product IDs as a SET datatype in Redis
        key = self._cache_key
        conn = get_redis_connection(settings.REDIS_CACHE_ALIAS)
        pipe = conn.pipeline()
        pipe.delete(key)
        pipe.sadd(key, *product_ids)
        pipe.expire(key, self._cache_ttl)
        pipe.execute()
        return product_ids

    def invalidate_cached_ids(self):
        self._member_cache = None
        return super().invalidate_cached_ids()


    def increment_cache_version(self):
        self.__class__.objects.filter(pk=self.pk).update(cache_version=(F('cache_version') + 1))
        self.invalidate_cached_ids()

    def save(self, *args, **kwargs):
        # Increment the cache_version number so that memoized functions (like contains_product) are automatically invalidated.
        if self.pk:
            self.cache_version = F('cache_version') + 1
            self.invalidate_cached_ids()
        return super().save(*args, **kwargs)


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

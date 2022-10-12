from decimal import Decimal as D
from django.conf import settings
from django.dispatch import receiver
from django.core import exceptions
from django.db import models, IntegrityError, connection, transaction
from django.db.models import F
from django.utils.translation import gettext_lazy as _
from django.utils.encoding import force_str
from django.utils.functional import cached_property
from django_pgviews.signals import view_synced
from django_pgviews import view as pg
from oscar.models.fields import AutoSlugField
from oscar.apps.offer.abstract_models import (
    AbstractBenefit,
    AbstractCondition,
    AbstractConditionalOffer,
    AbstractRange,
    AbstractRangeProduct,
    AbstractRangeProductFileUpload,
)
from oscar.apps.offer.results import (
    SHIPPING_DISCOUNT,
    ZERO_DISCOUNT,
    BasketDiscount,
    PostOrderAction,
    ShippingDiscount,
)
from oscar.apps.offer.utils import load_proxy
from oscar.templatetags.currency_filters import currency
from .sql import SQL_RANGE_PRODUCTS, get_sql_range_product_triggers
import copy
import logging
import math

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
    slug = AutoSlugField(populate_from="name", unique=True, null=True, overwrite=True)
    priority = models.IntegerField(null=False, unique=True)
    is_system_group = models.BooleanField(default=False, editable=False)

    class Meta:
        verbose_name = _("OfferGroup")
        ordering = ("-priority",)

    def __str__(self):
        return "{} (priority {})".format(self.name, self.priority)


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
        _("Short Name"), max_length=50, help_text=_("Abbreviated version of offer name")
    )
    desktop_image = models.ImageField(
        _("Ad Image (Desktop)"),
        null=True,
        blank=True,
        upload_to=getattr(settings, "BLUELIGHT_OFFER_IMAGE_FOLDER"),
        help_text=_("Desktop image used for promo display."),
    )
    mobile_image = models.ImageField(
        _("Ad Image (Mobile)"),
        null=True,
        blank=True,
        upload_to=getattr(settings, "BLUELIGHT_OFFER_IMAGE_FOLDER"),
        help_text=_("Mobile image used for promo display."),
    )
    # When offer_type == "User", we use groups to determine which users get the offer
    groups = models.ManyToManyField(
        "auth.Group",
        verbose_name=_("User Groups"),
        blank=True,
        help_text=_(
            "Select which User Groups are eligible for this offer. If none are selected, all "
            "users are eligible."
        ),
    )
    offer_group = models.ForeignKey(
        OfferGroup,
        verbose_name=_("Offer Group"),
        related_name="offers",
        null=True,
        on_delete=models.CASCADE,
        help_text=_(
            "Select the Offer Group that this offer belongs to. Offer Group controls the order "
            "offers are applied in and which offers may be combined together."
        ),
    )
    affects_cosmetic_pricing = models.BooleanField(
        _("Affects Cosmetic Pricing?"),
        default=True,
        help_text=_(
            "Controls whether or not this offer will affect advertised product prices. Turn off "
            "for offers which should only apply once the product is in a customer's basket."
        ),
    )

    class Meta:
        ordering = ("-offer_group__priority", "-priority", "pk")

    def availability_restrictions(self):
        restrictions = super().availability_restrictions()
        if self.offer_type == self.USER:
            restrictions.append(
                {
                    "description": _("Offer is limited to user groups: %s")
                    % ", ".join(g.name for g in self.groups.all()),
                    "is_satisfied": True,
                }
            )
        return restrictions

    def get_upsell_details(self, basket):
        return self.condition.proxy().get_upsell_details(self, basket)

    def apply_benefit(self, basket):
        try:
            return super().apply_benefit(basket)
        except Exception as e:
            logger.exception(e)
            return ZERO_DISCOUNT

    def record_usage(self, discount):
        ConditionalOffer.objects.filter(pk=self.pk).update(
            num_applications=(F("num_applications") + discount["freq"]),
            total_discount=(F("total_discount") + discount["discount"]),
            num_orders=(F("num_orders") + 1),
        )

    record_usage.alters_data = True


class Benefit(AbstractBenefit):
    # Use this field to provide an hard-cap on the discount amount than a benefit
    # can provide.
    max_discount = models.DecimalField(
        _("Max discount"),
        decimal_places=2,
        max_digits=12,
        null=True,
        blank=True,
        help_text=_(
            "If set, do not allow this benefit to provide a discount greater "
            "than this amount (for a particular basket application)."
        ),
    )

    def proxy(self):
        if self.proxy_class:
            Klass = load_proxy(self.proxy_class)
            return _init_proxy_class(self, Klass)
        return super().proxy()

    @property
    def name(self):
        return force_str(super().name)

    @property
    def type_name(self):
        benefit_classes = getattr(settings, "BLUELIGHT_BENEFIT_CLASSES", [])
        names = dict(benefit_classes)
        names["oscarbluelight.offer.benefits.CompoundBenefit"] = _("Compound benefit")
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
            raise exceptions.ValidationError(
                _("Benefit should not have a type field. Use proxy class instead.")
            )
        proxy_instance = self.proxy()
        cleaner = getattr(proxy_instance, "_clean", None)
        if cleaner and callable(cleaner):
            return cleaner()
        return super().clean()

    def save(self, *args, **kwargs):
        ret = super().save(*args, **kwargs)
        # If the elected proxy_class isn't a proxy model, it has it's own table where a row needs to exist.
        if self.proxy_class:
            Klass = load_proxy(self.proxy_class)
            if (
                self.__class__ != Klass
                and not Klass._meta.proxy
                and not Klass.objects.filter(pk=self.pk).exists()
            ):
                proxy = copy.deepcopy(self)
                proxy.__class__ = Klass
                proxy.save()
        return ret

    def _get_max_discount_amount(self, max_total_discount=None):
        if max_total_discount is not None:
            return max_total_discount
        if self.max_discount is not None:
            return self.max_discount
        return D(math.inf)

    def _append_max_discount_to_text(self, text):
        if self.max_discount:
            text += _(", maximum discount of %(max_discount)s") % {
                "max_discount": currency(self.max_discount),
            }
        return text


class Condition(AbstractCondition):
    def proxy(self):
        if self.proxy_class:
            Klass = load_proxy(self.proxy_class)
            return _init_proxy_class(self, Klass)
        return super().proxy()

    @property
    def name(self):
        return force_str(super().name)

    @property
    def type_name(self):
        condition_classes = getattr(settings, "BLUELIGHT_CONDITION_CLASSES", [])
        names = dict(condition_classes)
        names["oscarbluelight.offer.conditions.CompoundCondition"] = _(
            "Compound condition"
        )
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
            raise exceptions.ValidationError(
                _("Condition should not have a type field. Use proxy class instead.")
            )
        proxy_instance = self.proxy()
        cleaner = getattr(proxy_instance, "_clean", None)
        if cleaner and callable(cleaner):
            return cleaner()

    def save(self, *args, **kwargs):
        ret = super().save(*args, **kwargs)
        # If the elected proxy_class isn't a proxy model, it has it's own table where a row needs to exist.
        if self.proxy_class:
            Klass = load_proxy(self.proxy_class)
            if (
                self.__class__ != Klass
                and not Klass._meta.proxy
                and not Klass.objects.filter(pk=self.pk).exists()
            ):
                proxy_instance = copy.deepcopy(self)
                proxy_instance.__class__ = Klass
                proxy_instance.save(force_insert=True)
        return ret


class Range(AbstractRange):
    @cached_property
    def product_queryset(self):
        Product = self.included_products.model
        # Use the "Include All" escape hatch?
        if self.includes_all_products:
            # Filter out blacklisted products
            return Product.objects.all().exclude(
                id__in=self.excluded_products.values("id")
            )
        # Query the cache view
        return Product.objects.all().filter(cached_ranges__range=self)

    def add_product_batch(self, products):
        """
        Same as Range.add_product, but works on a batch of products (in order to optimize the number
        of queries run on the DB)
        """
        # Insert new rows into the included_products relationship
        RangeProduct = self.included_products.through
        rows = [RangeProduct(range=self, product=product) for product in products]
        RangeProduct.objects.bulk_create(rows, ignore_conflicts=True)
        # Remove product from excluded products if it was removed earlier and
        # re-added again, thus it returns back to the range product list.
        ExcludedProduct = self.excluded_products.through
        ExcludedProduct.objects.filter(product__in=products).all().delete()
        # Invalidate cache because queryset has changed
        self.invalidate_cached_queryset()

    def delete(self, *args, **kwargs):
        # Disallow deleting a range with any dependents
        if self.benefit_set.exists() or self.condition_set.exists():
            raise IntegrityError(
                _("Can not delete range with a dependent benefit or condition.")
            )
        return super().delete(*args, **kwargs)


class RangeProduct(AbstractRangeProduct):
    pass


class RangeProductFileUpload(AbstractRangeProductFileUpload):
    pass


class RangeProductSet(pg.MaterializedView):
    range = models.ForeignKey(
        Range, related_name="cached_products", on_delete=models.DO_NOTHING
    )
    product = models.ForeignKey(
        "catalogue.Product", related_name="cached_ranges", on_delete=models.DO_NOTHING
    )

    concurrent_index = "range_id, product_id"
    sql = SQL_RANGE_PRODUCTS

    class Meta:
        managed = False

    @classmethod
    def set_disable_triggers_for_session(cls, disable_triggers):
        if disable_triggers:
            stmnt = "SET oscarbluelight.disable_triggers = true"
        else:
            stmnt = "SET oscarbluelight.disable_triggers = false"
        with connection.cursor() as cursor:
            cursor.execute(stmnt)


# Make proxy_class field not unique.
Condition._meta.get_field("proxy_class")._unique = False


__all__ = [
    "BasketDiscount",
    "ShippingDiscount",
    "PostOrderAction",
    "SHIPPING_DISCOUNT",
    "ZERO_DISCOUNT",
    "ConditionalOffer",
    "Benefit",
    "Condition",
    "Range",
    "RangeProduct",
    "RangeProductFileUpload",
    "OfferGroup",
]


from .benefits import *  # NOQA
from .conditions import *  # NOQA

from .benefits import __all__ as benefit_classes  # NOQA
from .conditions import __all__ as condition_classes  # NOQA

__all__.extend(benefit_classes)
__all__.extend(condition_classes)


@receiver(view_synced, sender=RangeProductSet)
@transaction.atomic()
def add_view_triggers(sender, **kwargs):
    with connection.cursor() as cursor:
        for sql in get_sql_range_product_triggers():
            cursor.execute(sql)

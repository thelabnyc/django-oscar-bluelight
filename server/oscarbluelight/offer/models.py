from __future__ import annotations

from collections.abc import Collection, Iterable
from datetime import datetime, timedelta
from decimal import Decimal
from typing import TYPE_CHECKING, Any, TypedDict, TypeVar
import copy
import logging
import math
import time

from django.conf import settings
from django.core import exceptions
from django.db import IntegrityError, connection, models
from django.db.models import F, Q, QuerySet
from django.db.models.base import ModelBase
from django.utils import timezone
from django.utils.encoding import force_str
from django.utils.functional import cached_property
from django.utils.translation import gettext_lazy as _
from oscar.apps.offer.abstract_models import (
    AbstractBenefit,
    AbstractCondition,
    AbstractConditionalOffer,
    AbstractRange,
    AbstractRangeProduct,
    AbstractRangeProductFileUpload,
)
from oscar.apps.offer.results import ApplicationResult
from oscar.apps.offer.utils import load_proxy
from oscar.core.loading import get_class, get_model
from oscar.models.fields import AutoSlugField  # type:ignore[attr-defined]
from oscar.templatetags.currency_filters import currency
from thelabdb.pgviews import view as pg

from .results import (
    SHIPPING_DISCOUNT,
    ZERO_DISCOUNT,
    BasketDiscount,
    OfferApplication,
    PostOrderAction,
    ShippingDiscount,
)
from .sql import SQL_RANGE_PRODUCTS, get_recalculate_offer_application_totals_sql

if TYPE_CHECKING:
    from django_stubs_ext import StrOrPromise
    from oscar.apps.catalogue.expressions import ExpandDownwardsCategoryQueryset
    from oscar.apps.catalogue.models import Product
    from oscar.apps.order.models import Order as _Order
    from oscar.apps.order.models import OrderDiscount as _OrderDiscount

    from ..mixins import BluelightBasketMixin as Basket
    from ..voucher.models import Voucher as _Voucher
    from .upsells import OfferUpsell
else:
    ExpandDownwardsCategoryQueryset = get_class(
        "catalogue.expressions", "ExpandDownwardsCategoryQueryset"
    )

logger = logging.getLogger(__name__)

T = TypeVar("T", bound=type[models.Model])


def _init_proxy_class(obj: T, Klass: type[T]) -> T:
    # Check if we're already the correct class
    if obj.__class__ == Klass:  # type:ignore[comparison-overlap]
        return obj

    # Check if we're using multi-table inheritance
    model_name = Klass._meta.model_name  # type:ignore[attr-defined]
    if hasattr(obj, model_name):
        return getattr(obj, model_name)

    # Else, it's just a proxy model
    proxy = copy.deepcopy(obj)
    proxy.__class__ = Klass  # type:ignore[method-assign, assignment]
    return proxy


class AvailabilityRestriction(TypedDict):
    description: str
    is_satisfied: bool


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

    def __str__(self) -> str:
        return f"{self.name} (priority {self.priority})"


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

    @classmethod
    def recalculate_offer_application_totals(cls) -> None:
        Order: type[_Order] = get_model("order", "Order")
        OrderDiscount: type[_OrderDiscount] = get_model("order", "OrderDiscount")
        start_ns = time.perf_counter_ns()
        update_sql = get_recalculate_offer_application_totals_sql(
            Order=Order,
            OrderDiscount=OrderDiscount,
            ConditionalOffer=cls,
            ignored_order_statuses=settings.BLUELIGHT_IGNORED_ORDER_STATUSES,
        )
        with connection.cursor() as cursor:
            cursor.execute(update_sql)
            updated_rows = cursor.rowcount
        end_ns = time.perf_counter_ns()
        elasped_ms = (end_ns - start_ns) / 1_000_000
        logger.info(
            "Successfully recalculated offer application totals in %.3fms. Updated %d offers.",
            elasped_ms,
            updated_rows,
        )

    def availability_restrictions(self) -> list[AvailabilityRestriction]:
        restrictions: list[AvailabilityRestriction] = (
            super().availability_restrictions()
        )
        if self.offer_type == self.USER:
            restrictions.append(
                {
                    "description": _("Offer is limited to user groups: %s")
                    % ", ".join(g.name for g in self.groups.all()),
                    "is_satisfied": True,
                }
            )
        return restrictions

    def get_upsell_details(self, basket: Basket) -> OfferUpsell | None:
        return self.condition.proxy().get_upsell_details(self, basket)

    def apply_benefit(self, basket: Basket) -> ApplicationResult:
        try:
            return super().apply_benefit(basket)
        except Exception as e:
            logger.exception(e)
            return ZERO_DISCOUNT

    def record_usage(self, discount: OfferApplication) -> None:
        ConditionalOffer.objects.filter(pk=self.pk).update(
            num_applications=(F("num_applications") + discount["freq"]),
            total_discount=(F("total_discount") + discount["discount"]),
            num_orders=(F("num_orders") + 1),
        )

    record_usage.alters_data = True  # type:ignore[attr-defined]


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

    def proxy(self) -> Benefit:
        if self.proxy_class:
            Klass = load_proxy(self.proxy_class)
            return _init_proxy_class(self, Klass)
        return super().proxy()

    @property
    def name(self) -> StrOrPromise:
        return force_str(super().name)

    @property
    def type_name(self) -> str:
        benefit_classes = getattr(settings, "BLUELIGHT_BENEFIT_CLASSES", [])
        names = dict(benefit_classes)
        names["oscarbluelight.offer.benefits.CompoundBenefit"] = _("Compound benefit")
        return names.get(self.proxy_class, self.proxy_class)

    @property
    def non_voucher_offers(self) -> QuerySet[ConditionalOffer]:
        return self.offers.exclude(offer_type=ConditionalOffer.VOUCHER).all()

    @property
    def vouchers(self) -> list[_Voucher]:
        vouchers = []
        for offer in self.offers.filter(offer_type=ConditionalOffer.VOUCHER).all():
            for voucher in offer.vouchers.filter(parent=None).all():
                vouchers.append(voucher)
        return vouchers

    def clean(self) -> None:
        if self.type:
            raise exceptions.ValidationError(
                _("Benefit should not have a type field. Use proxy class instead.")
            )
        proxy_instance = self.proxy()
        cleaner = getattr(proxy_instance, "_clean", None)
        if cleaner and callable(cleaner):
            return cleaner()
        return super().clean()

    def save(
        self,
        force_insert: bool | tuple[ModelBase, ...] = False,
        force_update: bool = False,
        using: str | None = None,
        update_fields: Iterable[str] | None = None,
    ) -> None:
        ret = super().save(
            force_insert=force_insert,
            force_update=force_update,
            using=using,
            update_fields=update_fields,
        )
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

    def _get_max_discount_amount(
        self, max_total_discount: Decimal | None = None
    ) -> Decimal:
        if max_total_discount is not None:
            return max_total_discount
        if self.max_discount is not None:
            return self.max_discount
        return Decimal(math.inf)

    def _append_max_discount_to_text(self, text: StrOrPromise) -> StrOrPromise:
        if self.max_discount:
            text += _(", maximum discount of %(max_discount)s") % {
                "max_discount": currency(self.max_discount),
            }
        return text


class Condition(AbstractCondition):
    def proxy(self) -> Condition:
        if self.proxy_class:
            Klass = load_proxy(self.proxy_class)
            return _init_proxy_class(self, Klass)
        return super().proxy()

    @property
    def name(self) -> StrOrPromise:
        return force_str(super().name)

    @property
    def type_name(self) -> str:
        condition_classes = getattr(settings, "BLUELIGHT_CONDITION_CLASSES", [])
        names = dict(condition_classes)
        names["oscarbluelight.offer.conditions.CompoundCondition"] = _(
            "Compound condition"
        )
        return names.get(self.proxy_class, self.proxy_class)

    @property
    def non_voucher_offers(self) -> QuerySet[ConditionalOffer]:
        return self.offers.exclude(offer_type=ConditionalOffer.VOUCHER).all()

    @property
    def vouchers(self) -> QuerySet[_Voucher]:
        from ..voucher.models import Voucher

        return (
            Voucher.objects.filter(
                offers__in=self.offers.filter(
                    offer_type=ConditionalOffer.VOUCHER
                ).all(),
                parent=None,
            )
            .distinct()
            .select_related()
        )

    def get_upsell_details(
        self, offer: ConditionalOffer, basket: Basket
    ) -> OfferUpsell | None:
        return None

    def clean(self) -> None:
        if self.type:
            raise exceptions.ValidationError(
                _("Condition should not have a type field. Use proxy class instead.")
            )
        proxy_instance = self.proxy()
        cleaner = getattr(proxy_instance, "_clean", None)
        if cleaner and callable(cleaner):
            return cleaner()

    def save(
        self,
        force_insert: bool | tuple[ModelBase, ...] = False,
        force_update: bool = False,
        using: str | None = None,
        update_fields: Iterable[str] | None = None,
    ) -> None:
        ret = super().save(
            force_insert=force_insert,
            force_update=force_update,
            using=using,
            update_fields=update_fields,
        )
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
    def product_queryset(self) -> QuerySet[Product]:
        Product = self.included_products.model
        # Use the "Include All" escape hatch?
        if self.includes_all_products:
            _filter = Q(id__in=self.excluded_products.values("id"))
            # extend filter if excluded_categories exist
            if self.excluded_categories.exists():
                expanded_range_categories = ExpandDownwardsCategoryQueryset(
                    self.excluded_categories.values("id")
                )
                _filter |= Q(categories__in=expanded_range_categories)
                # extend filter for parent categories, exclude parent = None
                if (
                    Product.objects.exclude(parent=None)
                    .filter(parent__categories__in=expanded_range_categories)
                    .exists()
                ):
                    _filter |= Q(parent__categories__in=expanded_range_categories)

            # Filter out blacklisted
            return Product.objects.exclude(_filter)
        # Query the cache view
        return Product.objects.all().filter(cached_ranges__range=self)

    def all_products_consistent(self) -> QuerySet[Product]:
        """
        Get the list of products without using the materialized view.
        oscar.apps.offer.abstract_models.AbstractRange.product_queryset
        without utilizing @cached_property
        """
        return AbstractRange.product_queryset.real_func(  # type:ignore[attr-defined]
            self
        )

    def add_product_batch(self, products: Collection[Product]) -> None:
        """
        Same as Range.add_product, but works on a batch of products (in order to optimize the number
        of queries run on the DB)
        """
        from .handlers import queue_rps_view_refresh

        # Insert new rows into the included_products relationship
        RangeProduct = self.included_products.through
        rows = [RangeProduct(range=self, product=product) for product in products]
        RangeProduct.objects.bulk_create(rows, ignore_conflicts=True)
        # Remove product from excluded products if it was removed earlier and
        # re-added again, thus it returns back to the range product list.
        ExcludedProduct = self.excluded_products.through
        ExcludedProduct.objects.filter(  # type:ignore[attr-defined]
            range=self,
            product__in=products,
        ).all().delete()
        # Queue a view refresh
        queue_rps_view_refresh()
        # Invalidate cache because queryset has changed
        self.invalidate_cached_queryset()

    def exclude_product_batch(self, products: Collection[Product]) -> None:
        """
        Inverse of add_product_batch
        """
        from .handlers import queue_rps_view_refresh

        # Insert new rows into the excluded_products relationship
        ExcludedProduct = self.excluded_products.through
        rows = [ExcludedProduct(range=self, product=product) for product in products]
        ExcludedProduct.objects.bulk_create(  # type:ignore[attr-defined]
            rows,
            ignore_conflicts=True,
        )
        # Remove product from excluded products if it was removed earlier and
        # re-added again, thus it returns back to the range product list.
        RangeProduct = self.included_products.through
        RangeProduct.objects.filter(range=self, product__in=products).all().delete()
        # Queue a view refresh
        queue_rps_view_refresh()
        # Invalidate cache because queryset has changed
        self.invalidate_cached_queryset()

    def delete(self, *args: Any, **kwargs: Any) -> Any:
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


class ViewRefreshLog(models.Model):
    class ViewType(models.IntegerChoices):
        RANGE_PRODUCT_SET = 1, _("Range Product Set")
        OFFER_APPLICATION_TOTALS = 2, _("Offer Application Totals")

    view_type = models.PositiveSmallIntegerField(choices=ViewType)
    refreshed_on = models.DateTimeField()

    class Meta:
        ordering = ("-refreshed_on", "view_type")
        indexes = [
            models.Index(fields=["view_type", "refreshed_on"]),
        ]

    @classmethod
    def log_view_refresh(cls, view_type: ViewType) -> None:
        now = timezone.now()
        # Truncate old log entries
        threshold = now - timedelta(hours=1)
        cls.objects.filter(
            view_type=view_type,
            refreshed_on__lte=threshold,
        ).all().delete()
        # Log the refresh
        cls.objects.create(view_type=view_type, refreshed_on=now)

    @classmethod
    def is_refresh_needed(cls, view_type: ViewType, requested_on_dt: datetime) -> bool:
        if timezone.is_naive(requested_on_dt):
            requested_on_dt = timezone.make_aware(requested_on_dt)
        last_refresh_dt = cls.get_last_refresh_dt(view_type)
        if last_refresh_dt is None:
            return True
        if timezone.is_naive(last_refresh_dt):
            last_refresh_dt = timezone.make_aware(last_refresh_dt)
        logger.info(
            "Evaluating RangeProductSetRefreshLog.is_refresh_needed. RequestedOn:[%s], LastRefresh:[%s]",
            requested_on_dt,
            last_refresh_dt,
        )
        return requested_on_dt >= last_refresh_dt

    @classmethod
    def get_last_refresh_dt(cls, view_type: ViewType) -> datetime | None:
        entry = cls.objects.filter(view_type=view_type).first()
        if not entry:
            return None
        return entry.refreshed_on


# Make proxy_class field not unique.
Condition._meta.get_field("proxy_class")._unique = False  # type:ignore[attr-defined]


__all__: list[str] = [
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
from .benefits import __all__ as benefit_classes  # NOQA
from .conditions import *  # NOQA
from .conditions import __all__ as condition_classes  # NOQA

__all__.extend(benefit_classes)  # type:ignore[has-type]
__all__.extend(condition_classes)  # type:ignore[has-type]

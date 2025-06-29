from __future__ import annotations

from decimal import Decimal
from typing import TYPE_CHECKING, Any, Literal, TypedDict
import logging

from django.contrib import messages
from django.db import transaction
from django.db.models import Q, QuerySet
from django.http import HttpRequest, HttpResponse, HttpResponseRedirect
from django.urls import reverse
from django.utils.translation import gettext_lazy as _
from django.utils.translation import ngettext
from django.views.generic import UpdateView
from oscar.apps.dashboard.ranges.views import RangeListView as BaseRangeListView
from oscar.apps.dashboard.ranges.views import (
    RangeProductListView as BaseRangeProductListView,
)

from oscarbluelight.offer.models import Range, RangeProductFileUpload

from .forms import (
    BatchPriceUpdateForm,
    RangeExcludedProductsUpdateForm,
    RangeProductForm,
    RangeProductSearchForm,
    RangeSearchForm,
)

if TYPE_CHECKING:
    from oscar.apps.catalogue.managers import ProductQuerySet
    from oscar.apps.partner.models import StockRecord

logger = logging.getLogger(__name__)


class RangeListView(BaseRangeListView):
    form_class = RangeSearchForm

    def get_queryset(self) -> QuerySet[Range]:
        qs = (
            super()
            .get_queryset()
            .prefetch_related("benefit_set", "condition_set", "suggesting_bundles")
            .order_by("name")
        )
        self.form = self.form_class(self.request.GET)
        qs, is_filtered = self.form.filter_queryset(qs)
        self.is_filtered = is_filtered
        return qs

    def get_context_data(self, **kwargs: Any) -> dict[str, Any]:
        ctx = super().get_context_data(**kwargs)
        ctx["form"] = self.form
        ctx["is_filtered"] = self.is_filtered
        return ctx


class BatchChangePreview(TypedDict):
    price: Decimal
    difference: Decimal
    direction: Literal["more", "less"]


class RangePriceListView(UpdateView):
    model = Range
    context_object_name = "range"
    form_class = BatchPriceUpdateForm
    template_name = "oscar/dashboard/ranges/range_price_list.html"

    def get_context_data(self, **kwargs: Any) -> dict[str, Any]:
        context = super().get_context_data(**kwargs)
        return context

    def get_success_url(self) -> str:
        return reverse("dashboard:range-prices", args=(self.get_object().pk,))

    def form_valid(self, form: BatchPriceUpdateForm) -> HttpResponse:
        rng = self.get_object()

        if "apply" in self.request.POST:
            self._apply_changes(rng, form)
            messages.success(self.request, _("Successfully Applied Price Update"))
            return HttpResponseRedirect(self.get_success_url())

        changes = self._build_changes_preview(rng, form)
        messages.info(self.request, _("Preview Prices Updated Below"))
        return self.render_to_response(
            self.get_context_data(form=form, preview=True, changes=changes)
        )

    def _build_changes_preview(
        self, rng: Range, form: BatchPriceUpdateForm
    ) -> dict[int, BatchChangePreview]:
        changes: dict[int, BatchChangePreview] = {}

        def do_discount_preview(sr: StockRecord) -> None:
            if sr.price is None:
                return
            new_price = form.apply_discount(
                getattr(sr, "price_retail", sr.price),
                sr.price,
            )
            difference = new_price - sr.price
            changes[sr.id] = {
                "price": new_price,
                "difference": abs(difference),
                "direction": "more" if difference > 0 else "less",
            }

        for product in rng.all_products():
            for sr in product.stockrecords.all():
                do_discount_preview(sr)
            for child in product.children.all():
                for sr in child.stockrecords.all():
                    do_discount_preview(sr)

        return changes

    @transaction.atomic
    def _apply_changes(self, rng: Range, form: BatchPriceUpdateForm) -> None:
        def do_discount(sr: StockRecord) -> None:
            if sr.price is None:
                return
            old_price = sr.price
            new_price = form.apply_discount(
                getattr(sr, "price_retail", sr.price),
                sr.price,
            )
            sr.price = new_price
            sr.save()
            logger.info(
                "User %s adjusted price of StockRecord[%s] from %s to %s"
                % (self.request.user, sr.pk, old_price, new_price)
            )

        for product in rng.all_products():
            for sr in product.stockrecords.all():
                do_discount(sr)
            for child in product.children.all():
                for sr in child.stockrecords.all():
                    do_discount(sr)


class RangeExcludedProductsView(UpdateView):
    model = Range
    context_object_name = "range"
    form_class = RangeExcludedProductsUpdateForm
    template_name = "oscar/dashboard/ranges/range_excluded_products.html"

    def get_success_url(self) -> str:
        return reverse("dashboard:range-list")


class RangeProductListView(BaseRangeProductListView):
    form_class = RangeProductForm
    search_form_class = RangeProductSearchForm

    def get_queryset(self) -> ProductQuerySet:
        """
        Override default query for RangeProductList
        Retrieve the product queryset directly from the database for accuracy in the dashboard
        """
        range_instance = self.get_product_range()
        products = (
            range_instance.all_products_consistent()
            .prefetch_related("stockrecords")
            .order_by("rangeproduct__display_order")
            .distinct()
        )
        search_form = self.search_form_class(self.request.GET)
        if search_form.is_valid():
            data = search_form.cleaned_data
            filter_q = Q()
            if data.get("product_name"):
                filter_q &= Q(title__search=data["product_name"])
            if data.get("upc"):
                filter_q &= Q(upc__iexact=data["upc"])
            if data.get("sku"):
                filter_q &= Q(stockrecords__partner_sku__iexact=data["sku"])
            if filter_q:
                products = products.filter(filter_q)
        return products

    def get_context_data(self, **kwargs: Any) -> dict[str, Any]:
        context = super().get_context_data(**kwargs)
        # Add search form to context
        if "search_form" not in context:
            context["search_form"] = self.search_form_class(self.request.GET)
        return context

    def handle_query_products(
        self, request: HttpRequest, product_range: Range, form: RangeProductForm
    ) -> None:
        products = form.get_products()
        if not products:
            return
        # Check what kind of operaiton this is, add or exclude
        if (
            form.cleaned_data["upload_type"]
            == RangeProductFileUpload.EXCLUDED_PRODUCTS_TYPE
        ):
            product_range.exclude_product_batch(products)
            action = _("excluded from this range")
        else:
            # Add the products to the range in a batch
            product_range.add_product_batch(products)
            action = _("added to this range")
        # Message the user
        num_products = len(products)
        messages.success(
            request,
            ngettext(
                "%(num_products)d product has been %(action)s",
                "%(num_products)d products have been %(action)s",
                num_products,
            )
            % {"num_products": num_products, "action": action},
        )
        dupe_skus = form.get_duplicate_skus()
        if dupe_skus:
            messages.warning(
                request,
                _(
                    "The products with SKUs or UPCs matching %(skus)s have "
                    "already been %(action)s"
                )
                % {"skus": ", ".join(dupe_skus), "action": action},
            )

        missing_skus = form.get_missing_skus()
        if missing_skus:
            messages.warning(
                request,
                _("No product(s) were found with SKU or UPC matching %s")
                % ", ".join(missing_skus),
            )
        self.check_imported_products_sku_duplicates(request, products)

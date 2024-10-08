from django.contrib import messages
from django.urls import reverse
from django.db import transaction
from django.http import HttpResponseRedirect
from django.views.generic import UpdateView
from django.utils.translation import ngettext, gettext_lazy as _
from oscar.core.loading import get_class, get_model
from oscar.apps.dashboard.ranges.views import (
    RangeListView as BaseRangeListView,
    RangeProductListView as BaseRangeProductListView,
)
from .forms import RangeSearchForm, RangeProductForm
import logging

logger = logging.getLogger(__name__)

Range = get_model("offer", "Range")
RangeProductFileUpload = get_model("offer", "RangeProductFileUpload")
BatchPriceUpdateForm = get_class("ranges_dashboard.forms", "BatchPriceUpdateForm")
RangeExcludedProductsUpdateForm = get_class(
    "ranges_dashboard.forms", "RangeExcludedProductsUpdateForm"
)


class RangeListView(BaseRangeListView):
    form_class = RangeSearchForm

    def get_queryset(self):
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

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["form"] = self.form
        ctx["is_filtered"] = self.is_filtered
        return ctx


class RangePriceListView(UpdateView):
    model = Range
    context_object_name = "range"
    form_class = BatchPriceUpdateForm
    template_name = "oscar/dashboard/ranges/range_price_list.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        return context

    def get_success_url(self):
        return reverse("dashboard:range-prices", args=(self.get_object().pk,))

    def form_valid(self, form):
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

    def _build_changes_preview(self, rng, form):
        changes = {}

        def do_discount_preview(sr):
            new_price = form.apply_discount(
                getattr(sr, "price_retail", sr.price), sr.price
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
    def _apply_changes(self, rng, form):
        def do_discount(sr):
            old_price = sr.price
            new_price = form.apply_discount(
                getattr(sr, "price_retail", sr.price), sr.price
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

    def get_success_url(self):
        return reverse("dashboard:range-list")


class RangeProductListView(BaseRangeProductListView):
    form_class = RangeProductForm

    def get_queryset(self):
        """
        Override default query for RangeProductList
        Retrieve the product queryset directly from the database for accuracy in the dashboard
        """
        range_instance = self.get_product_range()
        products = (
            range_instance.all_products_consistent()
            .order_by("rangeproduct__display_order")
            .distinct()
        )

        return products

    def handle_query_products(self, request, product_range, form):
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

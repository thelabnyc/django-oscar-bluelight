from decimal import Decimal
from typing import TYPE_CHECKING, Any

from django import forms
from django.contrib.postgres.search import SearchVector
from django.db.models import Q, QuerySet
from django.utils.translation import gettext_lazy as _
from oscar.apps.dashboard.ranges.forms import UPC_SET_REGEX
from oscar.apps.dashboard.ranges.forms import RangeProductForm as BaseRangeProductForm
from oscar.core.loading import get_model

from oscarbluelight.offer.models import Range, RangeProductFileUpload

if TYPE_CHECKING:
    from oscar.apps.catalogue.models import Product
else:
    Product = get_model("catalogue", "Product")


class BaseRangeSearchForm(forms.Form):
    product_name = forms.CharField(required=False, label=_("Product Name"))
    upc = forms.CharField(required=False, label=_("UPC"))
    sku = forms.CharField(required=False, label=_("SKU"))


class RangeSearchForm(BaseRangeSearchForm):
    text = forms.CharField(required=False, label=_("Search"))

    def filter_queryset(self, qs: QuerySet[Range]) -> tuple[QuerySet[Range], bool]:
        is_filtered = False
        if not self.is_valid():
            return qs, is_filtered
        data = self.cleaned_data

        if data.get("text"):
            qs = qs.annotate(search=SearchVector("name", "slug", "description")).filter(
                search=data["text"]
            )
            is_filtered = True

        # Filter by contained-products is difficult because the not a simple in-DB relationship.
        # Products are included in a range by one of several means (by category or by direct
        # inclusion) and can also be directly excluded. Thus, we can't do this filter in a single
        # query. Instead, we have to:
        #   1. Find the Products matching the query
        #   2. Build a set of all the Range IDs which include those products
        #   3. Filter the original queryset by those RangeIDs
        if data.get("product_name") or data.get("upc") or data.get("sku"):
            products_qs = Product.objects.all()
            if data.get("product_name"):
                products_qs = products_qs.filter(title__search=data["product_name"])
            if data.get("upc"):
                products_qs = products_qs.filter(upc__iexact=data["upc"])
            if data.get("sku"):
                products_qs = products_qs.filter(
                    stockrecords__partner_sku__iexact=data["sku"]
                )
            products = products_qs.all()
            range_ids = set()
            for r in qs.all():
                for p in products:
                    if r.contains_product(p):
                        range_ids.add(r.pk)
                        break
            qs = qs.filter(pk__in=range_ids)
            is_filtered = True

        return qs, is_filtered


class RangeProductSearchForm(BaseRangeSearchForm):
    pass


class BatchPriceUpdateForm(forms.Form):
    ABSOLUTE, PERCENTAGE_RETAIL, PERCENTAGE_ACTUAL = (
        "ABSOLUTE",
        "PERCENTAGE_RETAIL",
        "PERCENTAGE_ACTUAL",
    )
    TYPES = (
        (PERCENTAGE_RETAIL, "Absolute Percentage of Retail Price"),
        (PERCENTAGE_ACTUAL, "Relative Percentage of Price Excluding Tax"),
        (ABSOLUTE, "Absolute Change"),
    )
    operation_type = forms.ChoiceField(
        label="Type of Change to Apply", initial=PERCENTAGE_RETAIL, choices=TYPES
    )
    amount = forms.DecimalField(initial=0, decimal_places=2, max_digits=12)

    def __init__(
        self,
        instance: Range | None = None,
        *args: Any,
        **kwargs: Any,
    ) -> None:
        super().__init__(*args, **kwargs)

    def apply_discount(
        self,
        price_retail: Decimal,
        price_excl_tax: Decimal,
    ) -> Decimal:
        otype = self.cleaned_data["operation_type"]
        amount = self.cleaned_data["amount"]
        operations = {
            self.PERCENTAGE_RETAIL: lambda: price_retail * (amount / 100),
            self.PERCENTAGE_ACTUAL: lambda: price_excl_tax
            + (price_excl_tax * (amount / 100)),
            self.ABSOLUTE: lambda: price_excl_tax + amount,
        }
        return operations[otype]()


class RangeExcludedProductsUpdateForm(forms.ModelForm):
    class Meta:
        model = Range
        fields = ["excluded_products"]
        help_texts = {
            "excluded_products": _(
                "What is an excluded product? Products listed here will not be considered as part of this range, even "
                "if they would normally be included by another means, such as by Category, by Product Class, or because "
                "it's Parent Product is included."
            ),
        }


class RangeProductForm(BaseRangeProductForm):
    def clean_query_with_upload_type(self, raw: str, upload_type: str) -> None:
        # Check that the search matches some products
        ids = set(UPC_SET_REGEX.findall(raw))
        # switch for included or excluded products
        if upload_type == RangeProductFileUpload.EXCLUDED_PRODUCTS_TYPE:
            products = self.product_range.excluded_products.all()
            action = _("excluded from this range")
        else:
            # Fetch the product queryset directly from the database to make the
            # success/warning/error messages be consistent with the dashboard view
            products = self.product_range.all_products_consistent()
            action = _("added to this range")
        existing_skus = set(
            products.values_list("stockrecords__partner_sku", flat=True)
        )
        existing_upcs = set(products.values_list("upc", flat=True))
        existing_ids = existing_skus.union(existing_upcs)
        new_ids = ids - existing_ids
        if len(new_ids) == 0:
            self.add_error(
                "query",
                _(
                    "The products with SKUs or UPCs matching %(skus)s have "
                    "already been %(action)s"
                )
                % {"skus": ", ".join(ids), "action": action},
            )
        else:
            self.products = Product._default_manager.filter(
                Q(stockrecords__partner_sku__in=new_ids) | Q(upc__in=new_ids)
            )
            if len(self.products) == 0:
                self.add_error(
                    "query",
                    _("No products exist with a SKU or UPC matching %s")
                    % ", ".join(ids),
                )
            found_skus = set(
                self.products.values_list("stockrecords__partner_sku", flat=True)
            )
            found_upcs = set(self.products.values_list("upc", flat=True))
            found_ids = found_skus.union(found_upcs)
            self.missing_skus = new_ids - found_ids
            self.duplicate_skus = existing_ids.intersection(ids)

from django import forms
from django.utils.translation import gettext_lazy as _
from django.contrib.postgres.search import SearchVector
from oscar.core.loading import get_model


Product = get_model("catalogue", "Product")
Range = get_model("offer", "Range")


class RangeSearchForm(forms.Form):
    text = forms.CharField(required=False, label=_("Search"))
    product_name = forms.CharField(required=False, label=_("Product Name"))
    upc = forms.CharField(required=False, label=_("UPC"))
    sku = forms.CharField(required=False, label=_("SKU"))

    def filter_queryset(self, qs):
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

    def __init__(self, instance=None, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def apply_discount(self, price_retail, price_excl_tax):
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

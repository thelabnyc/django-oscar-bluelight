from django import forms
from django.db.models import Q
from django.conf import settings
from django.contrib.auth.models import Group
from django.utils.translation import gettext_lazy as _
from oscar.forms.widgets import DatePickerInput
from oscar.apps.dashboard.offers.forms import (
    RestrictionsForm as BaseRestrictionsForm,
)
from django.forms import ModelMultipleChoiceField
from oscar.core.loading import get_model

ConditionalOffer = get_model("offer", "ConditionalOffer")
CompoundBenefit = get_model("offer", "CompoundBenefit")
Benefit = get_model("offer", "Benefit")
CompoundCondition = get_model("offer", "CompoundCondition")
Condition = get_model("offer", "Condition")
Range = get_model("offer", "Range")
OfferGroup = get_model("offer", "OfferGroup")
Order = get_model("order", "Order")
SourceType = get_model("payment", "SourceType")


class BenefitSearchForm(forms.Form):
    range = forms.ModelChoiceField(
        required=False, queryset=Range.objects.order_by("name")
    )


class ConditionSearchForm(forms.Form):
    range = forms.ModelChoiceField(
        required=False, queryset=Range.objects.order_by("name")
    )


class OrderDiscountSearchForm(forms.Form):
    number = forms.CharField(required=False, label=_("Order number"))
    status = forms.ChoiceField(required=False, label=_("Order status"), choices=[])
    date_from = forms.DateField(
        required=False, label=_("Date from"), widget=DatePickerInput
    )
    date_to = forms.DateField(
        required=False, label=_("Date to"), widget=DatePickerInput
    )
    product = forms.CharField(required=False, label=_("Product"))
    payment_method = forms.ChoiceField(
        required=False, label=_("Payment method"), choices=[]
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["status"].choices = self.get_order_status_choices()
        self.fields["payment_method"].choices = self.get_payment_method_choices()

    def get_order_status_choices(self):
        return [("", "---------")] + [(v, v) for v in Order.all_statuses()]

    def get_payment_method_choices(self):
        return [("", "---------")] + [
            (src.code, src.name) for src in SourceType.objects.all()
        ]

    def filter_queryset(self, qs):
        if not self.is_valid():
            return qs
        data = self.cleaned_data
        is_filtered = False
        if data.get("number"):
            qs = qs.filter(order__number__icontains=data["number"])
            is_filtered = True
        if data.get("status"):
            qs = qs.filter(order__status=data["status"])
            is_filtered = True
        if data.get("date_from"):
            qs = qs.filter(order__date_placed__gte=data["date_from"])
            is_filtered = True
        if data.get("date_to"):
            qs = qs.filter(order__date_placed__lte=data["date_to"])
            is_filtered = True
        if data.get("product"):
            qs = qs.filter(
                (
                    Q(order__lines__title__icontains=data["product"])
                    | Q(order__lines__upc__icontains=data["product"])  # NOQA
                    | Q(order__lines__partner_sku__icontains=data["product"])  # NOQA
                )
            )
            is_filtered = True
        if data.get("payment_method"):
            qs = qs.filter(order__sources__source_type__code=data["payment_method"])
            is_filtered = True
        return qs, is_filtered


class BenefitForm(forms.ModelForm):
    _benefit_classes = getattr(settings, "BLUELIGHT_BENEFIT_CLASSES", [])
    proxy_class = forms.ChoiceField(
        choices=_benefit_classes,
        required=True,
        label=_("Type"),
        help_text=_("Select a benefit type"),
    )

    class Meta:
        model = Benefit
        fields = ["range", "proxy_class", "value", "max_affected_items", "max_discount"]


class ConditionForm(forms.ModelForm):
    _condition_classes = getattr(settings, "BLUELIGHT_CONDITION_CLASSES", [])
    proxy_class = forms.ChoiceField(
        choices=_condition_classes,
        required=True,
        label=_("Type"),
        help_text=_("Select a condition type"),
    )

    class Meta:
        model = Condition
        fields = [
            "range",
            "proxy_class",
            "value",
        ]


class CompoundBenefitForm(forms.ModelForm):
    CPATH = "%s.%s" % (CompoundBenefit.__module__, CompoundBenefit.__name__)
    proxy_class = forms.ChoiceField(
        choices=((CPATH, _("Compound Benefit")),),
        initial=CPATH,
        disabled=True,
        label=_("Type"),
        help_text=_("Select a benefit type"),
    )

    class Meta:
        model = CompoundBenefit
        fields = ["proxy_class", "subbenefits", "max_discount"]


class CompoundConditionForm(forms.ModelForm):
    CPATH = "%s.%s" % (CompoundCondition.__module__, CompoundCondition.__name__)
    proxy_class = forms.ChoiceField(
        choices=((CPATH, _("Compound Condition")),),
        initial=CPATH,
        disabled=True,
        label=_("Type"),
        help_text=_("Select a condition type"),
    )

    class Meta:
        model = CompoundCondition
        fields = ["proxy_class", "conjunction", "subconditions"]


class MetaDataForm(forms.ModelForm):
    offer_group = forms.ModelChoiceField(
        label=_("Offer Group"),
        queryset=OfferGroup.objects.get_queryset(),
        help_text=_("Offer group to which this offer belongs"),
    )

    class Meta:
        model = ConditionalOffer
        fields = (
            "name",
            "short_name",
            "description",
            # Oscar puts offer_type on the metadata form, but we put it on the restrictions
            # form instead (due to it's ties to the user group limiting functionality).
            # "offer_type",
            "offer_group",
            "affects_cosmetic_pricing",
            "priority",
        )


class BenefitSelectionForm(forms.ModelForm):
    class Meta:
        model = ConditionalOffer
        fields = ("benefit",)


class ConditionSelectionForm(forms.ModelForm):
    class Meta:
        model = ConditionalOffer
        fields = ("condition",)


class RestrictionsForm(BaseRestrictionsForm):
    groups = forms.ModelMultipleChoiceField(
        label=_("User Groups"),
        queryset=Group.objects.get_queryset(),
        help_text=_("Which user groups will be able to apply this offer?"),
        required=False,
    )

    class Meta:
        model = ConditionalOffer
        fields = list(BaseRestrictionsForm.Meta.fields) + [
            "offer_type",
            "groups",
        ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["priority"].widget = forms.HiddenInput()
        self.fields["priority"].disabled = True
        self.fields["exclusive"].widget = forms.HiddenInput()
        self.fields["exclusive"].disabled = True
        self.fields["combinations"].widget = forms.HiddenInput()
        self.fields["combinations"].disabled = True

    def clean_offer_type(self):
        data = self.cleaned_data["offer_type"]
        if (
            (self.instance.pk is not None)
            and (self.instance.offer_type == ConditionalOffer.VOUCHER)
            and ("offer_type" in self.changed_data)
            and self.instance.vouchers.exists()
        ):
            raise forms.ValidationError(
                _("This can only be changed if it has no vouchers attached to it")
            )
        return data

    def clean(self):
        cleaned_data = super().clean()
        # If offer_type is _User_, require at least 1 group to be selected
        if cleaned_data["offer_type"] == ConditionalOffer.USER:
            if len(cleaned_data["groups"]) <= 0:
                raise forms.ValidationError(
                    {
                        "groups": _(
                            "User offers must have at least 1 user group selected."
                        )
                    }
                )
        # If offer_type is anything other than _User_, clear the groups field.
        else:
            cleaned_data["groups"] = []
        return cleaned_data


class OfferGroupForm(forms.ModelForm):
    offers = ModelMultipleChoiceField(
        queryset=ConditionalOffer.objects.order_by("name").all(),
        widget=forms.widgets.SelectMultiple(),
        required=False,
    )

    class Meta:
        model = OfferGroup
        fields = (
            "name",
            "priority",
            "offers",
        )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance:
            self.initial["offers"] = self.instance.offers.all()

    def save(self, *args, **kwargs):
        offer_group = super().save(*args, **kwargs)
        offer_group.offers.set(self.cleaned_data["offers"])
        return offer_group

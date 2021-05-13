from django import forms
from django.contrib.auth.models import Group
from django.utils.translation import gettext_lazy as _
from oscar.core.loading import get_model
from oscar.forms import widgets

Voucher = get_model("voucher", "Voucher")
Benefit = get_model("offer", "Benefit")
Condition = get_model("offer", "Condition")
Range = get_model("offer", "Range")
OfferGroup = get_model("offer", "OfferGroup")

MAX_CHILDREN_CREATE = 100_000


class VoucherForm(forms.Form):
    name = forms.CharField(label=_("Name"), max_length=128)
    description = forms.CharField(
        label=_("Description"), widget=forms.Textarea, required=False
    )
    code = forms.CharField(label=_("Code"))
    create_children = forms.BooleanField(
        label=_("Should child codes be created?"), required=False
    )
    auto_generate_child_count = forms.IntegerField(
        label=_("How many child codes should be created?"),
        initial=0,
        min_value=0,
        max_value=MAX_CHILDREN_CREATE,
        required=False,
    )
    start_datetime = forms.DateTimeField(
        label=_("Start datetime"), widget=widgets.DateTimePickerInput()
    )
    end_datetime = forms.DateTimeField(
        label=_("End datetime"), widget=widgets.DateTimePickerInput()
    )
    priority = forms.IntegerField(
        label=_("Priority"),
        initial=0,
        min_value=0,
        help_text=_("The highest priority vouchers are applied first"),
    )
    usage = forms.ChoiceField(label=_("Usage"), choices=Voucher.USAGE_CHOICES)
    limit_usage_by_group = forms.BooleanField(
        label=_("Should usage be limited to specific user groups?"), required=False
    )
    groups = forms.ModelMultipleChoiceField(
        label=_("User Group Whitelist"),
        help_text=_("Which user groups will be able to apply this offer?"),
        queryset=Group.objects.order_by("name"),
        required=False,
    )
    condition = forms.ModelChoiceField(
        label=_("Condition"),
        help_text=_(
            "In addition to entering the voucher code, what precondition (if any) must be met before this voucher is applied?"
        ),
        queryset=Condition.objects.get_queryset(),
        required=False,
    )
    desktop_image = forms.ImageField(
        label=_("Desktop Image"),
        help_text=_("Desktop image used for promo display."),
        required=False,
    )
    mobile_image = forms.ImageField(
        label=_("Mobile Image"),
        help_text=_("Mobile image used for promo display."),
        required=False,
    )
    benefit = forms.ModelChoiceField(
        label=_("Incentive"),
        help_text=_(
            "What benefit should be given to the customer as a result of this voucher code?"
        ),
        queryset=Benefit.objects.get_queryset(),
    )
    offer_group = forms.ModelChoiceField(
        label=_("Offer Group"),
        help_text=_("What group should this voucher belong to?"),
        queryset=OfferGroup.objects.get_queryset(),
    )
    max_global_applications = forms.IntegerField(
        label=_("Max global applications"),
        min_value=0,
        required=False,
        help_text=_(
            "The number of times this offer can be used before it is unavailable"
        ),
    )
    max_user_applications = forms.IntegerField(
        label=_("Max user applications"),
        min_value=0,
        required=False,
        help_text=_("The number of times a single user can use this offer"),
    )
    max_basket_applications = forms.IntegerField(
        label=_("Max basket applications"),
        min_value=0,
        required=False,
        help_text=_(
            "The number of times this offer can be applied to a basket (and order)"
        ),
    )
    max_discount = forms.DecimalField(
        label=_("Max discount"),
        min_value=0,
        decimal_places=2,
        max_digits=12,
        required=False,
        help_text=_(
            "When an offer has given more discount to orders than this threshold, then the offer becomes unavailable"
        ),
    )

    def __init__(self, voucher=None, *args, **kwargs):
        self.voucher = voucher
        super().__init__(*args, **kwargs)

    def clean_name(self):
        name = self.cleaned_data["name"].strip()
        if not name:
            raise forms.ValidationError(_("Please enter a voucher name"))
        qs = Voucher.objects
        if self.voucher:
            qs = qs.exclude(pk=self.voucher.pk)
        qs = qs.filter(parent=None)
        qs = qs.filter(name=name)
        if qs.count() > 0:
            raise forms.ValidationError(_("The name '%s' is already in use") % name)
        return name

    def clean_code(self):
        code = self.cleaned_data["code"].strip().upper()
        if not code:
            raise forms.ValidationError(_("Please enter a voucher code"))
        qs = Voucher.objects
        if self.voucher:
            qs = qs.exclude(pk=self.voucher.pk)
        qs = qs.filter(code=code)
        if qs.count() > 0:
            raise forms.ValidationError(_("The code '%s' is already in use") % code)
        return code

    def clean(self):
        cleaned_data = super().clean()
        start_datetime = cleaned_data.get("start_datetime")
        end_datetime = cleaned_data.get("end_datetime")
        if start_datetime and end_datetime and end_datetime < start_datetime:
            raise forms.ValidationError(_("The start date must be before the end date"))
        return cleaned_data


class AddChildCodesForm(forms.Form):
    _creation_type_choices = [
        ("auto", _("Auto-Generate Codes")),
        ("manual", _("Manually Enter Codes")),
    ]
    creation_type = forms.ChoiceField(
        label=_("Child Code Creation Mode"),
        help_text=_("What kind of child codes do you want to generate?"),
        choices=_creation_type_choices,
        widget=forms.RadioSelect,
    )
    auto_generate_count = forms.IntegerField(
        label=_("Auto-Generated Child Code Count"),
        help_text=_("How many random child codes should be created?"),
        required=False,
        initial=0,
        min_value=0,
        max_value=MAX_CHILDREN_CREATE,
    )
    custom_child_codes = forms.CharField(
        label=_("Custom Child Codes"),
        help_text=_(
            "Create custom child codes for this voucher by entering 1 code per line."
        ),
        required=False,
        widget=forms.Textarea(
            attrs={
                "cols": 20,
                "rows": 5,
            }
        ),
    )

    def clean_custom_child_codes(self):
        code_txt = self.cleaned_data["custom_child_codes"]
        codes = [code.strip() for code in code_txt.splitlines()]
        return codes

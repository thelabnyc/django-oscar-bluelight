from django import forms
from django.contrib.auth.models import Group
from django.utils.translation import gettext_lazy as _
from django.utils import timezone
from oscar.core.loading import get_model
from oscar.forms.widgets import DateTimePickerInput
from oscar.apps.dashboard.vouchers.forms import (
    VoucherForm as BaseVoucherForm,
)

Voucher = get_model("voucher", "Voucher")

MAX_CHILDREN_CREATE = 100_000


class VoucherForm(BaseVoucherForm):
    name = forms.CharField(
        label=_("Name"),
        required=True,
        max_length=128,
    )

    # Child Codes
    _child_creation_type_choices = [
        ("none", _("Don't Create Child Codes")),
        ("auto", _("Auto-Generate Child Codes")),
        ("manual", _("Manually Enter Child Codes")),
    ]
    child_creation_type = forms.ChoiceField(
        label=_("Create Child Codes?"),
        help_text=_("What kind of child codes do you want to generate?"),
        choices=_child_creation_type_choices,
        widget=forms.RadioSelect,
    )
    auto_generate_child_count = forms.IntegerField(
        label=_("How many child codes should be created?"),
        initial=0,
        min_value=0,
        max_value=MAX_CHILDREN_CREATE,
        required=False,
    )
    custom_child_codes = forms.CharField(
        label=_("Custom Child Codes"),
        help_text=_(
            "Create custom child codes for this voucher by entering 1 code per line."
        ),
        required=False,
        widget=forms.Textarea(
            attrs={
                "class": "no-widget-init",  # Prevent Oscar Js from making this a TinyMCE WSSIWYG field
                "cols": 20,
                "rows": 5,
            }
        ),
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

    class Meta(BaseVoucherForm.Meta):
        fields = BaseVoucherForm.Meta.fields + [
            "child_creation_type",
            "auto_generate_child_count",
            "custom_child_codes",
            "usage",
            "limit_usage_by_group",
            "groups",
        ]

    def clean_custom_child_codes(self):
        code_txt = self.cleaned_data["custom_child_codes"]
        codes = [code.strip() for code in code_txt.splitlines()]
        return codes


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


class CodeExportForm(forms.Form):
    date_from = forms.DateTimeField(
        required=False, label=_("Date from"), widget=DateTimePickerInput
    )
    date_to = forms.DateTimeField(
        required=False,
        label=_("Date to"),
        widget=DateTimePickerInput,
        initial=timezone.now(),
    )
    format_choices = (
        ("csv", _("CSV")),
        ("json", _("JSON")),
    )
    file_format = forms.ChoiceField(
        widget=forms.RadioSelect,
        required=True,
        choices=format_choices,
        initial="csv",
        label=_("Get results as"),
    )

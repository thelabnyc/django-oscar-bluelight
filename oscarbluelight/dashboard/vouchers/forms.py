from django import forms
from django.contrib.auth.models import Group
from django.utils.translation import ugettext_lazy as _
from oscar.core.loading import get_model
from oscar.forms import widgets

Voucher = get_model('voucher', 'Voucher')
Benefit = get_model('offer', 'Benefit')
Range = get_model('offer', 'Range')

MAX_CHILDREN_CREATE = 1000


class VoucherForm(forms.Form):
    name = forms.CharField(
        label=_("Name"))
    description = forms.CharField(
        label=_("Description"),
        widget=forms.Textarea,
        required=False)
    code = forms.CharField(
        label=_("Code"))
    create_children = forms.BooleanField(
        label=_('Should child codes be created?'),
        required=False)
    child_count = forms.IntegerField(
        label=_('How many child codes should be created?'),
        initial=0,
        min_value=0,
        max_value=MAX_CHILDREN_CREATE,
        required=False)
    start_datetime = forms.DateTimeField(
        label=_("Start datetime"),
        widget=widgets.DateTimePickerInput())
    end_datetime = forms.DateTimeField(
        label=_("End datetime"),
        widget=widgets.DateTimePickerInput())
    usage = forms.ChoiceField(
        label=_("Usage"),
        choices=Voucher.USAGE_CHOICES)
    limit_usage_by_group = forms.BooleanField(
        label=_('Should usage be limited to specific user groups?'),
        required=False)
    groups = forms.ModelMultipleChoiceField(
        label=_('User Group Whitelist'),
        queryset=Group.objects.order_by('name'),
        required=False)
    benefit = forms.ModelChoiceField(
        label=_('Incentive'),
        queryset=Benefit.objects.get_queryset())

    def __init__(self, voucher=None, *args, **kwargs):
        self.voucher = voucher
        super().__init__(*args, **kwargs)

    def clean_name(self):
        name = self.cleaned_data['name']
        try:
            voucher = Voucher.objects.get(name=name)
            if not self.voucher or voucher.id != self.voucher.id:
                raise forms.ValidationError(_("The name '%s' is already in use") % name)
        except Voucher.DoesNotExist:
            pass
        return name

    def clean_code(self):
        code = self.cleaned_data['code'].strip().upper()
        if not code:
            raise forms.ValidationError(_("Please enter a voucher code"))
        try:
            voucher = Voucher.objects.get(code=code)
            if not self.voucher or voucher.id != self.voucher.id:
                raise forms.ValidationError(_("The code '%s' is already in use") % code)
        except Voucher.DoesNotExist:
            pass
        return code

    def clean(self):
        cleaned_data = super().clean()
        start_datetime = cleaned_data.get('start_datetime')
        end_datetime = cleaned_data.get('end_datetime')
        if start_datetime and end_datetime and end_datetime < start_datetime:
            raise forms.ValidationError(_("The start date must be before the end date"))
        return cleaned_data


class AddChildCodesForm(forms.Form):
    child_count = forms.IntegerField(
        label=_('How many child codes should be created?'),
        initial=0,
        min_value=0,
        max_value=MAX_CHILDREN_CREATE)

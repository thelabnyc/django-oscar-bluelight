from django import forms
from django.contrib.auth.models import Group
from django.utils.translation import ugettext_lazy as _
from oscar.apps.dashboard.vouchers.forms import VoucherForm as DefaultVoucherForm
from oscar.core.loading import get_model

Voucher = get_model('voucher', 'Voucher')
Benefit = get_model('offer', 'Benefit')
Range = get_model('offer', 'Range')

MAX_CHILDREN_CREATE = 1000


class VoucherForm(DefaultVoucherForm):
    description = forms.CharField(
        label=_("Description"),
        widget=forms.Textarea,
        required=False)
    limit_usage_by_group = forms.BooleanField(
        label=_('Should usage be limited to specific user groups?'),
        required=False)
    groups = forms.ModelMultipleChoiceField(
        label=_('User Group Whitelist'),
        queryset=Group.objects.order_by('name'),
        required=False)
    create_children = forms.BooleanField(
        label=_('Should child codes be created?'),
        required=False)
    child_count = forms.IntegerField(
        label=_('How many child codes should be created?'),
        initial=0,
        min_value=0,
        max_value=MAX_CHILDREN_CREATE,
        required=False)


class AddChildCodesForm(forms.Form):
    child_count = forms.IntegerField(
        label=_('How many child codes should be created?'),
        initial=0,
        min_value=0,
        max_value=MAX_CHILDREN_CREATE)

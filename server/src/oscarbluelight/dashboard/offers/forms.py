from django import forms
from django.conf import settings
from django.contrib.auth.models import Group
from django.utils.translation import ugettext_lazy as _
from oscar.apps.dashboard.offers.forms import (
    MetaDataForm as BaseMetaDataForm,
    RestrictionsForm as BaseRestrictionsForm,
)
from django.forms import ModelMultipleChoiceField
from oscar.core.loading import get_model

ConditionalOffer = get_model('offer', 'ConditionalOffer')
Benefit = get_model('offer', 'Benefit')
CompoundCondition = get_model('offer', 'CompoundCondition')
Condition = get_model('offer', 'Condition')
Range = get_model('offer', 'Range')
OfferGroup = get_model('offer', 'OfferGroup')


class BenefitSearchForm(forms.Form):
    range = forms.ModelChoiceField(required=False, queryset=Range.objects.order_by('name'))


class ConditionSearchForm(forms.Form):
    range = forms.ModelChoiceField(required=False, queryset=Range.objects.order_by('name'))


class BenefitForm(forms.ModelForm):
    _benefit_classes = getattr(settings, 'BLUELIGHT_BENEFIT_CLASSES', [])
    proxy_class = forms.ChoiceField(
        choices=_benefit_classes,
        required=True,
        label=_('Type'),
        help_text='Select a benefit type')

    class Meta:
        model = Benefit
        fields = ['range', 'proxy_class', 'value', 'max_affected_items']


class ConditionForm(forms.ModelForm):
    _condition_classes = getattr(settings, 'BLUELIGHT_CONDITION_CLASSES', [])
    proxy_class = forms.ChoiceField(
        choices=_condition_classes,
        required=True,
        label=_('Type'),
        help_text='Select a condition type')

    class Meta:
        model = Condition
        fields = ['range', 'proxy_class', 'value', ]


class CompoundConditionForm(forms.ModelForm):
    CPATH = "%s.%s" % (CompoundCondition.__module__, CompoundCondition.__name__)
    proxy_class = forms.ChoiceField(
        choices=(
            (CPATH, 'Compound Condition'),
        ),
        initial=CPATH,
        disabled=True,
        label=_('Type'),
        help_text='Select a condition type')

    class Meta:
        model = CompoundCondition
        fields = ['proxy_class', 'conjunction', 'subconditions']


class MetaDataForm(BaseMetaDataForm):
    offer_group = forms.ModelChoiceField(
        label=_('Offer Group'),
        queryset=OfferGroup.objects.get_queryset(),
        help_text=_('Offer group to which this offer belongs'))

    apply_to_displayed_prices = forms.BooleanField(
        label=_("Apply offer to displayed product prices, before the product is added to a basket"),
        required=False)

    class Meta(BaseMetaDataForm.Meta):
        fields = ('name', 'short_name', 'description', 'offer_group', 'priority', 'apply_to_displayed_prices')


class BenefitSelectionForm(forms.ModelForm):
    class Meta:
        model = ConditionalOffer
        fields = ('benefit', )


class ConditionSelectionForm(forms.ModelForm):
    class Meta:
        model = ConditionalOffer
        fields = ('condition', )


class RestrictionsForm(BaseRestrictionsForm):
    limit_by_group = forms.BooleanField(
        label=_("Limit offer to selected user groups"),
        required=False)

    groups = forms.ModelMultipleChoiceField(
        label=_("User Groups"),
        queryset=Group.objects.get_queryset(),
        help_text=_("Which user groups will be able to apply this offer?"),
        required=False)

    class Meta:
        model = ConditionalOffer
        fields = ('start_datetime', 'end_datetime',
                  'limit_by_group', 'groups',
                  'max_basket_applications', 'max_user_applications',
                  'max_global_applications', 'max_discount')

    def clean(self):
        cleaned_data = super().clean()
        cleaned_data['limit_by_group'] = cleaned_data.get('limit_by_group', False)
        if not cleaned_data['limit_by_group']:
            cleaned_data['groups'] = []
        return cleaned_data


class OfferGroupForm(forms.ModelForm):
    offers = ModelMultipleChoiceField(
        queryset=ConditionalOffer.objects.order_by('name').all(),
        widget=forms.widgets.SelectMultiple(),
        required=False
    )

    class Meta:
        model = OfferGroup
        fields = ('name', 'priority', 'offers', )


    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance:
            self.initial['offers'] = self.instance.offers.all()


    def save(self, *args, **kwargs):
        offer_group = super().save(*args, **kwargs)
        offer_group.offers = self.cleaned_data['offers']
        return offer_group

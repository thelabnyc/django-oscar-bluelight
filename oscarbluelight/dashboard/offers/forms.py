from django import forms
from django.contrib.auth.models import Group
from django.utils.translation import ugettext_lazy as _
from oscar.apps.dashboard.offers.forms import (
    ConditionForm as BaseConditionForm,
    RestrictionsForm as BaseRestrictionsForm,
)
from oscar.core.loading import get_model

ConditionalOffer = get_model('offer', 'ConditionalOffer')
CompoundCondition = get_model('offer', 'CompoundCondition')
Condition = get_model('offer', 'Condition')
Range = get_model('offer', 'Range')


class ConditionForm(BaseConditionForm):
    def __init__(self, *args, **kwargs):
        forms.ModelForm.__init__(self, *args, **kwargs)

        conditions = Condition.objects.all()
        if len(conditions) > 0:
            # Initialize custom_condition field
            choices = [(c.id, str(c)) for c in conditions]
            choices.insert(0, ('', ' --------- '))
            self.fields['custom_condition'].choices = choices
            condition = kwargs.get('instance')
            if condition:
                self.fields['custom_condition'].initial = condition.id
        else:
            # No custom conditions and so the type/range/value fields
            # are no longer optional
            for field in ('type', 'range', 'value'):
                self.fields[field].required = True

        # Remove COMPOUND type from type choice dropdown
        def is_not_compound(choice):
            return choice[0] != Condition.COMPOUND
        self.fields['type'].choices = filter(is_not_compound, self.fields['type'].choices)


class ConditionSearchForm(forms.Form):
    range = forms.ModelChoiceField(required=False, queryset=Range.objects.order_by('name'))


class CompoundConditionForm(forms.ModelForm):
    class Meta:
        model = CompoundCondition
        fields = ['conjunction', 'subconditions']

    def save(self, *args, **kwargs):
        self.instance.type = Condition.COMPOUND
        return super().save(*args, **kwargs)


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

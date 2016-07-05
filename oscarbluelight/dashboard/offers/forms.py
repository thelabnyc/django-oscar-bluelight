from django import forms
from oscar.apps.dashboard.offers.forms import ConditionForm as BaseConditionForm
from oscar.core.loading import get_model

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

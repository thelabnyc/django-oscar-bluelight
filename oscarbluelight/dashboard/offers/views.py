from django.core.urlresolvers import reverse_lazy
from django.utils.translation import ugettext_lazy as _
from django.views.generic import DeleteView, ListView, CreateView, UpdateView
from oscar.core.loading import get_class, get_model

CompoundCondition = get_model('offer', 'CompoundCondition')
Condition = get_model('offer', 'Condition')

CompoundConditionForm = get_class('dashboard.offers.forms', 'CompoundConditionForm')
ConditionForm = get_class('dashboard.offers.forms', 'ConditionForm')
ConditionSearchForm = get_class('dashboard.offers.forms', 'ConditionSearchForm')


class ConditionListView(ListView):
    model = Condition
    context_object_name = 'conditions'
    template_name = 'dashboard/offers/condition_list.html'
    form_class = ConditionSearchForm

    def get_queryset(self):
        qs = self.model._default_manager.order_by('-id')

        self.description = _("All conditions")

        # We track whether the queryset is filtered to determine whether we
        # show the search form 'reset' button.
        self.is_filtered = False
        self.form = self.form_class(self.request.GET)
        if not self.form.is_valid():
            return qs

        data = self.form.cleaned_data
        if data['range']:
            qs = qs.filter(range=data['range'])
            self.description = _("Offers for range '%s'") % data['range']
            self.is_filtered = True
        return qs

    def get_context_data(self, **kwargs):
        ctx = super(ConditionListView, self).get_context_data(**kwargs)
        ctx['queryset_description'] = self.description
        ctx['form'] = self.form
        ctx['is_filtered'] = self.is_filtered
        return ctx


class ConditionDeleteView(DeleteView):
    model = Condition
    template_name = 'dashboard/offers/condition_delete.html'
    success_url = reverse_lazy('dashboard:condition-list')


class CompoundConditionCreateView(CreateView):
    model = CompoundCondition
    template_name = 'dashboard/offers/condition_edit_compound.html'
    form_class = CompoundConditionForm
    success_url = reverse_lazy('dashboard:condition-list')


class ConditionCreateView(CreateView):
    model = Condition
    template_name = 'dashboard/offers/condition_edit.html'
    form_class = ConditionForm
    success_url = reverse_lazy('dashboard:condition-list')


class ConditionUpdateView(UpdateView):
    model = Condition
    success_url = reverse_lazy('dashboard:condition-list')

    def get_object(self, queryset=None):
        obj = super(ConditionUpdateView, self).get_object(queryset)
        return obj.proxy()

    def get_form_class(self):
        if self.object.type == Condition.COMPOUND:
            return CompoundConditionForm
        return ConditionForm

    def get_template_names(self):
        if self.object.type == Condition.COMPOUND:
            return 'dashboard/offers/condition_edit_compound.html'
        return 'dashboard/offers/condition_edit.html'

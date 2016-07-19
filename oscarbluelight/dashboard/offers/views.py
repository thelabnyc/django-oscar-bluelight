from django.core import serializers
from django.core.urlresolvers import reverse_lazy
from django.utils.translation import ugettext_lazy as _
from django.views.generic import DeleteView, ListView, CreateView, UpdateView
from oscar.core.loading import get_class, get_model
from oscar.apps.dashboard.offers import views

ConditionalOffer = get_model('offer', 'ConditionalOffer')
CompoundCondition = get_model('offer', 'CompoundCondition')
Condition = get_model('offer', 'Condition')

CompoundConditionForm = get_class('dashboard.offers.forms', 'CompoundConditionForm')
ConditionForm = get_class('dashboard.offers.forms', 'ConditionForm')
ConditionSearchForm = get_class('dashboard.offers.forms', 'ConditionSearchForm')
MetaDataForm = get_class('dashboard.offers.forms', 'MetaDataForm')
BenefitForm = get_class('dashboard.offers.forms', 'BenefitForm')
RestrictionsForm = get_class('dashboard.offers.forms', 'RestrictionsForm')


class OfferWizardStepView(views.OfferWizardStepView):
    def _store_object(self, form):
        session_data = self.request.session.setdefault(self.wizard_name, {})

        # Get a transient model instance to save to the session
        instance = form.save(commit=False)

        # Filter out many-to-many fields from the serializer
        names = [f.name for f in instance._meta.get_fields() if not f.many_to_many]
        json_qs = serializers.serialize('json', [instance], fields=names)
        session_data[self._key(is_object=True)] = json_qs
        self.request.session.save()


class OfferMetaDataView(OfferWizardStepView):
    step_name = 'metadata'
    form_class = MetaDataForm
    template_name = 'dashboard/offers/metadata_form.html'
    url_name = 'dashboard:offer-metadata'
    success_url_name = 'dashboard:offer-benefit'

    def get_instance(self):
        return self.offer

    def get_title(self):
        return _("Name and description")


class OfferBenefitView(OfferWizardStepView):
    step_name = 'benefit'
    form_class = BenefitForm
    template_name = 'dashboard/offers/benefit_form.html'
    url_name = 'dashboard:offer-benefit'
    success_url_name = 'dashboard:offer-condition'
    previous_view = OfferMetaDataView

    def get_instance(self):
        return self.offer.benefit

    def get_title(self):
        # This is referred to as the 'incentive' within the dashboard.
        return _("Incentive")


class OfferConditionView(OfferWizardStepView):
    step_name = 'condition'
    form_class = ConditionForm
    template_name = 'dashboard/offers/condition_form.html'
    url_name = 'dashboard:offer-condition'
    success_url_name = 'dashboard:offer-restrictions'
    previous_view = OfferBenefitView

    def get_instance(self):
        return self.offer.condition


class OfferRestrictionsView(OfferWizardStepView):
    step_name = 'restrictions'
    form_class = RestrictionsForm
    template_name = 'dashboard/offers/restrictions_form.html'
    previous_view = OfferConditionView
    url_name = 'dashboard:offer-restrictions'

    def get_form_kwargs(self, *args, **kwargs):
        kwargs = super().get_form_kwargs(*args, **kwargs)
        offer = kwargs.get('instance')
        kwargs['initial'] = kwargs.get('initial', {})
        if offer:
            kwargs['initial']['limit_by_group'] = (offer.offer_type == ConditionalOffer.USER)
        return kwargs

    def save_offer(self, offer, form):
        # We update the offer with the name/description from step 1
        session_offer = self._fetch_session_offer()
        offer.name = session_offer.name
        offer.description = session_offer.description

        # Update offer type
        if form.cleaned_data['limit_by_group']:
            offer.offer_type = ConditionalOffer.USER
        else:
            offer.offer_type = ConditionalOffer.SITE

        # Save offer and m2m fields
        offer.save()
        form.save_m2m()
        return super().save_offer(offer)

    def form_valid(self, form):
        offer = form.save(commit=False)
        return self.save_offer(offer, form)

    def get_instance(self):
        return self.offer

    def get_title(self):
        return _("Restrictions")



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

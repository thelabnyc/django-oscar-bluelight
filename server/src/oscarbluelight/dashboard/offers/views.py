from django.contrib import messages
from django.core import serializers
from django.urls import reverse_lazy, reverse
from django.core.serializers.json import DjangoJSONEncoder
from django.http import HttpResponseRedirect
from django.utils.translation import gettext_lazy as _
from django.views.generic import DeleteView, ListView, CreateView, UpdateView
from oscar.core.loading import get_class, get_model
from oscar.apps.dashboard.offers.views import *  # noqa
from oscar.apps.dashboard.offers import views
import json

ConditionalOffer = get_model("offer", "ConditionalOffer")
CompoundBenefit = get_model("offer", "CompoundBenefit")
Benefit = get_model("offer", "Benefit")
CompoundCondition = get_model("offer", "CompoundCondition")
Condition = get_model("offer", "Condition")
OfferGroup = get_model("offer", "OfferGroup")
Voucher = get_model("voucher", "Voucher")

BenefitSearchForm = get_class("offers_dashboard.forms", "BenefitSearchForm")
BenefitForm = get_class("offers_dashboard.forms", "BenefitForm")
OfferGroupForm = get_class("offers_dashboard.forms", "OfferGroupForm")

ConditionSearchForm = get_class("offers_dashboard.forms", "ConditionSearchForm")
ConditionForm = get_class("offers_dashboard.forms", "ConditionForm")
CompoundBenefitForm = get_class("offers_dashboard.forms", "CompoundBenefitForm")
CompoundConditionForm = get_class("offers_dashboard.forms", "CompoundConditionForm")

OrderDiscountSearchForm = get_class("offers_dashboard.forms", "OrderDiscountSearchForm")
MetaDataForm = get_class("offers_dashboard.forms", "MetaDataForm")
BenefitSelectionForm = get_class("offers_dashboard.forms", "BenefitSelectionForm")
ConditionSelectionForm = get_class("offers_dashboard.forms", "ConditionSelectionForm")
RestrictionsForm = get_class("offers_dashboard.forms", "RestrictionsForm")


class OfferWizardStepView(views.OfferWizardStepView):
    def _store_form_kwargs(self, form):
        session_data = self.request.session.setdefault(self.wizard_name, {})
        # Adjust kwargs to avoid trying to save the instances
        form_data = form.cleaned_data.copy()
        for prop in ("range", "benefit", "condition", "offer_group"):
            obj = form_data.get(prop, None)
            if obj is not None:
                form_data[prop] = obj.id
        form_kwargs = {"data": form_data}
        json_data = json.dumps(form_kwargs, cls=DjangoJSONEncoder)
        session_data[self._key()] = json_data
        self.request.session.save()

    def _store_object(self, form):
        session_data = self.request.session.setdefault(self.wizard_name, {})

        # Get a transient model instance to save to the session
        instance = form.save(commit=False)

        # Filter out many-to-many fields from the serializer
        names = [f.name for f in instance._meta.get_fields() if not f.many_to_many]
        json_qs = serializers.serialize("json", [instance], fields=names)
        session_data[self._key(is_object=True)] = json_qs
        self.request.session.save()

    def get_instance(self):
        return self.offer

    def save_offer(self, offer, form):
        # We update the offer with the name/description from step 1
        session_offer = self._fetch_session_offer()
        offer.name = session_offer.name
        offer.short_name = session_offer.short_name
        offer.description = session_offer.description
        offer.offer_group = session_offer.offer_group
        offer.affects_cosmetic_pricing = session_offer.affects_cosmetic_pricing
        offer.priority = session_offer.priority

        # Save the related models and assign to the offer
        temp_offer = self._fetch_object("benefit")
        if temp_offer:
            benefit = temp_offer.benefit
            benefit.save()
            offer.benefit = benefit

        temp_offer = self._fetch_object("condition")
        if temp_offer:
            condition = temp_offer.condition
            condition.save()
            offer.condition = condition

        # Save offer and m2m fields
        offer.save()
        form.save_m2m()

        self._flush_session()

        if self.update:
            msg = _("Offer '%s' updated") % offer.name
        else:
            msg = _("Offer '%s' created!") % offer.name
        messages.success(self.request, msg)
        return HttpResponseRedirect(
            reverse("dashboard:offer-detail", kwargs={"pk": offer.pk})
        )

    def form_valid(self, form):
        self._store_form_kwargs(form)
        self._store_object(form)
        # Save changes to this offer when updating and pressed save button
        if self.update and "save" in form.data:
            return self.save_offer(self.offer, form)
        # Proceed to next page
        return super().form_valid(form)


class OfferMetaDataView(OfferWizardStepView):
    step_name = "metadata"
    form_class = MetaDataForm
    template_name = "oscar/dashboard/offers/metadata_form.html"
    url_name = "dashboard:offer-metadata"
    success_url_name = "dashboard:offer-benefit"

    def get_title(self):
        return _("Name and description")


class OfferBenefitView(OfferWizardStepView):
    step_name = "benefit"
    form_class = BenefitSelectionForm
    template_name = "oscar/dashboard/offers/benefit_selection_form.html"
    url_name = "dashboard:offer-benefit"
    success_url_name = "dashboard:offer-condition"
    previous_view = OfferMetaDataView

    def get_title(self):
        # This is referred to as the 'incentive' within the dashboard.
        return _("Incentive")


class OfferConditionView(OfferWizardStepView):
    step_name = "condition"
    form_class = ConditionSelectionForm
    template_name = "oscar/dashboard/offers/condition_selection_form.html"
    url_name = "dashboard:offer-condition"
    success_url_name = "dashboard:offer-restrictions"
    previous_view = OfferBenefitView


class OfferRestrictionsView(OfferWizardStepView):
    step_name = "restrictions"
    form_class = RestrictionsForm
    template_name = "oscar/dashboard/offers/restrictions_form.html"
    previous_view = OfferConditionView
    url_name = "dashboard:offer-restrictions"

    def get_form_kwargs(self, *args, **kwargs):
        kwargs = super().get_form_kwargs(*args, **kwargs)
        offer = kwargs.get("instance")
        kwargs["initial"] = kwargs.get("initial", {})
        if offer:
            kwargs["initial"]["limit_by_group"] = (
                offer.offer_type == ConditionalOffer.USER
            )
        return kwargs

    def save_offer(self, offer, form):
        # Update offer type
        if form.cleaned_data["limit_by_group"]:
            offer.offer_type = ConditionalOffer.USER
        else:
            offer.offer_type = ConditionalOffer.SITE

        # Save the offer
        super().save_offer(offer, form)

        # Redirect to the offer detail view
        return HttpResponseRedirect(
            reverse("dashboard:offer-detail", kwargs={"pk": offer.pk})
        )

    def form_valid(self, form):
        offer = form.save(commit=False)
        return self.save_offer(offer, form)

    def get_title(self):
        return _("Restrictions")


class OfferDetailView(views.OfferDetailView):
    form_class = OrderDiscountSearchForm

    def get_queryset(self):
        qs = super().get_queryset().order_by("-order__date_placed")
        self.form = self.form_class(self.request.GET)
        qs, is_filtered = self.form.filter_queryset(qs)
        self.is_filtered = is_filtered
        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["form"] = self.form
        ctx["is_filtered"] = self.is_filtered
        return ctx

    def render_to_response(self, context):
        if self.request.GET.get("format") == "csv":
            OrderDiscountCSVFormatter = get_class(
                "offers_dashboard.reports", "OrderDiscountCSVFormatter"
            )
            formatter = OrderDiscountCSVFormatter()
            qs = self.get_queryset().order_by("order__date_placed")
            return formatter.generate_response(qs, offer=self.offer)
        return super().render_to_response(context)


class BenefitListView(ListView):
    model = Benefit
    context_object_name = "benefits"
    template_name = "oscar/dashboard/offers/benefit_list.html"
    form_class = BenefitSearchForm

    def get_queryset(self):
        qs = (
            self.model._default_manager.select_related("range")
            .prefetch_related("offers", "parent_benefits")
            .order_by("-id")
        )

        self.description = _("All benefits")

        # We track whether the queryset is filtered to determine whether we
        # show the search form 'reset' button.
        self.is_filtered = False
        self.form = self.form_class(self.request.GET)
        if not self.form.is_valid():
            return qs

        data = self.form.cleaned_data
        if data["range"]:
            qs = qs.filter(range=data["range"])
            self.description = _("Benefits for range '%s'") % data["range"]
            self.is_filtered = True
        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["queryset_description"] = self.description
        ctx["form"] = self.form
        ctx["is_filtered"] = self.is_filtered
        return ctx


class BenefitDeleteView(DeleteView):
    model = Benefit
    template_name = "oscar/dashboard/offers/benefit_delete.html"
    success_url = reverse_lazy("dashboard:benefit-list")


class CompoundBenefitCreateView(CreateView):
    model = CompoundBenefit
    template_name = "oscar/dashboard/offers/benefit_edit_compound.html"
    form_class = CompoundBenefitForm
    success_url = reverse_lazy("dashboard:benefit-list")


class BenefitCreateView(CreateView):
    model = Benefit
    template_name = "oscar/dashboard/offers/benefit_edit.html"
    form_class = BenefitForm
    success_url = reverse_lazy("dashboard:benefit-list")


class BenefitUpdateView(UpdateView):
    model = Benefit
    success_url = reverse_lazy("dashboard:benefit-list")

    def get_object(self, queryset=None):
        obj = super().get_object(queryset)
        return obj.proxy()

    def get_form_class(self):
        if hasattr(self.object, "subbenefits"):
            return CompoundBenefitForm
        return BenefitForm

    def get_template_names(self):
        if hasattr(self.object, "subbenefits"):
            return "oscar/dashboard/offers/benefit_edit_compound.html"
        return "oscar/dashboard/offers/benefit_edit.html"


class ConditionListView(ListView):
    model = Condition
    context_object_name = "conditions"
    template_name = "oscar/dashboard/offers/condition_list.html"
    form_class = ConditionSearchForm

    def get_queryset(self):
        qs = (
            self.model._default_manager.select_related("range")
            .prefetch_related("offers", "parent_conditions")
            .order_by("-id")
        )

        self.description = _("All conditions")

        # We track whether the queryset is filtered to determine whether we
        # show the search form 'reset' button.
        self.is_filtered = False
        self.form = self.form_class(self.request.GET)
        if not self.form.is_valid():
            return qs

        data = self.form.cleaned_data
        if data["range"]:
            qs = qs.filter(range=data["range"])
            self.description = _("Conditions for range '%s'") % data["range"]
            self.is_filtered = True
        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["queryset_description"] = self.description
        ctx["form"] = self.form
        ctx["is_filtered"] = self.is_filtered
        return ctx


class ConditionDeleteView(DeleteView):
    model = Condition
    template_name = "oscar/dashboard/offers/condition_delete.html"
    success_url = reverse_lazy("dashboard:condition-list")


class CompoundConditionCreateView(CreateView):
    model = CompoundCondition
    template_name = "oscar/dashboard/offers/condition_edit_compound.html"
    form_class = CompoundConditionForm
    success_url = reverse_lazy("dashboard:condition-list")


class ConditionCreateView(CreateView):
    model = Condition
    template_name = "oscar/dashboard/offers/condition_edit.html"
    form_class = ConditionForm
    success_url = reverse_lazy("dashboard:condition-list")


class ConditionUpdateView(UpdateView):
    model = Condition
    success_url = reverse_lazy("dashboard:condition-list")

    def get_object(self, queryset=None):
        obj = super().get_object(queryset)
        return obj.proxy()

    def get_form_class(self):
        if hasattr(self.object, "subconditions"):
            return CompoundConditionForm
        return ConditionForm

    def get_template_names(self):
        if hasattr(self.object, "subconditions"):
            return "oscar/dashboard/offers/condition_edit_compound.html"
        return "oscar/dashboard/offers/condition_edit.html"


class OfferGroupCreateView(CreateView):
    model = OfferGroup
    template_name = "oscar/dashboard/offers/offergroup_edit.html"
    form_class = OfferGroupForm
    success_url = reverse_lazy("dashboard:offergroup-list")


class OfferGroupListView(ListView):
    model = OfferGroup
    template_name = "oscar/dashboard/offers/offergroup_list.html"


class OfferGroupDeleteView(DeleteView):
    model = OfferGroup
    template_name = "oscar/dashboard/offers/offergroup_delete.html"
    success_url = reverse_lazy("dashboard:offergroup-list")

    def get(self, request, *args, **kwargs):
        if not self._is_validate_delete(request):
            return HttpResponseRedirect(self.success_url)
        return super().get(request, *args, **kwargs)

    def delete(self, request, *args, **kwargs):
        if not self._is_validate_delete(request):
            return HttpResponseRedirect(self.success_url)
        return super().delete(request, *args, **kwargs)

    def _is_validate_delete(self, request):
        group = self.get_object()
        if group.is_system_group:
            messages.error(request, _("System Offer Groups Can Not Be Deleted"))
            return False
        if group.offers.count() > 0:
            messages.error(
                request, _("Offer Groups That Still Contain Offers Can Not Be Deleted")
            )
            return False
        return True


class OfferGroupUpdateView(UpdateView):
    model = OfferGroup
    template_name = "oscar/dashboard/offers/offergroup_edit.html"
    form_class = OfferGroupForm
    success_url = reverse_lazy("dashboard:offergroup-list")

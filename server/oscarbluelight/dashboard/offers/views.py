from __future__ import annotations

from typing import (
    TYPE_CHECKING,
    Any,
    Generic,
    Literal,
    NewType,
    TypedDict,
    TypeVar,
    cast,
    get_args,
)
import json

from django.contrib import messages
from django.core import serializers
from django.core.paginator import Paginator
from django.core.serializers.json import DjangoJSONEncoder
from django.http import HttpRequest, HttpResponse, HttpResponseRedirect, JsonResponse
from django.urls import reverse, reverse_lazy
from django.utils.translation import gettext_lazy as _
from django.views.generic import CreateView, DeleteView, ListView, UpdateView
from oscar.apps.dashboard.offers import views
from oscar.apps.dashboard.offers.views import *  # noqa
from oscar.core.loading import get_class

from oscarbluelight.offer.models import (
    Benefit,
    CompoundBenefit,
    CompoundCondition,
    Condition,
    ConditionalOffer,
    OfferGroup,
)

from .forms import (
    BenefitForm,
    BenefitSearchForm,
    BenefitSelectionForm,
    CompoundBenefitForm,
    CompoundConditionForm,
    ConditionForm,
    ConditionSearchForm,
    ConditionSelectionForm,
    MetaDataForm,
    OfferGroupForm,
    OfferSearchForm,
    OrderDiscountSearchForm,
    RestrictionsForm,
)

if TYPE_CHECKING:
    from django.db.models.query import QuerySet
    from django_stubs_ext import StrOrPromise
    from oscar.apps.order.models import OrderDiscount

T = TypeVar(
    "T",
    MetaDataForm,
    BenefitSelectionForm,
    ConditionSelectionForm,
    RestrictionsForm,
)
ConditionItemType = Literal["non_voucher_offers", "vouchers"]
ConditionItemPk = NewType("ConditionItemPk", int)
ConditionItemName = NewType("ConditionItemName", str)


class ConditionItem(TypedDict):
    pk: ConditionItemPk
    name: ConditionItemName


class OfferWizardStepView(  # type:ignore[no-redef]
    views.OfferWizardStepView,
    Generic[T],
):
    form_class: type[T]

    def _store_form_kwargs(self, form: T) -> None:
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

    def _store_object(self, form: T) -> None:
        session_data = self.request.session.setdefault(self.wizard_name, {})

        # Get a transient model instance to save to the session
        instance = form.save(commit=False)

        # Filter out many-to-many fields from the serializer
        names = [f.name for f in instance._meta.get_fields() if not f.many_to_many]
        json_qs = serializers.serialize("json", [instance], fields=names)
        session_data[self._key(is_object=True)] = json_qs
        self.request.session.save()

    def get_instance(self) -> ConditionalOffer:
        return self.offer

    def save_offer(self, offer: ConditionalOffer, form: T) -> HttpResponse:
        # We update the offer with the name/description from step 1
        session_offer = self._fetch_session_offer()
        offer.name = session_offer.name
        offer.short_name = session_offer.short_name
        offer.description = session_offer.description
        offer.desktop_image = session_offer.desktop_image
        offer.mobile_image = session_offer.mobile_image
        offer.offer_group = session_offer.offer_group
        offer.affects_cosmetic_pricing = session_offer.affects_cosmetic_pricing
        offer.priority = session_offer.priority

        # Since offer_type is moved from the metadata form to restrictions from,
        # check it is in the form or not in case of only Step 1 metadata form saving.
        offer.offer_type = (
            form.cleaned_data["offer_type"]
            if "offer_type" in form.cleaned_data
            else session_offer.offer_type
        )

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

    def form_valid(self, form: T) -> HttpResponse:
        self._store_form_kwargs(form)
        self._store_object(form)
        # Save changes to this offer when updating and pressed save button
        if self.update and "save" in form.data:
            return self.save_offer(self.offer, form)
        # Proceed to next page
        return super().form_valid(form)


class OfferMetaDataView(OfferWizardStepView):  # type:ignore[no-redef]
    step_name = "metadata"
    form_class = MetaDataForm
    template_name = "oscar/dashboard/offers/metadata_form.html"
    url_name = "dashboard:offer-metadata"
    success_url_name = "dashboard:offer-benefit"

    def get_title(self) -> StrOrPromise:
        return _("Name and description")


class OfferBenefitView(OfferWizardStepView):  # type:ignore[no-redef]
    step_name = "benefit"
    form_class = BenefitSelectionForm
    template_name = "oscar/dashboard/offers/benefit_selection_form.html"
    url_name = "dashboard:offer-benefit"
    success_url_name = "dashboard:offer-condition"
    previous_view = OfferMetaDataView

    def get_title(self) -> StrOrPromise:
        # This is referred to as the 'incentive' within the dashboard.
        return _("Incentive")


class OfferConditionView(OfferWizardStepView):  # type:ignore[no-redef]
    step_name = "condition"
    form_class = ConditionSelectionForm
    template_name = "oscar/dashboard/offers/condition_selection_form.html"
    url_name = "dashboard:offer-condition"
    success_url_name = "dashboard:offer-restrictions"
    previous_view = OfferBenefitView


class OfferListView(views.OfferListView):  # type:ignore[no-redef]
    form_class = OfferSearchForm

    def get_queryset(self) -> QuerySet[ConditionalOffer]:
        qs = super().get_queryset()
        if self.form.is_valid():
            offer_group_slug = self.form.cleaned_data["offer_group"]
            if offer_group_slug:
                qs = qs.filter(offer_group__slug=offer_group_slug).distinct()
                self.search_filters.append(
                    _('Offer Group matches "%s"') % offer_group_slug
                )
        return qs


class OfferRestrictionsView(OfferWizardStepView):  # type:ignore[no-redef]
    step_name = "restrictions"
    form_class = RestrictionsForm
    template_name = "oscar/dashboard/offers/restrictions_form.html"
    previous_view = OfferConditionView
    url_name = "dashboard:offer-restrictions"

    def save_offer(
        self, offer: ConditionalOffer, form: RestrictionsForm
    ) -> HttpResponse:
        # Save the offer
        super().save_offer(offer, form)

        # Redirect to the offer detail view
        return HttpResponseRedirect(
            reverse("dashboard:offer-detail", kwargs={"pk": offer.pk})
        )

    def form_valid(self, form: RestrictionsForm) -> HttpResponse:
        offer = form.save(commit=False)
        return self.save_offer(offer, form)

    def get_title(self) -> StrOrPromise:
        return _("Restrictions")


class OfferImageUpdateView(UpdateView):
    model = ConditionalOffer
    fields = [
        "desktop_image",
        "mobile_image",
    ]
    context_object_name = "offer"
    template_name = "oscar/dashboard/offers/image_form.html"

    def get_context_data(self, **kwargs: Any) -> dict[str, Any]:
        ctx = super().get_context_data(**kwargs)
        ctx["title"] = _("Update Offer Images")
        return ctx

    def get_success_url(self) -> str:
        return reverse("dashboard:offer-detail", kwargs={"pk": self.kwargs["pk"]})


class OfferDetailView(views.OfferDetailView):  # type:ignore[no-redef]
    form_class = OrderDiscountSearchForm

    def get_queryset(self) -> QuerySet[OrderDiscount]:
        qs = super().get_queryset().order_by("-order__date_placed")
        self.form = self.form_class(self.request.GET)
        qs, is_filtered = self.form.filter_queryset(qs)
        self.is_filtered = is_filtered
        return qs

    def get_context_data(self, **kwargs: Any) -> dict[str, Any]:
        ctx = super().get_context_data(**kwargs)
        ctx["form"] = self.form
        ctx["is_filtered"] = self.is_filtered
        return ctx

    def render_to_response(
        self, context: dict[str, Any], **response_kwargs: Any
    ) -> HttpResponse:
        if self.request.GET.get("format") == "csv":
            OrderDiscountCSVFormatter = get_class(
                "offers_dashboard.reports", "OrderDiscountCSVFormatter"
            )
            formatter = OrderDiscountCSVFormatter()
            qs = self.get_queryset().order_by("order__date_placed")
            return formatter.generate_response(qs, offer=self.offer)
        return super().render_to_response(context, **response_kwargs)


class BenefitListView(ListView):
    model = Benefit
    context_object_name = "benefits"
    template_name = "oscar/dashboard/offers/benefit_list.html"
    form_class = BenefitSearchForm
    paginate_by = 25

    def get_queryset(self) -> QuerySet[Benefit]:
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
        if data["benefit_type"]:
            qs = qs.filter(proxy_class=data["benefit_type"])
            self.is_filtered = True
        if data["min_value"] is not None:
            qs = qs.filter(value__gte=data["min_value"])
            self.is_filtered = True
        if data["max_value"] is not None:
            qs = qs.filter(value__lte=data["max_value"])
            self.is_filtered = True

        return qs

    def get_context_data(self, **kwargs: Any) -> dict[str, Any]:
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

    def get_object(self, queryset: QuerySet[Benefit] | None = None) -> Benefit:
        obj = super().get_object(queryset)
        return obj.proxy()

    def get_form_class(self) -> type[CompoundBenefitForm] | type[BenefitForm]:
        if hasattr(self.object, "subbenefits"):
            return CompoundBenefitForm
        return BenefitForm

    def get_template_names(self) -> list[str]:
        if hasattr(self.object, "subbenefits"):
            return ["oscar/dashboard/offers/benefit_edit_compound.html"]
        return ["oscar/dashboard/offers/benefit_edit.html"]


class ConditionListView(ListView):
    model = Condition
    context_object_name = "conditions"
    template_name = "oscar/dashboard/offers/condition_list.html"
    form_class = ConditionSearchForm
    items_per_object = 500

    def _get_items_for_condition(
        self, condition_pk: ConditionItemPk, item_type: ConditionItemType, page: int = 1
    ) -> dict[str, bool | list[ConditionItem]]:
        condition = self.model._default_manager.get(pk=condition_pk)
        items = getattr(condition, item_type)
        paginator = Paginator(items, self.items_per_object)
        current_page = paginator.get_page(page)
        return {
            "items": [
                ConditionItem(pk=item.pk, name=item.name) for item in current_page
            ],
            "has_next": current_page.has_next(),
        }

    def get(
        self, request: HttpRequest, *args: Any, **kwargs: Any
    ) -> HttpResponse | JsonResponse:
        if request.headers.get("X-Requested-With") == "XMLHttpRequest":
            condition_pk = request.GET.get("condition_pk")
            page = int(request.GET.get("page", 1))
            item_type = request.GET.get("type")
            if not condition_pk or not item_type:
                return JsonResponse(
                    {"error": "Missing required parameters: condition_pk, type"},
                    status=400,
                )
            if item_type not in get_args(ConditionItemType):
                return JsonResponse(
                    {"error": f"Invalid item type for Condition: {item_type}"},
                    status=400,
                )
            data = self._get_items_for_condition(
                ConditionItemPk(int(condition_pk)),
                cast(ConditionItemType, item_type),
                page,
            )
            return JsonResponse(data)
        return super().get(request, *args, **kwargs)

    def get_queryset(self) -> QuerySet[Condition]:
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

    def get_context_data(self, **kwargs: Any) -> dict[str, Any]:
        ctx = super().get_context_data(**kwargs)
        ctx["queryset_description"] = self.description
        ctx["form"] = self.form
        ctx["is_filtered"] = self.is_filtered
        # Add initial pages of offers and vouchers for each condition
        for condition in ctx["conditions"]:
            condition.initial_offers = self._get_items_for_condition(
                condition.id, "non_voucher_offers"
            )
            condition.initial_vouchers = self._get_items_for_condition(
                condition.id, "vouchers"
            )
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

    def get_object(self, queryset: QuerySet[Condition] | None = None) -> Condition:
        obj = super().get_object(queryset)
        return obj.proxy()

    def get_form_class(self) -> type[CompoundConditionForm] | type[ConditionForm]:
        if hasattr(self.object, "subconditions"):
            return CompoundConditionForm
        return ConditionForm

    def get_template_names(self) -> list[str]:
        if hasattr(self.object, "subconditions"):
            return ["oscar/dashboard/offers/condition_edit_compound.html"]
        return ["oscar/dashboard/offers/condition_edit.html"]


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

    def get(self, request: HttpRequest, *args: Any, **kwargs: Any) -> HttpResponse:
        if not self._is_validate_delete(request):
            return HttpResponseRedirect(self.success_url)
        return super().get(request, *args, **kwargs)

    def post(self, request: HttpRequest, *args: Any, **kwargs: Any) -> HttpResponse:
        if not self._is_validate_delete(request):
            return HttpResponseRedirect(self.success_url)
        return super().post(request, *args, **kwargs)

    def _is_validate_delete(self, request: HttpRequest) -> bool:
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

from django.conf import settings
from django.core.paginator import Paginator
from django.contrib import messages
from django.urls import reverse
from django.db import transaction
from django.http import HttpResponse, HttpResponseRedirect, Http404
from django.shortcuts import get_object_or_404
from django.utils.translation import gettext_lazy as _
from django.views import generic
from oscar.core.loading import get_class, get_model
from oscar.apps.dashboard.vouchers.views import *  # noqa
from oscar.apps.dashboard.vouchers.views import (
    VoucherListView as DefaultVoucherListView,
    VoucherCreateView as DefaultVoucherCreateView,
    VoucherStatsView as DefaultVoucherStatsView,
    VoucherUpdateView as DefaultVoucherUpdateView,
)
from oscarbluelight.voucher import tasks
import csv
import re

try:
    import simplejson
except ImportError:
    import json as simplejson

Benefit = get_model("offer", "Benefit")
Condition = get_model("offer", "Condition")
ConditionalOffer = get_model("offer", "ConditionalOffer")
Voucher = get_model("voucher", "Voucher")
OrderDiscount = get_model("order", "OrderDiscount")

AddChildCodesForm = get_class("vouchers_dashboard.forms", "AddChildCodesForm")
VoucherForm = get_class("vouchers_dashboard.forms", "VoucherForm")
OrderDiscountSearchForm = get_class("offers_dashboard.forms", "OrderDiscountSearchForm")

BLUELIGHT_OFFER_IMAGE_FOLDER = getattr(settings, "BLUELIGHT_OFFER_IMAGE_FOLDER")


class VoucherListView(DefaultVoucherListView):
    def get_queryset(self):
        qs = super().get_queryset()
        return qs.exclude_children()


class VoucherCreateView(DefaultVoucherCreateView):
    form_class = VoucherForm

    def form_valid(self, form):
        with transaction.atomic():
            # Create offer and benefit
            benefit = form.cleaned_data["benefit"]
            condition = form.cleaned_data["condition"]
            if not condition:
                condition = Condition.objects.create(
                    range=benefit.range,
                    proxy_class="oscarbluelight.offer.conditions.BluelightCountCondition",
                    value=1,
                )
            name = form.cleaned_data["name"]
            offer = ConditionalOffer.objects.create(
                name=_("Offer for voucher '%s'") % name,
                short_name=form.cleaned_data["code"],
                description=form.cleaned_data["description"],
                offer_type=ConditionalOffer.VOUCHER,
                benefit=benefit,
                condition=condition,
                mobile_image=form.cleaned_data["mobile_image"],
                desktop_image=form.cleaned_data["desktop_image"],
                offer_group=form.cleaned_data["offer_group"],
                priority=form.cleaned_data["priority"],
                max_global_applications=form.cleaned_data["max_global_applications"],
                max_user_applications=form.cleaned_data["max_user_applications"],
                max_basket_applications=form.cleaned_data["max_basket_applications"],
                max_discount=form.cleaned_data["max_discount"],
            )
            voucher = Voucher.objects.create(
                name=name,
                code=form.cleaned_data["code"],
                usage=form.cleaned_data["usage"],
                start_datetime=form.cleaned_data["start_datetime"],
                end_datetime=form.cleaned_data["end_datetime"],
                limit_usage_by_group=form.cleaned_data["limit_usage_by_group"],
            )
            voucher.groups.set(form.cleaned_data["groups"])
            voucher.save()
            voucher.offers.add(offer)

        # Create child codes
        if form.cleaned_data["create_children"]:
            tasks.add_child_codes.apply_async(
                args=(voucher.pk,),
                kwargs={
                    "auto_generate_count": form.cleaned_data[
                        "auto_generate_child_count"
                    ],
                },
                countdown=1,
            )
            messages.success(
                self.request,
                _("Creating %s child codes…")
                % form.cleaned_data["auto_generate_child_count"],
            )

        return HttpResponseRedirect(self.get_success_url())


class VoucherStatsView(DefaultVoucherStatsView):
    form_class = OrderDiscountSearchForm

    def get_related_order_discounts(self):
        ids = [self.object.id] + [c.id for c in self.object.children.all()]
        qs = OrderDiscount.objects.filter(voucher_id__in=ids).order_by(
            "-order__date_placed"
        )
        self.form = self.form_class(self.request.GET)
        qs, is_filtered = self.form.filter_queryset(qs)
        self.is_filtered = is_filtered
        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        # Child vouchers
        ctx["children"] = self.object.children.order_by("code")
        # Related orders
        discounts = self.get_related_order_discounts()
        paginator = Paginator(discounts, settings.OSCAR_DASHBOARD_ITEMS_PER_PAGE)
        ctx["is_paginated"] = True
        ctx["paginator"] = paginator
        ctx["page_obj"] = paginator.get_page(self.request.GET.get("page", 1))
        ctx["discounts"] = ctx["page_obj"]
        ctx["form"] = self.form
        ctx["is_filtered"] = self.is_filtered
        return ctx

    def render_to_response(self, context):
        if self.request.GET.get("format") == "csv":
            OrderDiscountCSVFormatter = get_class(
                "offers_dashboard.reports", "OrderDiscountCSVFormatter"
            )
            formatter = OrderDiscountCSVFormatter()
            qs = self.get_related_order_discounts().order_by("order__date_placed")
            return formatter.generate_response(qs, offer=self.object.offers.first())
        return super().render_to_response(context)


class VoucherUpdateView(DefaultVoucherUpdateView):
    form_class = VoucherForm

    def get_initial(self):
        voucher = self.get_voucher()
        initial = {
            "name": voucher.name,
            "code": voucher.code,
            "start_datetime": voucher.start_datetime,
            "end_datetime": voucher.end_datetime,
            "usage": voucher.usage,
            "limit_usage_by_group": voucher.limit_usage_by_group,
            "groups": voucher.groups.all(),
        }

        offer = voucher.offers.first()
        if offer:
            initial["priority"] = offer.priority
            initial["offer_group"] = offer.offer_group
            initial["max_global_applications"] = offer.max_global_applications
            initial["max_user_applications"] = offer.max_user_applications
            initial["max_basket_applications"] = offer.max_basket_applications
            initial["max_discount"] = offer.max_discount
            initial["desktop_image"] = offer.desktop_image
            initial["mobile_image"] = offer.mobile_image
            initial["condition"] = offer.condition
            initial["benefit"] = offer.benefit
            initial["description"] = offer.description

        return initial

    @transaction.atomic
    def form_valid(self, form):
        voucher = self.get_voucher()
        voucher.name = form.cleaned_data["name"]
        voucher.code = form.cleaned_data["code"]
        voucher.usage = form.cleaned_data["usage"]
        voucher.start_datetime = form.cleaned_data["start_datetime"]
        voucher.end_datetime = form.cleaned_data["end_datetime"]
        voucher.limit_usage_by_group = form.cleaned_data["limit_usage_by_group"]
        voucher.groups.set(form.cleaned_data["groups"])
        voucher.save()

        benefit = form.cleaned_data["benefit"]
        condition = form.cleaned_data["condition"]
        if not condition:
            condition = Condition.objects.get_or_create(
                range=benefit.range,
                proxy_class="oscarbluelight.offer.conditions.BluelightCountCondition",
                value=1,
            )[0]

        offer = voucher.offers.first()
        if not offer:
            offer = ConditionalOffer(
                name=_("Offer for voucher '%s'") % voucher.name,
                offer_type=ConditionalOffer.VOUCHER,
            )

        offer.desktop_image = form.cleaned_data["desktop_image"]
        offer.mobile_image = form.cleaned_data["mobile_image"]
        offer.short_name = form.cleaned_data["code"]
        offer.description = form.cleaned_data["description"]
        offer.condition = condition
        offer.benefit = benefit
        offer.offer_group = form.cleaned_data["offer_group"]
        offer.priority = form.cleaned_data["priority"]
        offer.max_global_applications = form.cleaned_data["max_global_applications"]
        offer.max_user_applications = form.cleaned_data["max_user_applications"]
        offer.max_basket_applications = form.cleaned_data["max_basket_applications"]
        offer.max_discount = form.cleaned_data["max_discount"]
        offer.save()

        voucher.offers.add(offer)

        return HttpResponseRedirect(self.get_success_url())


class AddChildCodesView(generic.FormView):
    template_name = "oscar/dashboard/vouchers/voucher_add_children.html"
    model = Voucher
    form_class = AddChildCodesForm

    _bg_task_threshold = 1000

    def get_voucher(self):
        return get_object_or_404(Voucher, id=self.kwargs["pk"])

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["voucher"] = self.get_voucher()
        return ctx

    @transaction.atomic
    def form_valid(self, form):
        voucher = self.get_voucher()
        # Start a background job to create the child codes
        auto_generate_count = form.cleaned_data.get("auto_generate_count") or 0
        custom_child_codes = form.cleaned_data.get("custom_child_codes") or []
        # Add messages to inform the user what's happening
        if auto_generate_count and auto_generate_count > 0:
            messages.info(
                self.request,
                _("Auto-generating %s child codes…") % auto_generate_count,
            )
        if len(custom_child_codes) > 0:
            messages.info(
                self.request,
                _("Saving %s custom child codes…") % len(custom_child_codes),
            )
        # Create the codes
        create_args = (voucher.pk,)
        create_kwargs = {
            "auto_generate_count": auto_generate_count,
            "custom_codes": custom_child_codes,
        }
        # Only start a bg task if a lot of codes were requested.
        total_requested_codes = auto_generate_count + len(custom_child_codes)
        if total_requested_codes >= self._bg_task_threshold:
            tasks.add_child_codes.apply_async(
                args=create_args, kwargs=create_kwargs, countdown=1
            )
        else:
            errors, success_count = tasks.add_child_codes(*create_args, **create_kwargs)
            for error in errors:
                messages.error(self.request, error)
            messages.success(
                self.request,
                _("Successfully saved %s new child codes!") % success_count,
            )
        # Redirect back to the voucher stats page
        return HttpResponseRedirect(self.get_success_url())

    def get_success_url(self):
        return reverse("dashboard:voucher-stats", args=(self.kwargs["pk"],))


class ExportChildCodesView(generic.DetailView):
    model = Voucher

    def get(self, request, format, *args, **kwargs):
        formats = {
            "csv": self._render_csv,
            "json": self._render_json,
        }
        if format not in formats:
            raise Http404()

        voucher = self.get_object()
        filename = re.sub(r"[^a-z0-9\_\-]+", "_", voucher.name.lower())
        children = voucher.children.order_by("code")
        return formats[format](filename, children)

    def _render_csv(self, filename, children):
        response = HttpResponse(content_type="text/csv")
        response["Content-Disposition"] = 'attachment; filename="%s.csv"' % filename
        writer = csv.writer(response)
        writer.writerow([_("Codes")])
        for child in children.all():
            writer.writerow([child.code])
        return response

    def _render_json(self, filename, children):
        response = HttpResponse(content_type="application/json")
        response["Content-Disposition"] = 'attachment; filename="%s.json"' % filename
        codes = [c.code for c in children.all()]
        data = simplejson.dumps({"codes": codes})
        response.write(data)
        return response

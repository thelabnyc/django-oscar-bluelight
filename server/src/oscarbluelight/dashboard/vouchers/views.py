from django.conf import settings
from django.core.paginator import Paginator
from django.contrib import messages
from django.urls import reverse
from django.db import transaction
from django.db.models import Count
from django.http import (
    HttpResponse,
    HttpResponseRedirect,
    Http404,
    HttpResponseBadRequest,
)
from django.shortcuts import get_object_or_404, redirect
from django.utils.translation import gettext_lazy as _
from django.utils.http import urlencode
from django.utils import timezone
from django.views import generic
from oscar.views.generic import BulkEditMixin
from oscar.core.loading import get_class, get_model
from oscar.apps.dashboard.vouchers.views import *  # noqa
from oscar.apps.dashboard.vouchers.views import (
    VoucherListView as DefaultVoucherListView,
    VoucherCreateView as DefaultVoucherCreateView,
    VoucherStatsView as DefaultVoucherStatsView,
    VoucherUpdateView as DefaultVoucherUpdateView,
)
from oscar.apps.dashboard.vouchers.forms import VoucherSearchForm
from oscar.views import sort_queryset
from oscarbluelight.voucher import tasks
from datetime import datetime
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
Order = get_model("order", "Order")

AddChildCodesForm = get_class("vouchers_dashboard.forms", "AddChildCodesForm")
VoucherForm = get_class("vouchers_dashboard.forms", "VoucherForm")
OrderDiscountSearchForm = get_class("offers_dashboard.forms", "OrderDiscountSearchForm")
CodeExportForm = get_class("vouchers_dashboard.forms", "CodeExportForm")

BLUELIGHT_OFFER_IMAGE_FOLDER = getattr(settings, "BLUELIGHT_OFFER_IMAGE_FOLDER")
CHILD_CODE_BG_TASK_THRESHOLD = 1000


def _create_child_codes(request, voucher, auto_generate_count, custom_child_codes):
    """
    Create child codes for the given voucher and message the user about the process.
    """
    if auto_generate_count and auto_generate_count > 0:
        messages.info(
            request,
            _("Auto-generating %s child codes…") % auto_generate_count,
        )
    if len(custom_child_codes) > 0:
        messages.info(
            request,
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
    if total_requested_codes >= CHILD_CODE_BG_TASK_THRESHOLD:
        tasks.add_child_codes.apply_async(
            args=create_args, kwargs=create_kwargs, countdown=1
        )
    else:
        errors, success_count = tasks.add_child_codes(*create_args, **create_kwargs)
        for error in errors:
            messages.error(request, error)
        messages.success(
            request,
            _("Successfully saved %s new child codes!") % success_count,
        )


class VoucherListView(DefaultVoucherListView):
    def get_queryset(self):
        qs = super().get_queryset()
        return qs.exclude_children()


class VoucherCreateView(DefaultVoucherCreateView):
    form_class = VoucherForm

    def form_valid(self, form):
        with transaction.atomic():
            response = super().form_valid(form)
            self.object.groups.add(*form.cleaned_data["groups"])
        # Create child codes
        if form.cleaned_data.get("child_creation_type") != "none":
            auto_generate_count = (
                form.cleaned_data.get("auto_generate_child_count") or 0
            )
            custom_child_codes = form.cleaned_data.get("custom_child_codes") or []
            _create_child_codes(
                self.request, self.object, auto_generate_count, custom_child_codes
            )
        return response


class VoucherStatsView(DefaultVoucherStatsView):
    form_class = OrderDiscountSearchForm

    def get_related_order_discounts(self):
        # Have to manually write this sub query in order to get reasonable
        # performance with large voucher counts.
        subquery_sql = """
        SELECT d.id
          FROM {order_orderdiscount} d
          LEFT JOIN {voucher_voucher} v
            ON v.id = d.voucher_id
         WHERE d.voucher_id = %s
            OR v.parent_id = %s
            """.strip().format(
            order_orderdiscount=OrderDiscount._meta.db_table,
            order_order=Order._meta.db_table,
            voucher_voucher=Voucher._meta.db_table,
        )
        qs = (
            OrderDiscount.objects.extra(
                where=[f'"{OrderDiscount._meta.db_table}"."id" IN ({subquery_sql})'],
                params=[self.object.id, self.object.id],
            )
            .select_related("order")
            .order_by("-order__date_placed")
        )
        self.form = self.form_class(self.request.GET)
        qs, is_filtered = self.form.filter_queryset(qs)
        self.is_filtered = is_filtered
        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        # Child vouchers
        ctx["children"] = self.object.list_children().order_by("code")
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
        initial = super().get_initial()
        initial["groups"] = self.object.groups.all()
        return initial

    @transaction.atomic
    def form_valid(self, form):
        response = super().form_valid(form)
        self.object.groups.set(form.cleaned_data["groups"])
        return response


class AddChildCodesView(generic.FormView):
    template_name = "oscar/dashboard/vouchers/voucher_add_children.html"
    model = Voucher
    form_class = AddChildCodesForm

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
        _create_child_codes(
            self.request, voucher, auto_generate_count, custom_child_codes
        )
        # Redirect back to the voucher stats page
        return HttpResponseRedirect(self.get_success_url())

    def get_success_url(self):
        return reverse("dashboard:voucher-stats", args=(self.kwargs["pk"],))


class ExportChildCodesView(generic.DetailView):
    model = Voucher

    def get(self, request, file_format, *args, **kwargs):
        formats = {
            "csv": self._render_csv,
            "json": self._render_json,
        }
        if file_format not in formats:
            raise Http404()
        date_from = request.GET.get("date_from", "")
        date_to = request.GET.get("date_to", "")
        if date_from and date_to:
            self._filters = {"date_created__range": [date_from, date_to]}
        elif date_from and not date_to:
            self._filters = {"date_created__gte": date_from}
        elif not date_from and date_to:
            self._filters = {"date_created__lte": date_to}
        else:
            self._filters = {}

        voucher = self.get_object()
        filename = re.sub(r"[^a-z0-9\_\-]+", "_", voucher.name.lower())
        codes = (
            voucher.list_children()
            .filter(**self._filters)
            .order_by("code")
            .values_list("code", "date_created")
        )
        return formats[file_format](filename, codes)

    def _render_csv(self, filename, codes):
        response = HttpResponse(content_type="text/csv")
        response["Content-Disposition"] = 'attachment; filename="%s.csv"' % filename
        writer = csv.writer(response)
        writer.writerow([_("Codes"), _("Date Created")])
        for code, date_created in codes:
            date_created = datetime.strftime(date_created, "%b %d, %Y, %H:%M %p")
            writer.writerow([code, date_created])
        return response

    def _render_json(self, filename, codes):
        response = HttpResponse(content_type="application/json")
        response["Content-Disposition"] = 'attachment; filename="%s.json"' % filename
        data = simplejson.dumps({"codes": [code[0] for code in codes]})
        response.write(data)
        return response


class ExportChildCodesFormView(generic.FormView):
    template_name = "oscar/dashboard/vouchers/voucher_export_children.html"
    form_class = CodeExportForm

    def dispatch(self, request, pk, *args, **kwargs):
        self.parent = get_object_or_404(Voucher, pk=pk)
        if not self.request.GET:
            self.form = self.form_class(initial=self.get_initial())
            return super().dispatch(request, pk, *args, **kwargs)
        self.form = self.form_class(self.request.GET, initial=self.get_initial())
        if not self.form.is_valid():
            return super().dispatch(request, pk, *args, **kwargs)
        self.file_format = self.form.cleaned_data.get("file_format") or "csv"
        query_kwargs = {
            "date_from": self.form.cleaned_data.get("date_from") or "",
            "date_to": self.form.cleaned_data.get("date_to") or "",
        }
        return redirect(self.get_success_url(query_kwargs))

    def get_initial(self):
        try:
            most_recent_creation = self.get_created_on_counts()[0]
            date_from = most_recent_creation["date_created__date"]
        except IndexError:
            date_from = None
        initial = {
            "date_from": date_from,
            "date_to": timezone.now(),
            "file_format": "csv",
        }
        return initial

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["parent_voucher"] = self.parent
        ctx["form"] = self.form
        ctx["created_on_counts"] = self.get_created_on_counts()[:100]
        return ctx

    def get_success_url(self, query_kwargs=None):
        url = reverse(
            "dashboard:voucher-export-children-file",
            kwargs={
                "pk": self.parent.pk,
                "file_format": self.file_format,
            },
        )
        if query_kwargs:
            return f"{url}?{urlencode(query_kwargs)}"
        return url

    def get_created_on_counts(self):
        created_on_counts = (
            self.parent.children.values(
                "date_created__date",
            )
            .annotate(num_codes=Count("code", distinct=True))
            .order_by("-date_created__date")
        )
        return created_on_counts


class ChildCodesListView(BulkEditMixin, generic.ListView):
    model = Voucher
    context_object_name = "vouchers"
    template_name = "oscar/dashboard/vouchers/voucher_list_children.html"
    form_class = VoucherSearchForm
    paginate_by = settings.OSCAR_DASHBOARD_ITEMS_PER_PAGE
    actions = ("delete_selected_codes",)

    def dispatch(self, request, parent_pk, *args, **kwargs):
        self.parent = get_object_or_404(Voucher, pk=parent_pk)
        return super().dispatch(request, parent_pk, *args, **kwargs)

    def get_queryset(self):
        self.search_filters = []
        qs = super().get_queryset().filter(parent=self.parent)
        qs = sort_queryset(
            qs,
            self.request,
            ["num_basket_additions", "num_orders", "date_created"],
            "-date_created",
        )

        if not self.request.GET:
            self.form = self.form_class()
            return qs

        self.form = self.form_class(self.request.GET)
        if not self.form.is_valid():
            return qs

        code = self.form.cleaned_data.get("code", None)
        if code:
            qs = qs.filter(code__icontains=code)
            self.search_filters.append(_('Code matches "%s"') % code)
        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["parent_voucher"] = self.parent
        ctx["form"] = self.form
        ctx["search_filters"] = self.search_filters
        return ctx

    def delete_selected_codes(self, request, vouchers):
        for voucher in vouchers:
            voucher.delete()
        msg = _("Deleted %s child voucher codes") % len(vouchers)
        messages.info(request, msg)
        return redirect("dashboard:voucher-list-children", parent_pk=self.parent.pk)


class VoucherSuspensionView(generic.View):
    def post(self, request, pk, *args, **kwargs):
        self.voucher = get_object_or_404(Voucher, pk=pk)
        action = request.POST.get("action")
        if action == "suspend":
            return self.suspend()
        elif action == "unsuspend":
            return self.unsuspend()
        return HttpResponseBadRequest()

    def suspend(self):
        if self.voucher.is_suspended:
            messages.error(self.request, _("Voucher is already suspended"))
        else:
            self.voucher.suspend()
            messages.success(self.request, _("Voucher suspended"))
        return HttpResponseRedirect(self.get_success_url())

    def unsuspend(self):
        if not self.voucher.is_suspended:
            messages.error(
                self.request,
                _("Voucher cannot be reinstated as it is not currently suspended"),
            )
        else:
            self.voucher.unsuspend()
            messages.success(self.request, _("Voucher reinstated"))
        return HttpResponseRedirect(self.get_success_url())

    def get_success_url(self):
        url = reverse(
            "dashboard:voucher-stats",
            kwargs={
                "pk": self.voucher.pk,
            },
        )
        return url

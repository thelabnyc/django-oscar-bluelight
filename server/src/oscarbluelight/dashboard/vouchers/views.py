from django.contrib import messages
from django.core.urlresolvers import reverse
from django.db import transaction
from django.http import HttpResponse, HttpResponseRedirect, Http404
from django.shortcuts import get_object_or_404
from django.utils.translation import ugettext_lazy as _
from django.views import generic
from oscar.core.loading import get_class, get_model
from oscar.apps.dashboard.vouchers.views import (
    VoucherListView as DefaultVoucherListView,
    VoucherCreateView as DefaultVoucherCreateView,
    VoucherStatsView as DefaultVoucherStatsView,
    VoucherUpdateView as DefaultVoucherUpdateView
)
from oscarbluelight.voucher import tasks
import csv
import re

try:
    import simplejson
except ImportError:
    import json as simplejson

Benefit = get_model('offer', 'Benefit')
Condition = get_model('offer', 'Condition')
ConditionalOffer = get_model('offer', 'ConditionalOffer')
Voucher = get_model('voucher', 'Voucher')
OrderDiscount = get_model('order', 'OrderDiscount')

AddChildCodesForm = get_class('dashboard.vouchers.forms', 'AddChildCodesForm')
VoucherForm = get_class('dashboard.vouchers.forms', 'VoucherForm')


class VoucherListView(DefaultVoucherListView):
    def get_queryset(self):
        qs = super().get_queryset()
        return qs.exclude_children()


class VoucherCreateView(DefaultVoucherCreateView):
    form_class = VoucherForm

    def form_valid(self, form):
        with transaction.atomic():
            # Create offer and benefit
            benefit = form.cleaned_data['benefit']
            condition = form.cleaned_data['condition']
            if not condition:
                condition = Condition.objects.create(
                    range=benefit.range,
                    proxy_class='oscarbluelight.offer.conditions.BluelightCountCondition',
                    value=1)
            name = form.cleaned_data['name']
            offer = ConditionalOffer.objects.create(
                name=_("Offer for voucher '%s'") % name,
                short_name=form.cleaned_data['code'],
                description=form.cleaned_data['description'],
                offer_type=ConditionalOffer.VOUCHER,
                benefit=benefit,
                condition=condition,
                offer_group=form.cleaned_data['offer_group'],
                priority=form.cleaned_data['priority'],
                max_global_applications=form.cleaned_data['max_global_applications'],
                max_user_applications=form.cleaned_data['max_user_applications'],
                max_basket_applications=form.cleaned_data['max_basket_applications'],
                max_discount=form.cleaned_data['max_discount'])
            voucher = Voucher.objects.create(
                name=name,
                code=form.cleaned_data['code'],
                usage=form.cleaned_data['usage'],
                start_datetime=form.cleaned_data['start_datetime'],
                end_datetime=form.cleaned_data['end_datetime'],
                limit_usage_by_group=form.cleaned_data['limit_usage_by_group'],
            )
            voucher.groups = form.cleaned_data['groups']
            voucher.save()
            voucher.offers.add(offer)

        # Create child codes
        if form.cleaned_data['create_children']:
            tasks.add_child_codes.apply_async(args=(voucher.pk, form.cleaned_data['child_count']), countdown=1)
            messages.success(self.request, _("Creating %s child codes…") % form.cleaned_data['child_count'])

        return HttpResponseRedirect(self.get_success_url())


class VoucherStatsView(DefaultVoucherStatsView):
    MAX_DISPLAYED_ORDERS = 25

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)

        ids = [self.object.id] + [c.id for c in self.object.children.all()]
        discounts = OrderDiscount.objects.filter(voucher_id__in=ids)
        discounts = discounts.order_by('-order__date_placed')
        ctx['discounts'] = discounts[:self.MAX_DISPLAYED_ORDERS]
        ctx['children'] = self.object.children.order_by('code')
        return ctx


class VoucherUpdateView(DefaultVoucherUpdateView):
    form_class = VoucherForm

    def get_initial(self):
        voucher = self.get_voucher()
        initial = {
            'name': voucher.name,
            'code': voucher.code,
            'start_datetime': voucher.start_datetime,
            'end_datetime': voucher.end_datetime,
            'usage': voucher.usage,
            'limit_usage_by_group': voucher.limit_usage_by_group,
            'groups': voucher.groups.all(),
        }

        offer = voucher.offers.first()
        if offer:
            initial['priority'] = offer.priority
            initial['offer_group'] = offer.offer_group
            initial['max_global_applications'] = offer.max_global_applications
            initial['max_user_applications'] = offer.max_user_applications
            initial['max_basket_applications'] = offer.max_basket_applications
            initial['max_discount'] = offer.max_discount
            initial['condition'] = offer.condition
            initial['benefit'] = offer.benefit
            initial['description'] = offer.description

        return initial

    @transaction.atomic
    def form_valid(self, form):
        voucher = self.get_voucher()
        voucher.name = form.cleaned_data['name']
        voucher.code = form.cleaned_data['code']
        voucher.usage = form.cleaned_data['usage']
        voucher.start_datetime = form.cleaned_data['start_datetime']
        voucher.end_datetime = form.cleaned_data['end_datetime']
        voucher.limit_usage_by_group = form.cleaned_data['limit_usage_by_group']
        voucher.groups = form.cleaned_data['groups']
        voucher.save()

        benefit = form.cleaned_data['benefit']
        condition = form.cleaned_data['condition']
        if not condition:
            condition, _ = Condition.objects.get_or_create(
                range=benefit.range,
                proxy_class='oscarbluelight.offer.conditions.BluelightCountCondition',
                value=1)

        offer = voucher.offers.first()
        if not offer:
            offer = ConditionalOffer(name=_("Offer for voucher '%s'") % voucher.name, offer_type=ConditionalOffer.VOUCHER)
        offer.short_name = form.cleaned_data['code']
        offer.description = form.cleaned_data['description']
        offer.condition = condition
        offer.benefit = benefit
        offer.offer_group = form.cleaned_data['offer_group']
        offer.priority = form.cleaned_data['priority']
        offer.max_global_applications = form.cleaned_data['max_global_applications']
        offer.max_user_applications = form.cleaned_data['max_user_applications']
        offer.max_basket_applications = form.cleaned_data['max_basket_applications']
        offer.max_discount = form.cleaned_data['max_discount']
        offer.save()

        voucher.offers.add(offer)

        return HttpResponseRedirect(self.get_success_url())


class AddChildCodesView(generic.FormView):
    template_name = 'dashboard/vouchers/voucher_add_children.html'
    model = Voucher
    form_class = AddChildCodesForm

    def get_voucher(self):
        return get_object_or_404(Voucher, id=self.kwargs['pk'])

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['voucher'] = self.get_voucher()
        return ctx

    @transaction.atomic
    def form_valid(self, form):
        voucher = self.get_voucher()
        tasks.add_child_codes.apply_async(args=(voucher.pk, form.cleaned_data['child_count']), countdown=1)
        messages.success(self.request, _("Creating %s child codes…") % form.cleaned_data['child_count'])
        return HttpResponseRedirect(self.get_success_url())

    def get_success_url(self):
        return reverse('dashboard:voucher-stats', args=(self.kwargs['pk'], ))


class ExportChildCodesView(generic.DetailView):
    model = Voucher

    def get(self, request, format, *args, **kwargs):
        formats = {
            'csv': self._render_csv,
            'json': self._render_json,
        }
        if format not in formats:
            raise Http404()

        voucher = self.get_object()
        filename = re.sub(r'[^a-z0-9\_\-]+', '_', voucher.name.lower())
        children = voucher.children.order_by('code')
        return formats[format](filename, children)


    def _render_csv(self, filename, children):
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="%s.csv"' % filename
        writer = csv.writer(response)
        writer.writerow([_('Codes')])
        for child in children.all():
            writer.writerow([child.code])
        return response


    def _render_json(self, filename, children):
        response = HttpResponse(content_type='application/json')
        response['Content-Disposition'] = 'attachment; filename="%s.json"' % filename
        codes = [c.code for c in children.all()]
        data = simplejson.dumps({ 'codes': codes })
        response.write(data)
        return response

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
import csv
import re

try:
    import simplejson
except ImportError:
    import json as simplejson

AddChildCodesForm = get_class('dashboard.vouchers.forms', 'AddChildCodesForm')
Benefit = get_model('offer', 'Benefit')
Condition = get_model('offer', 'Condition')
ConditionalOffer = get_model('offer', 'ConditionalOffer')
Voucher = get_model('voucher', 'Voucher')
OrderDiscount = get_model('order', 'OrderDiscount')


class VoucherListView(DefaultVoucherListView):
    def get_queryset(self):
        qs = super().get_queryset()
        return qs.exclude_children()


class VoucherCreateView(DefaultVoucherCreateView):
    @transaction.atomic()
    def form_valid(self, form):
        # Create offer and benefit
        condition = Condition.objects.create(
            range=form.cleaned_data['benefit_range'],
            type=Condition.COUNT,
            value=1
        )
        benefit = Benefit.objects.create(
            range=form.cleaned_data['benefit_range'],
            type=form.cleaned_data['benefit_type'],
            value=form.cleaned_data['benefit_value']
        )
        name = form.cleaned_data['name']
        offer = ConditionalOffer.objects.create(
            name=_("Offer for voucher '%s'") % name,
            description=form.cleaned_data['description'],
            offer_type=ConditionalOffer.VOUCHER,
            benefit=benefit,
            condition=condition,
        )
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
            # TODO: This should probably be asynchronous, via Celery or something, to prevent
            # hanging for too long if there are a lot of codes.
            voucher.create_children( form.cleaned_data['child_count'] )

        return HttpResponseRedirect(self.get_success_url())


class VoucherStatsView(DefaultVoucherStatsView):
    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)

        ids = [self.object.id] + [c.id for c in self.object.children.all()]
        discounts = OrderDiscount.objects.filter(voucher_id__in=ids)
        discounts = discounts.order_by('-order__date_placed')
        ctx['discounts'] = discounts
        ctx['children'] = self.object.children.order_by('code').all()
        return ctx


class VoucherUpdateView(DefaultVoucherUpdateView):
    def get_initial(self):
        initial = super().get_initial()
        voucher = self.get_voucher()
        initial['description'] = voucher.offers.first().description
        initial['limit_usage_by_group'] = voucher.limit_usage_by_group
        initial['groups'] = voucher.groups.all()
        return initial

    @transaction.atomic()
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

        offer = voucher.offers.all()[0]
        offer.description = form.cleaned_data['description']
        offer.save()

        offer.condition.range = form.cleaned_data['benefit_range']
        offer.condition.save()

        benefit = voucher.benefit
        benefit.range = form.cleaned_data['benefit_range']
        benefit.type = form.cleaned_data['benefit_type']
        benefit.value = form.cleaned_data['benefit_value']
        benefit.save()

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

    @transaction.atomic()
    def form_valid(self, form):
        voucher = self.get_voucher()
        # TODO: This should probably be asynchronous, via Celery or something, to prevent
        # hanging for too long if there are a lot of codes.
        voucher.create_children( form.cleaned_data['child_count'] )
        voucher.save()
        messages.success(self.request, _("Created %s child codes") % form.cleaned_data['child_count'])
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

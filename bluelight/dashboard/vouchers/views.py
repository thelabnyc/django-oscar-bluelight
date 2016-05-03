from django.db import transaction
from django.http import HttpResponseRedirect
from django.utils.translation import ugettext_lazy as _
from oscar.core.loading import get_class, get_model
from oscar.apps.dashboard.vouchers.views import (
    VoucherCreateView as DefaultVoucherCreateView,
    VoucherUpdateView as DefaultVoucherUpdateView
)

Benefit = get_model('offer', 'Benefit')
Condition = get_model('offer', 'Condition')
ConditionalOffer = get_model('offer', 'ConditionalOffer')
Voucher = get_model('voucher', 'Voucher')


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
        return HttpResponseRedirect(self.get_success_url())


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
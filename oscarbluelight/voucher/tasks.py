from __future__ import absolute_import
from celery import shared_task
from oscar.core.loading import get_model


@shared_task(ignore_result=True)
def update_child_vouchers(voucher_id):
    Voucher = get_model('voucher', 'Voucher')
    parent = Voucher.objects.get(pk=voucher_id)
    parent.update_children()


@shared_task(ignore_result=True)
def add_child_codes(voucher_id, child_count):
    Voucher = get_model('voucher', 'Voucher')
    parent = Voucher.objects.get(pk=voucher_id)
    parent.create_children(child_count)
    parent.save()

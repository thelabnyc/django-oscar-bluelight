from __future__ import absolute_import
from celery import shared_task
from oscar.core.loading import get_model
import logging

logger = logging.getLogger(__name__)


@shared_task(ignore_result=True)
def update_child_vouchers(voucher_id):
    Voucher = get_model("voucher", "Voucher")
    parent = Voucher.objects.get(pk=voucher_id)
    parent.update_children()


@shared_task(ignore_result=True)
def add_child_codes(voucher_id, auto_generate_count=0, custom_codes=[]):
    Voucher = get_model("voucher", "Voucher")
    parent = Voucher.objects.get(pk=voucher_id)
    errors = parent.create_children(
        auto_generate_count=auto_generate_count, custom_codes=custom_codes
    )
    parent.save()
    for error in errors:
        logger.warning(error)
    return errors

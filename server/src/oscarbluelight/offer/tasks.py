from __future__ import absolute_import
from celery import shared_task
from oscar.core.loading import get_model


@shared_task(ignore_result=True)
def recalculate_offer_application_totals():
    ConditionalOffer = get_model("offer", "ConditionalOffer")
    ConditionalOffer.recalculate_offer_application_totals()

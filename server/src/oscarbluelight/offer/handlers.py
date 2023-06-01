from datetime import datetime
from django.utils import timezone
from django.dispatch import receiver
from django.db import transaction
from django.db.models.signals import post_migrate, m2m_changed, post_save
from oscar.core.loading import get_model
from .groups import ensure_all_system_groups_exist
from .applicator import pricing_cache_ns
from . import tasks

OfferGroup = get_model("offer", "OfferGroup")
ConditionalOffer = get_model("offer", "ConditionalOffer")
Benefit = get_model("offer", "Benefit")
Condition = get_model("offer", "Condition")
Range = get_model("offer", "Range")
RangeProduct = get_model("offer", "RangeProduct")
RangeProductSet = get_model("offer", "RangeProductSet")
Category = get_model("catalogue", "Category")
ProductCategory = get_model("catalogue", "ProductCategory")
Product = get_model("catalogue", "Product")
ProductClass = get_model("catalogue", "ProductClass")
StockRecord = get_model("partner", "StockRecord")
Order = get_model("order", "Order")
OrderDiscount = get_model("order", "OrderDiscount")


# Invalidate cosmetic price cache whenever any Offer or StockRecord data changes
@receiver(post_save, sender=OfferGroup)
@receiver(post_save, sender=ConditionalOffer)
@receiver(post_save, sender=Benefit)
@receiver(post_save, sender=Condition)
@receiver(post_save, sender=StockRecord)
def invalidate_pricing_cache_ns(sender, instance, **kwargs):
    transaction.on_commit(lambda: pricing_cache_ns.invalidate())


# Whenever anything changes that might affect the range membership data, queue
# a refresh of the materialized view. Once the MV refresh is done, the task will
# also invalidate pricing_cache_ns
@receiver(post_save, sender=Category)
@receiver(post_save, sender=ProductCategory)
@receiver(post_save, sender=Product)
@receiver(post_save, sender=ProductClass)
@receiver(post_save, sender=Range)
@receiver(post_save, sender=RangeProduct)
@receiver(m2m_changed, sender=Range.included_products.through)
@receiver(m2m_changed, sender=Range.excluded_products.through)
@receiver(m2m_changed, sender=Range.classes.through)
@receiver(m2m_changed, sender=Range.included_categories.through)
def queue_rps_view_refresh(*args, **kwargs):
    def _queue():
        now = datetime.timestamp(timezone.now())
        tasks.refresh_rps_view.delay(now)

    transaction.on_commit(_queue)


# Create system groups post-migration
@receiver(post_migrate)
def post_migrate_ensure_all_system_groups_exist(sender, **kwargs):
    ensure_all_system_groups_exist()


# Whenever an Order or an OrderDiscount is either created or changed, queue a task
# to recalculate the Offer application totals. Run this update task in the
# background since it has the potential to be a little slow, and it should be
# fine if the stats/usage data is a few seconds behind.
@receiver(post_save, sender=Order)
@receiver(post_save, sender=OrderDiscount)
def queue_recalculate_offer_application_totals(sender, **kwargs):
    transaction.on_commit(
        lambda: tasks.recalculate_offer_application_totals.apply_async()
    )

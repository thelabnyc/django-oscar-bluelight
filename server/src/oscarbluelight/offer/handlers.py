from django.conf import settings
from django.dispatch import receiver
from django.db import transaction
from django.db.models.signals import post_migrate, m2m_changed, post_save
from django.db.backends.signals import connection_created
from django.test.signals import setting_changed
from oscar.core.loading import get_model
from .groups import ensure_all_system_groups_exist
from .applicator import pricing_cache_ns

OfferGroup = get_model("offer", "OfferGroup")
ConditionalOffer = get_model("offer", "ConditionalOffer")
Benefit = get_model("offer", "Benefit")
Condition = get_model("offer", "Condition")
Range = get_model("offer", "Range")
RangeProductSet = get_model("offer", "RangeProductSet")
Category = get_model("catalogue", "Category")
ProductCategory = get_model("catalogue", "ProductCategory")
Product = get_model("catalogue", "Product")
StockRecord = get_model("partner", "StockRecord")


def post_migrate_ensure_all_system_groups_exist(sender, **kwargs):
    ensure_all_system_groups_exist()


def invalidate_pricing_cache_ns(sender, instance, **kwargs):
    transaction.on_commit(lambda: pricing_cache_ns.invalidate())


# Invalidate cosmetic price cache whenever any Offer data changes
post_save.connect(invalidate_pricing_cache_ns, sender=OfferGroup)
post_save.connect(invalidate_pricing_cache_ns, sender=ConditionalOffer)
post_save.connect(invalidate_pricing_cache_ns, sender=Benefit)
post_save.connect(invalidate_pricing_cache_ns, sender=Condition)

# Invalidate cosmetic price cache whenever any Product Range data changes
m2m_changed.connect(invalidate_pricing_cache_ns, sender=Range.included_products.through)
m2m_changed.connect(invalidate_pricing_cache_ns, sender=Range.excluded_products.through)
m2m_changed.connect(invalidate_pricing_cache_ns, sender=Range.classes.through)
m2m_changed.connect(
    invalidate_pricing_cache_ns, sender=Range.included_categories.through
)

# Invalidate cosmetic price cache whenever any Product data changes
post_save.connect(invalidate_pricing_cache_ns, sender=Category)
post_save.connect(invalidate_pricing_cache_ns, sender=ProductCategory)
post_save.connect(invalidate_pricing_cache_ns, sender=Product)
post_save.connect(invalidate_pricing_cache_ns, sender=StockRecord)

# Create system groups post-migration
post_migrate.connect(post_migrate_ensure_all_system_groups_exist)


# Update disable_triggers var based on Django settings when the DB connection is created
@receiver(connection_created)
def set_disable_triggers_on_connection_created(sender, **kwargs):
    value = getattr(settings, "BLUELIGHT_PG_VIEW_TRIGGERS_DISABLED", False)
    if value:
        RangeProductSet.set_disable_triggers_for_session(value)


# Update disable_triggers var when Django settings are changed
@receiver(setting_changed)
def set_disable_triggers_on_settings_change(sender, setting, value, enter, **kwargs):
    if setting == "BLUELIGHT_PG_VIEW_TRIGGERS_DISABLED":
        RangeProductSet.set_disable_triggers_for_session(value)

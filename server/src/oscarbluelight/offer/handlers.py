from django.db import transaction
from django.db.models.signals import post_migrate, m2m_changed, post_save
from oscar.core.loading import get_model
from .groups import ensure_all_system_groups_exist
from .applicator import pricing_cache_ns

OfferGroup = get_model('offer', 'OfferGroup')
ConditionalOffer = get_model('offer', 'ConditionalOffer')
Benefit = get_model('offer', 'Benefit')
Condition = get_model('offer', 'Condition')
Range = get_model('offer', 'Range')
Category = get_model('catalogue', 'Category')
ProductCategory = get_model('catalogue', 'ProductCategory')
Product = get_model('catalogue', 'Product')
StockRecord = get_model('partner', 'StockRecord')



def post_migrate_ensure_all_system_groups_exist(sender, **kwargs):
    ensure_all_system_groups_exist()


def increment_range_cache_version(sender, instance, **kwargs):
    instance.increment_cache_version()


def invalidate_pricing_cache_ns(sender, instance, **kwargs):
    transaction.on_commit(lambda: pricing_cache_ns.invalidate())


def update_range_member_cache(sender, instance, **kwargs):
    for r in Range.objects.all():
        r.increment_cache_version()


# Invalidate range cache when it's data changes
m2m_changed.connect(increment_range_cache_version, sender=Range.included_products.through)
m2m_changed.connect(increment_range_cache_version, sender=Range.excluded_products.through)
m2m_changed.connect(increment_range_cache_version, sender=Range.classes.through)
m2m_changed.connect(increment_range_cache_version, sender=Range.included_categories.through)

# Update range member cache when a product/category is saved
post_save.connect(update_range_member_cache, sender=ProductCategory)
post_save.connect(update_range_member_cache, sender=Product)

# Invalidate cosmetic price cache whenever any Offer data changes
post_save.connect(invalidate_pricing_cache_ns, sender=OfferGroup)
post_save.connect(invalidate_pricing_cache_ns, sender=ConditionalOffer)
post_save.connect(invalidate_pricing_cache_ns, sender=Benefit)
post_save.connect(invalidate_pricing_cache_ns, sender=Condition)

# Invalidate cosmetic price cache whenever any Product Range data changes
m2m_changed.connect(invalidate_pricing_cache_ns, sender=Range.included_products.through)
m2m_changed.connect(invalidate_pricing_cache_ns, sender=Range.excluded_products.through)
m2m_changed.connect(invalidate_pricing_cache_ns, sender=Range.classes.through)
m2m_changed.connect(invalidate_pricing_cache_ns, sender=Range.included_categories.through)

# Invalidate cosmetic price cache whenever any Product data changes
post_save.connect(invalidate_pricing_cache_ns, sender=Category)
post_save.connect(invalidate_pricing_cache_ns, sender=ProductCategory)
post_save.connect(invalidate_pricing_cache_ns, sender=Product)
post_save.connect(invalidate_pricing_cache_ns, sender=StockRecord)

# Create system groups post-migration
post_migrate.connect(post_migrate_ensure_all_system_groups_exist)

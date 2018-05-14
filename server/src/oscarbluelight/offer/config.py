from django.db.models.signals import post_migrate, m2m_changed
from oscar.apps.offer import config
from .groups import ensure_all_system_groups_exist



def post_migrate_ensure_all_system_groups_exist(sender, **kwargs):
    ensure_all_system_groups_exist()


def increment_range_cache_version(sender, instance, **kwargs):
    instance.increment_cache_version()


class OfferConfig(config.OfferConfig):
    name = 'oscarbluelight.offer'

    def ready(self):
        super().ready()
        # Invalidate range cache when it's data changes
        from oscar.core.loading import get_model
        Range = get_model('offer', 'Range')
        m2m_changed.connect(increment_range_cache_version, sender=Range.included_products.through)
        m2m_changed.connect(increment_range_cache_version, sender=Range.excluded_products.through)
        m2m_changed.connect(increment_range_cache_version, sender=Range.classes.through)
        m2m_changed.connect(increment_range_cache_version, sender=Range.included_categories.through)
        # Create system groups post-migration
        post_migrate.connect(post_migrate_ensure_all_system_groups_exist)

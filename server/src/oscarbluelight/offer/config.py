from django.db.models.signals import post_migrate
from oscar.apps.offer import config
from .groups import ensure_all_system_groups_exist


class OfferConfig(config.OfferConfig):
    name = 'oscarbluelight.offer'

    def ready(self):
        super().ready()
        post_migrate.connect(lambda sender, **kwargs: ensure_all_system_groups_exist())

from oscar.apps.offer import config


class OfferConfig(config.OfferConfig):
    name = 'oscarbluelight.offer'

    def ready(self):
        super().ready()
        # Invalidate range cache when it's data changes
        from . import handlers  # NOQA

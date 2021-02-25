from oscar.apps.offer import apps


class OfferConfig(apps.OfferConfig):
    name = "oscarbluelight.offer"

    def ready(self):
        super().ready()
        # Invalidate range cache when it's data changes
        from . import handlers  # NOQA

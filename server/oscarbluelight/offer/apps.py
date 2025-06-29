from oscar.apps.offer import apps


class OfferConfig(apps.OfferConfig):
    name = "oscarbluelight.offer"
    default_auto_field = "django.db.models.BigAutoField"

    def ready(self) -> None:
        super().ready()
        # Invalidate range cache when it's data changes
        from . import handlers  # NOQA

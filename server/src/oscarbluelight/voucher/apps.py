from oscar.apps.voucher import apps


class VoucherConfig(apps.VoucherConfig):
    name = "oscarbluelight.voucher"
    default_auto_field = "django.db.models.BigAutoField"

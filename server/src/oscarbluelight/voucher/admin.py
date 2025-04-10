from django.contrib import admin

from .models import Voucher, VoucherApplication


@admin.register(Voucher)
class VoucherAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "code",
        "usage",
        "num_basket_additions",
        "num_orders",
        "total_discount",
        "limit_usage_by_group",
    )
    readonly_fields = ("num_basket_additions", "num_orders", "total_discount")
    fieldsets = (
        (None, {"fields": ("name", "code", "usage", "start_datetime", "end_datetime")}),
        ("User Group Whitelist", {"fields": ("limit_usage_by_group", "groups")}),
        ("Benefit", {"fields": ("offers",)}),
        ("Usage", {"fields": ("num_basket_additions", "num_orders", "total_discount")}),
    )


@admin.register(VoucherApplication)
class VoucherApplicationAdmin(admin.ModelAdmin):
    list_display = ("voucher", "user", "order", "date_created")
    readonly_fields = ("voucher", "user", "order")

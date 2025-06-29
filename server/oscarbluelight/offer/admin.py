from django.contrib import admin

from .models import (
    Benefit,
    CompoundCondition,
    Condition,
    ConditionalOffer,
    OfferGroup,
    Range,
)


@admin.register(Benefit)
class BenefitAdmin(admin.ModelAdmin):
    list_display = ("__str__", "proxy_class", "value", "range")


@admin.register(Condition)
class ConditionAdmin(admin.ModelAdmin):
    list_display = ("__str__", "proxy_class", "value", "range")


@admin.register(CompoundCondition)
class CompoundConditionAdmin(admin.ModelAdmin):
    list_display = ("name", "conjunction", "range")
    list_filter = ("conjunction",)
    fields = ("conjunction", "subconditions")


class ConditionalOfferAdmin(admin.StackedInline):
    max_num = 3
    list_display = (
        "name",
        "offer_type",
        "start_datetime",
        "end_datetime",
        "condition",
        "benefit",
        "total_discount",
    )
    list_filter = ("offer_type",)
    readonly_fields = ("total_discount", "num_orders")
    fieldsets = (
        (
            None,
            {
                "fields": (
                    "name",
                    "description",
                    "offer_type",
                    "groups",
                    "condition",
                    "benefit",
                    "start_datetime",
                    "end_datetime",
                    "priority",
                )
            },
        ),
        ("Usage", {"fields": ("total_discount", "num_orders")}),
    )
    model = ConditionalOffer


@admin.register(OfferGroup)
class OfferGroupAdmin(admin.ModelAdmin):
    list_filter = ("name",)
    list_display = ("name", "priority")
    fields = (
        "name",
        "priority",
    )
    inlines = [
        ConditionalOfferAdmin,
    ]


admin.site.register(Range)

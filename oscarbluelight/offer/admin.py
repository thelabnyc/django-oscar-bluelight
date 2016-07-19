from django.contrib import admin
from oscar.core.loading import get_model

ConditionalOffer = get_model('offer', 'ConditionalOffer')
Condition = get_model('offer', 'Condition')
Benefit = get_model('offer', 'Benefit')
Range = get_model('offer', 'Range')
CompoundCondition = get_model('offer', 'CompoundCondition')


@admin.register(Benefit)
class BenefitAdmin(admin.ModelAdmin):
    list_display = ('__str__', 'proxy_class', 'value', 'range')


@admin.register(Condition)
class ConditionAdmin(admin.ModelAdmin):
    list_display = ('__str__', 'proxy_class', 'value', 'range')


@admin.register(CompoundCondition)
class CompoundConditionAdmin(admin.ModelAdmin):
    list_display = ('name', 'conjunction', 'range')
    list_filter = ('conjunction', )
    fields = ('conjunction', 'subconditions')


@admin.register(ConditionalOffer)
class ConditionalOfferAdmin(admin.ModelAdmin):
    list_display = ('name', 'offer_type', 'start_datetime', 'end_datetime', 'condition', 'benefit', 'total_discount')
    list_filter = ('offer_type', )
    readonly_fields = ('total_discount', 'num_orders')
    fieldsets = (
        (None, {
            'fields': ('name', 'description', 'offer_type', 'groups', 'condition',
                       'benefit', 'start_datetime', 'end_datetime', 'priority')
        }),
        ('Usage', {
            'fields': ('total_discount', 'num_orders')
        }),
    )


admin.site.register(Range)

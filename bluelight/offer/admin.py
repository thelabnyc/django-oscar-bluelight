from django.contrib import admin
from oscar.core.loading import get_model

CompoundCondition = get_model('offer', 'CompoundCondition')


@admin.register(CompoundCondition)
class CompoundConditionAdmin(admin.ModelAdmin):
    list_display = ('name', 'conjunction', 'range')
    list_filter = ('conjunction', )
    fields = ('conjunction', 'subconditions')


from oscar.apps.offer.admin import *  # noqa

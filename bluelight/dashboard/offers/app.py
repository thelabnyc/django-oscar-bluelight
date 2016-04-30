from django.conf.urls import url
from oscar.apps.dashboard.offers.app import OffersDashboardApplication as Application
from oscar.core.loading import get_class


class OffersDashboardApplication(Application):
    condition_list_view = get_class('dashboard.offers.views', 'ConditionListView')
    condition_delete_view = get_class('dashboard.offers.views', 'ConditionDeleteView')
    condition_create_view = get_class('dashboard.offers.views', 'ConditionCreateView')
    compound_condition_create_view = get_class('dashboard.offers.views', 'CompoundConditionCreateView')
    condition_update_view = get_class('dashboard.offers.views', 'ConditionUpdateView')

    def get_urls(self):
        base_urls = super().get_urls()
        custom_urls = [
            # Conditions
            url(r'^conditions/$', self.condition_list_view.as_view(), name='condition-list'),
            url(r'^conditions/new/$', self.condition_create_view.as_view(), name='condition-create'),
            url(r'^conditions/new-compound/$', self.compound_condition_create_view.as_view(), name='condition-create-compound'),
            url(r'^conditions/(?P<pk>[0-9]+)/$', self.condition_update_view.as_view(), name='condition-update'),
            url(r'^conditions/(?P<pk>[0-9]+)/delete/$', self.condition_delete_view.as_view(), name='condition-delete'),
        ]
        return base_urls + self.post_process_urls(custom_urls)


application = OffersDashboardApplication()

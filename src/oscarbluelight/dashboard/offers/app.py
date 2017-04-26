from django.conf.urls import url
from oscar.apps.dashboard.offers.app import OffersDashboardApplication as Application
from oscar.core.loading import get_class


class OffersDashboardApplication(Application):
    benefit_list_view = get_class('dashboard.offers.views', 'BenefitListView')
    benefit_delete_view = get_class('dashboard.offers.views', 'BenefitDeleteView')
    benefit_create_view = get_class('dashboard.offers.views', 'BenefitCreateView')
    benefit_update_view = get_class('dashboard.offers.views', 'BenefitUpdateView')

    condition_list_view = get_class('dashboard.offers.views', 'ConditionListView')
    condition_delete_view = get_class('dashboard.offers.views', 'ConditionDeleteView')
    condition_create_view = get_class('dashboard.offers.views', 'ConditionCreateView')
    compound_condition_create_view = get_class('dashboard.offers.views', 'CompoundConditionCreateView')
    condition_update_view = get_class('dashboard.offers.views', 'ConditionUpdateView')

    offergroup_create_view = get_class('dashboard.offers.views', 'OfferGroupCreateView')
    offergroup_list_view = get_class('dashboard.offers.views', 'OfferGroupListView')
    offergroup_update_view = get_class('dashboard.offers.views', 'OfferGroupUpdateView')
    offergroup_delete_view = get_class('dashboard.offers.views', 'OfferGroupDeleteView')

    def get_urls(self):
        base_urls = super().get_urls()
        custom_urls = [
            # Conditions
            url(r'^benefits/$', self.benefit_list_view.as_view(), name='benefit-list'),
            url(r'^benefits/new/$', self.benefit_create_view.as_view(), name='benefit-create'),
            url(r'^benefits/(?P<pk>[0-9]+)/$', self.benefit_update_view.as_view(), name='benefit-update'),
            url(r'^benefits/(?P<pk>[0-9]+)/delete/$', self.benefit_delete_view.as_view(), name='benefit-delete'),

            # Conditions
            url(r'^conditions/$', self.condition_list_view.as_view(), name='condition-list'),
            url(r'^conditions/new/$', self.condition_create_view.as_view(), name='condition-create'),
            url(r'^conditions/new-compound/$', self.compound_condition_create_view.as_view(), name='condition-create-compound'),
            url(r'^conditions/(?P<pk>[0-9]+)/$', self.condition_update_view.as_view(), name='condition-update'),
            url(r'^conditions/(?P<pk>[0-9]+)/delete/$', self.condition_delete_view.as_view(), name='condition-delete'),

            # offer group
            url(r'^offer_group/$', self.offergroup_list_view.as_view(), name='offergroup-list'),
            url(r'^offer_group/new/$', self.offergroup_create_view.as_view(), name='offergroup-create'),
            url(r'^offer_group/(?P<pk>[0-9]+)/$', self.offergroup_update_view.as_view(), name='offergroup-update'),
            url(r'^offer_group/(?P<pk>[0-9]+)/delete/$', self.offergroup_delete_view.as_view(), name='offergroup-delete'),
        ]
        return base_urls + self.post_process_urls(custom_urls)


application = OffersDashboardApplication()

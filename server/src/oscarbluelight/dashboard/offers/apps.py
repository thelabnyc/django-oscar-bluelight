from django.conf.urls import url, include
from django.views.i18n import JavaScriptCatalog
from rest_framework import routers
from oscar.apps.dashboard.offers import apps
from oscar.core.loading import get_class


class OffersDashboardConfig(apps.OffersDashboardConfig):
    name = "oscarbluelight.dashboard.offers"

    def ready(self):
        self.list_view = get_class("offers_dashboard.views", "OfferListView")
        self.metadata_view = get_class("offers_dashboard.views", "OfferMetaDataView")
        self.condition_view = get_class("offers_dashboard.views", "OfferConditionView")
        self.benefit_view = get_class("offers_dashboard.views", "OfferBenefitView")
        self.restrictions_view = get_class(
            "offers_dashboard.views", "OfferRestrictionsView"
        )
        self.delete_view = get_class("offers_dashboard.views", "OfferDeleteView")
        self.detail_view = get_class("offers_dashboard.views", "OfferDetailView")

    def get_urls(self):
        from .api_views import OfferGroupViewSet
        from .views import (
            BenefitListView,
            BenefitDeleteView,
            BenefitCreateView,
            CompoundBenefitCreateView,
            BenefitUpdateView,
            ConditionListView,
            ConditionDeleteView,
            ConditionCreateView,
            CompoundConditionCreateView,
            ConditionUpdateView,
            OfferGroupCreateView,
            OfferGroupListView,
            OfferGroupUpdateView,
            OfferGroupDeleteView,
        )

        base_urls = super().get_urls()

        router = routers.DefaultRouter()
        router.register(r"offergroups", OfferGroupViewSet, basename="api-offergroup")

        custom_urls = [
            # API
            url(r"^api/", include(router.urls)),
            # i18n JS Catalogue
            url(
                r"^bluelight-i18n\.js$",
                JavaScriptCatalog.as_view(packages=["oscarbluelight"]),
                name="oscarbluelight-i18n-js",
            ),
            # Benefits
            url(r"^benefits/$", BenefitListView.as_view(), name="benefit-list"),
            url(r"^benefits/new/$", BenefitCreateView.as_view(), name="benefit-create"),
            url(
                r"^benefits/new-compound/$",
                CompoundBenefitCreateView.as_view(),
                name="benefit-create-compound",
            ),
            url(
                r"^benefits/(?P<pk>[0-9]+)/$",
                BenefitUpdateView.as_view(),
                name="benefit-update",
            ),
            url(
                r"^benefits/(?P<pk>[0-9]+)/delete/$",
                BenefitDeleteView.as_view(),
                name="benefit-delete",
            ),
            # Conditions
            url(r"^conditions/$", ConditionListView.as_view(), name="condition-list"),
            url(
                r"^conditions/new/$",
                ConditionCreateView.as_view(),
                name="condition-create",
            ),
            url(
                r"^conditions/new-compound/$",
                CompoundConditionCreateView.as_view(),
                name="condition-create-compound",
            ),
            url(
                r"^conditions/(?P<pk>[0-9]+)/$",
                ConditionUpdateView.as_view(),
                name="condition-update",
            ),
            url(
                r"^conditions/(?P<pk>[0-9]+)/delete/$",
                ConditionDeleteView.as_view(),
                name="condition-delete",
            ),
            # Offer Groups
            url(
                r"^offer_group/$", OfferGroupListView.as_view(), name="offergroup-list"
            ),
            url(
                r"^offer_group/new/$",
                OfferGroupCreateView.as_view(),
                name="offergroup-create",
            ),
            url(
                r"^offer_group/(?P<pk>[0-9]+)/$",
                OfferGroupUpdateView.as_view(),
                name="offergroup-update",
            ),
            url(
                r"^offer_group/(?P<pk>[0-9]+)/delete/$",
                OfferGroupDeleteView.as_view(),
                name="offergroup-delete",
            ),
        ]
        return base_urls + self.post_process_urls(custom_urls)

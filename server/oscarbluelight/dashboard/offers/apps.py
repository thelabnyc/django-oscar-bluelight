from __future__ import annotations

from django.urls import include, path
from django.urls.resolvers import URLPattern, URLResolver
from django.views.i18n import JavaScriptCatalog
from oscar.apps.dashboard.offers import apps
from oscar.core.loading import get_class
from rest_framework import routers


class OffersDashboardConfig(apps.OffersDashboardConfig):
    name = "oscarbluelight.dashboard.offers"

    def ready(self) -> None:
        from .views import OfferListView

        self.list_view = OfferListView
        self.metadata_view = get_class("offers_dashboard.views", "OfferMetaDataView")
        self.condition_view = get_class("offers_dashboard.views", "OfferConditionView")
        self.benefit_view = get_class("offers_dashboard.views", "OfferBenefitView")
        self.restrictions_view = get_class(
            "offers_dashboard.views", "OfferRestrictionsView"
        )
        self.image_update_view = get_class(
            "offers_dashboard.views", "OfferImageUpdateView"
        )
        self.delete_view = get_class("offers_dashboard.views", "OfferDeleteView")
        self.detail_view = get_class("offers_dashboard.views", "OfferDetailView")

    def get_urls(self) -> list[URLPattern | URLResolver]:
        from .api_views import OfferAPIView, OfferGroupViewSet
        from .views import (
            BenefitCreateView,
            BenefitDeleteView,
            BenefitListView,
            BenefitUpdateView,
            CompoundBenefitCreateView,
            CompoundConditionCreateView,
            ConditionCreateView,
            ConditionDeleteView,
            ConditionListView,
            ConditionUpdateView,
            OfferGroupCreateView,
            OfferGroupDeleteView,
            OfferGroupListView,
            OfferGroupUpdateView,
        )

        base_urls = super().get_urls()

        router = routers.DefaultRouter()
        router.register(r"offergroups", OfferGroupViewSet, basename="api-offergroup")

        custom_urls = [
            # API
            path("api/", include(router.urls)),
            # i18n JS Catalogue
            path(
                "bluelight-i18n.js",
                JavaScriptCatalog.as_view(packages=["oscarbluelight"]),
                name="oscarbluelight-i18n-js",
            ),
            # Offers
            path(
                "<int:pk>/images/",
                self.image_update_view.as_view(),
                name="offer-images",
            ),
            path(
                "offers/",
                OfferAPIView.as_view(),
                name="offer-api-list",
            ),
            # Benefits
            path("benefits/", BenefitListView.as_view(), name="benefit-list"),
            path("benefits/new/", BenefitCreateView.as_view(), name="benefit-create"),
            path(
                "benefits/new-compound/",
                CompoundBenefitCreateView.as_view(),
                name="benefit-create-compound",
            ),
            path(
                "benefits/<int:pk>/",
                BenefitUpdateView.as_view(),
                name="benefit-update",
            ),
            path(
                "benefits/<int:pk>/delete/",
                BenefitDeleteView.as_view(),
                name="benefit-delete",
            ),
            # Conditions
            path("conditions/", ConditionListView.as_view(), name="condition-list"),
            path(
                "conditions/new/",
                ConditionCreateView.as_view(),
                name="condition-create",
            ),
            path(
                "conditions/new-compound/",
                CompoundConditionCreateView.as_view(),
                name="condition-create-compound",
            ),
            path(
                "conditions/<int:pk>/",
                ConditionUpdateView.as_view(),
                name="condition-update",
            ),
            path(
                "conditions/<int:pk>/delete/",
                ConditionDeleteView.as_view(),
                name="condition-delete",
            ),
            # Offer Groups
            path("offer_group/", OfferGroupListView.as_view(), name="offergroup-list"),
            path(
                "offer_group/new/",
                OfferGroupCreateView.as_view(),
                name="offergroup-create",
            ),
            path(
                "offer_group/<int:pk>/",
                OfferGroupUpdateView.as_view(),
                name="offergroup-update",
            ),
            path(
                "offer_group/<int:pk>/delete/",
                OfferGroupDeleteView.as_view(),
                name="offergroup-delete",
            ),
        ]
        return base_urls + self.post_process_urls(custom_urls)

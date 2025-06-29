from __future__ import annotations

from django.urls import path
from django.urls.resolvers import URLPattern
from oscar.apps.dashboard.ranges import apps
from oscar.core.loading import get_class


class RangesDashboardConfig(apps.RangesDashboardConfig):
    name = "oscarbluelight.dashboard.ranges"

    def ready(self) -> None:
        super().ready()
        self.list_view = get_class("ranges_dashboard.views", "RangeListView")
        self.products_view = get_class("ranges_dashboard.views", "RangeProductListView")

    def get_urls(self) -> list[URLPattern]:
        price_list_view = get_class("ranges_dashboard.views", "RangePriceListView")
        excluded_products_view = get_class(
            "ranges_dashboard.views", "RangeExcludedProductsView"
        )
        urlpatterns = [
            path(
                "<int:pk>/prices/",
                price_list_view.as_view(),
                name="range-prices",
            ),
            path(
                "<int:pk>/excluded-products/",
                excluded_products_view.as_view(),
                name="range-excluded-products",
            ),
        ]
        return super().get_urls() + self.post_process_urls(urlpatterns)

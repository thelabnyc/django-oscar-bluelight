from django.conf.urls import url
from oscar.apps.dashboard.ranges import apps
from oscar.core.loading import get_class


class RangesDashboardConfig(apps.RangesDashboardConfig):
    name = "oscarbluelight.dashboard.ranges"

    def ready(self):
        super().ready()
        self.list_view = get_class("ranges_dashboard.views", "RangeListView")
        self.products_view = get_class("ranges_dashboard.views", "RangeProductListView")

    def get_urls(self):
        price_list_view = get_class("ranges_dashboard.views", "RangePriceListView")
        excluded_products_view = get_class(
            "ranges_dashboard.views", "RangeExcludedProductsView"
        )
        urlpatterns = [
            url(
                r"^(?P<pk>\d+)/prices/$", price_list_view.as_view(), name="range-prices"
            ),
            url(
                r"^(?P<pk>\d+)/excluded-products/$",
                excluded_products_view.as_view(),
                name="range-excluded-products",
            ),
        ]
        return super().get_urls() + self.post_process_urls(urlpatterns)

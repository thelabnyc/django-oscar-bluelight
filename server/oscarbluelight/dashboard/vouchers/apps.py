from __future__ import annotations

from django.urls import path
from django.urls.resolvers import URLPattern
from oscar.apps.dashboard.vouchers import apps
from oscar.core.loading import get_class


class VouchersDashboardConfig(apps.VouchersDashboardConfig):
    name = "oscarbluelight.dashboard.vouchers"

    def ready(self) -> None:
        super().ready()
        self.list_view = get_class("vouchers_dashboard.views", "VoucherListView")
        self.create_view = get_class("vouchers_dashboard.views", "VoucherCreateView")
        self.update_view = get_class("vouchers_dashboard.views", "VoucherUpdateView")
        self.delete_view = get_class("vouchers_dashboard.views", "VoucherDeleteView")
        self.stats_view = get_class("vouchers_dashboard.views", "VoucherStatsView")
        self.set_list_view = get_class("vouchers_dashboard.views", "VoucherSetListView")
        self.set_create_view = get_class(
            "vouchers_dashboard.views", "VoucherSetCreateView"
        )
        self.set_update_view = get_class(
            "vouchers_dashboard.views", "VoucherSetUpdateView"
        )
        self.set_detail_view = get_class(
            "vouchers_dashboard.views", "VoucherSetDetailView"
        )
        self.set_download_view = get_class(
            "vouchers_dashboard.views", "VoucherSetDownloadView"
        )
        self.suspension_view = get_class(
            "vouchers_dashboard.views", "VoucherSuspensionView"
        )

    def get_urls(self) -> list[URLPattern]:
        from .views import (
            AddChildCodesView,
            ChildCodesListView,
            ExportChildCodesFormView,
            ExportChildCodesView,
            VoucherStatsView,
            VoucherSuspensionView,
        )

        urls = [
            path(
                "stats/<int:parent_pk>/children/",
                ChildCodesListView.as_view(),
                name="voucher-list-children",
            ),
            path(
                "stats/<int:pk>/add-children/",
                AddChildCodesView.as_view(),
                name="voucher-add-children",
            ),
            path(
                "stats/<int:pk>/export-children/",
                ExportChildCodesFormView.as_view(),
                name="voucher-export-children",
            ),
            path(
                "stats/<int:pk>/export-children.<slug:file_format>",
                ExportChildCodesView.as_view(),
                name="voucher-export-children-file",
            ),
            path(
                "stats/<int:pk>/update-suspension-status/",
                VoucherSuspensionView.as_view(),
                name="voucher-update-suspension-status",
            ),
            path(
                "stats/<int:pk>/",
                VoucherStatsView.as_view(),
                name="voucher-stats",
            ),
        ]
        return super().get_urls() + self.post_process_urls(urls)

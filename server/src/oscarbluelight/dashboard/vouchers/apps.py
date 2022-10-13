from django.urls import re_path
from oscar.apps.dashboard.vouchers import apps
from oscar.core.loading import get_class


class VouchersDashboardConfig(apps.VouchersDashboardConfig):
    name = "oscarbluelight.dashboard.vouchers"

    def ready(self):
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

    def get_urls(self):
        from .views import (
            AddChildCodesView,
            ExportChildCodesFormView,
            ExportChildCodesView,
            VoucherStatsView,
            ChildCodesListView,
            VoucherSuspensionView,
        )

        urls = [
            re_path(
                r"^stats/(?P<parent_pk>\d+)/children/$",
                ChildCodesListView.as_view(),
                name="voucher-list-children",
            ),
            re_path(
                r"^stats/(?P<pk>\d+)/add-children/$",
                AddChildCodesView.as_view(),
                name="voucher-add-children",
            ),
            re_path(
                r"^stats/(?P<pk>\d+)/export-children/$",
                ExportChildCodesFormView.as_view(),
                name="voucher-export-children",
            ),
            re_path(
                r"^stats/(?P<pk>\d+)/export-children.(?P<file_format>[\w]+)$",
                ExportChildCodesView.as_view(),
                name="voucher-export-children-file",
            ),
            re_path(
                r"^stats/(?P<pk>\d+)/update-suspension-status/$",
                VoucherSuspensionView.as_view(),
                name="voucher-update-suspension-status",
            ),
            re_path(
                r"^stats/(?P<pk>\d+)/$",
                VoucherStatsView.as_view(),
                name="voucher-stats",
            ),
        ]
        return super().get_urls() + self.post_process_urls(urls)

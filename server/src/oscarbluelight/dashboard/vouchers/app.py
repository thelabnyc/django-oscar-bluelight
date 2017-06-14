from django.conf.urls import url
from oscar.apps.dashboard.vouchers.app import VoucherDashboardApplication as DefaultVoucherDashboardApplication
from oscar.core.loading import get_class


class VoucherDashboardApplication(DefaultVoucherDashboardApplication):
    add_children_view = get_class('dashboard.vouchers.views', 'AddChildCodesView')
    export_children_view = get_class('dashboard.vouchers.views', 'ExportChildCodesView')
    voucher_stats_view = get_class('dashboard.vouchers.views', 'VoucherStatsView')

    def get_urls(self):
        urls = [
            url(r'^stats/(?P<pk>\d+)/add-children/$', self.add_children_view.as_view(),
                name='voucher-add-children'),
            url(r'^stats/(?P<pk>\d+)/export-children.(?P<format>[\w]+)$', self.export_children_view.as_view(),
                name='voucher-export-children'),
            url(r'^stats/(?P<pk>\d+)/$', self.voucher_stats_view.as_view(), name='voucher-stats'),
        ]
        return super().get_urls() + self.post_process_urls(urls)


application = VoucherDashboardApplication()

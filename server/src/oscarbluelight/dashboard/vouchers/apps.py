from django.conf.urls import url
from oscar.apps.dashboard.vouchers import apps



class VouchersDashboardConfig(apps.VouchersDashboardConfig):
    name = 'oscarbluelight.dashboard.vouchers'


    def get_urls(self):
        from .views import (
            AddChildCodesView,
            ExportChildCodesView,
            VoucherStatsView,
        )
        urls = [
            url(r'^stats/(?P<pk>\d+)/add-children/$', AddChildCodesView.as_view(),
                name='voucher-add-children'),
            url(r'^stats/(?P<pk>\d+)/export-children.(?P<format>[\w]+)$', ExportChildCodesView.as_view(),
                name='voucher-export-children'),
            url(r'^stats/(?P<pk>\d+)/$', VoucherStatsView.as_view(), name='voucher-stats'),
        ]
        return super().get_urls() + self.post_process_urls(urls)

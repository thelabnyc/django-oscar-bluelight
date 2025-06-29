from __future__ import annotations

from typing import TYPE_CHECKING

from django.db.models import QuerySet
from django.http import HttpResponse
from django.utils.translation import gettext_lazy as _
from oscar.apps.dashboard.offers import reports
from oscar.apps.dashboard.offers.reports import *  # NOQA

if TYPE_CHECKING:
    from oscar.apps.order.models import OrderDiscount


class OrderDiscountCSVFormatter(  # type:ignore[no-redef]
    reports.OrderDiscountCSVFormatter
):
    def generate_csv(
        self,
        response: HttpResponse,
        order_discounts: QuerySet[OrderDiscount],
    ) -> None:
        writer = self.get_csv_writer(response)
        header_row = [
            _("Order number"),
            _("Order status"),
            _("Order date"),
            _("Order total"),
            _("Cost"),
            _("Products"),
            _("UPCs"),
            _("SKUs"),
            _("Payment methods"),
        ]
        writer.writerow(header_row)
        order_discounts = order_discounts.prefetch_related(
            "order__lines", "order__sources"
        ).all()
        for order_discount in order_discounts:
            order = order_discount.order
            product_names: set[str] = set()
            upcs: set[str] = set()
            skus: set[str] = set()
            payment_methods: set[str] = set()
            for line in order.lines.all():
                product_names.add(line.title)
                if line.upc:
                    upcs.add(line.upc)
                skus.add(line.partner_sku)
            for source in order.sources.all():
                payment_methods.add(source.source_type.name)
            row = [
                order.number,
                order.status,
                self.format_datetime(order.date_placed),
                order.total_incl_tax,
                order_discount.amount,
                "\n".join(sorted(list(product_names))),
                "\n".join(sorted(list(upcs))),
                "\n".join(sorted(list(skus))),
                "\n".join(sorted(list(payment_methods))),
            ]
            writer.writerow(row)

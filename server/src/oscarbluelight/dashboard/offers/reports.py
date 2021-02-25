from django.utils.translation import gettext_lazy as _
from oscar.apps.dashboard.offers import reports
from oscar.apps.dashboard.offers.reports import *  # NOQA


class OrderDiscountCSVFormatter(reports.OrderDiscountCSVFormatter):
    def generate_csv(self, response, order_discounts):
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
            product_names = set([])
            upcs = set([])
            skus = set([])
            payment_methods = set([])
            for line in order.lines.all():
                product_names.add(line.title)
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

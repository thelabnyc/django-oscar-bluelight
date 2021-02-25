from django.utils.translation import gettext_lazy as _
from django.utils.encoding import force_str
from oscar.apps.voucher.reports import (
    VoucherReportCSVFormatter as BaseVoucherReportCSVFormatter,
    VoucherReportGenerator as BaseVoucherReportGenerator,
)
from django.utils.html import strip_tags
from oscar.core.loading import get_model

Voucher = get_model("voucher", "Voucher")


class VoucherReportCSVFormatter(BaseVoucherReportCSVFormatter):
    def generate_csv(self, response, vouchers):
        writer = self.get_csv_writer(response)
        header_row = [
            _("ID"),
            _("Name"),
            _("Description"),
            _("Code"),
            _("Num Child Code"),
            _("Offer Group"),
            _("Priority"),
            _("Desktop Image"),
            _("Mobile Image"),
            _("Incentive ID"),
            _("Incentive Name"),
            _("Condition ID"),
            _("Condition Name"),
            _("Start Datetime"),
            _("End Datetime"),
            _("Usage"),
            _("Restrictions"),
            _("Status"),
            _("Usage is limited to specific user group?"),
            _("User Groups"),
        ]
        writer.writerow(header_row)

        for voucher in vouchers:
            for offer in voucher.offers.all():
                row = [
                    voucher.pk,
                    voucher.name,
                    strip_tags(offer.description),
                    voucher.code,
                    (voucher.children.count()),
                    str(offer.offer_group),
                    offer.priority,
                    (offer.desktop_image.url if offer.desktop_image else ""),
                    (offer.mobile_image.url if offer.mobile_image else ""),
                    offer.benefit.pk,
                    offer.benefit.proxy().name,
                    offer.condition.pk,
                    offer.condition.proxy().name,
                    self.format_datetime(voucher.start_datetime),
                    self.format_datetime(voucher.end_datetime),
                    voucher.get_usage_display(),
                    (
                        "\n".join(
                            [
                                force_str(r["description"])
                                for r in offer.availability_restrictions()
                            ]
                        )
                    ),
                    offer.status,
                    (_("Yes") if voucher.limit_usage_by_group else _("No")),
                    ("\n".join(g.name for g in voucher.groups.all())),
                ]
                writer.writerow(row)


class VoucherReportGenerator(BaseVoucherReportGenerator):
    code = "vouchers"
    description = _("All Vouchers on Site")

    formatters = {
        "CSV_formatter": VoucherReportCSVFormatter,
    }

    def generate(self):
        vouchers = Voucher.objects.filter(parent__isnull=True).all()
        return self.formatter.generate_response(vouchers)

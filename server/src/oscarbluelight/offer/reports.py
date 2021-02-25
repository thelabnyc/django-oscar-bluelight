from django.utils.translation import gettext_lazy as _
from django.utils.encoding import force_str
from oscar.apps.offer.reports import (
    OfferReportCSVFormatter as BaseOfferReportCSVFormatter,
    OfferReportGenerator as BaseOfferReportGenerator,
)
from django.utils.html import strip_tags
from oscar.core.loading import get_model

ConditionalOffer = get_model("offer", "ConditionalOffer")


class OfferReportCSVFormatter(BaseOfferReportCSVFormatter):
    def generate_csv(self, response, offers):
        writer = self.get_csv_writer(response)
        header_row = [
            _("ID"),
            _("Name"),
            _("Short Name"),
            _("Offer Type"),
            _("Description"),
            _("Offer Group"),
            _("Priority"),
            _("Desktop Image"),
            _("Mobile Image"),
            _("Incentive ID"),
            _("Incentive Name"),
            _("Condition ID"),
            _("Condition Name"),
            _("Restrictions"),
            _("Status"),
        ]
        writer.writerow(header_row)

        for offer in offers:
            row = [
                offer.pk,
                offer.name,
                offer.short_name,
                offer.offer_type,
                strip_tags(offer.description),
                str(offer.offer_group),
                offer.priority,
                (offer.desktop_image.url if offer.desktop_image else ""),
                (offer.mobile_image.url if offer.mobile_image else ""),
                offer.benefit.pk,
                offer.benefit.proxy().name,
                offer.condition.pk,
                offer.condition.proxy().name,
                (
                    "\n".join(
                        [
                            force_str(r["description"])
                            for r in offer.availability_restrictions()
                        ]
                    )
                ),
                offer.status,
            ]
            writer.writerow(row)


class OfferReportGenerator(BaseOfferReportGenerator):
    code = "conditional-offers"
    description = _("All Offers on Site")

    formatters = {
        "CSV_formatter": OfferReportCSVFormatter,
    }

    def generate(self):
        offers = ConditionalOffer.objects.exclude(
            offer_type=ConditionalOffer.VOUCHER
        ).all()
        return self.formatter.generate_response(offers)

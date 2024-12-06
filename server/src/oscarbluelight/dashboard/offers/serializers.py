from rest_framework import serializers
from oscarbluelight.offer.models import OfferGroup, ConditionalOffer
from oscarbluelight.voucher.models import Voucher

DEFAULT_OFFER_LIMIT_TO_DISPLAY = 1000


class VoucherSerializer(serializers.ModelSerializer):
    details_link = serializers.HyperlinkedIdentityField(
        view_name="dashboard:voucher-stats"
    )
    desktop_image = serializers.SerializerMethodField()
    mobile_image = serializers.SerializerMethodField()

    class Meta:
        model = Voucher
        fields = (
            "id",
            "name",
            "code",
            "is_active",
            "details_link",
            "desktop_image",
            "mobile_image",
        )

    def get_desktop_image(self, obj):
        offer = obj.offers.first()
        if offer:
            return offer.desktop_image.url if offer.desktop_image else ""
        return ""

    def get_mobile_image(self, obj):
        offer = obj.offers.first()
        if offer:
            return offer.mobile_image.url if offer.mobile_image else ""
        return ""


class OfferSerializer(serializers.ModelSerializer):
    vouchers = serializers.SerializerMethodField()
    desktop_image = serializers.SerializerMethodField()
    mobile_image = serializers.SerializerMethodField()
    details_link = serializers.HyperlinkedIdentityField(
        view_name="dashboard:offer-detail"
    )

    class Meta:
        model = ConditionalOffer
        fields = (
            "id",
            "name",
            "offer_type",
            "priority",
            "is_available",
            "vouchers",
            "details_link",
            "desktop_image",
            "mobile_image",
        )

    def get_vouchers(self, obj):
        return VoucherSerializer(many=True, context=self.context).to_representation(
            obj.vouchers.exclude_children().all()
        )

    def get_desktop_image(self, obj):
        return obj.desktop_image.url if obj.desktop_image else ""

    def get_mobile_image(self, obj):
        return obj.mobile_image.url if obj.mobile_image else ""


class OfferGroupSerializer(serializers.ModelSerializer):
    offers = serializers.SerializerMethodField()
    update_link = serializers.HyperlinkedIdentityField(
        view_name="dashboard:offergroup-update"
    )
    delete_link = serializers.HyperlinkedIdentityField(
        view_name="dashboard:offergroup-delete"
    )

    class Meta:
        model = OfferGroup
        fields = (
            "id",
            "name",
            "slug",
            "priority",
            "is_system_group",
            "offers",
            "update_link",
            "delete_link",
        )

    @staticmethod
    def _limit_displayed_offers(offer_group):
        """
        Sometimes, an offer group might have an excessive number of offers attached to it, and each offer might
        include a large number of vouchers.

        For example:

        One offer group contains 500 offers.
        Each offer has 10,000 vouchers.

        This can significantly increase the render time on the Oscar offer dashboard page.
        To mitigate this, the number of offers displayed is limited to a certain threshold.
        """
        if offer_group.offers.count() > DEFAULT_OFFER_LIMIT_TO_DISPLAY:
            return offer_group.offers.all()[:DEFAULT_OFFER_LIMIT_TO_DISPLAY]
        else:
            return offer_group.offers.all()

    def get_offers(self, obj):
        offers = self._limit_displayed_offers(obj)
        return OfferSerializer(offers, many=True, context=self.context).data

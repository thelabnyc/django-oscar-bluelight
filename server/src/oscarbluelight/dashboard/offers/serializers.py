from rest_framework import serializers
from oscarbluelight.offer.models import OfferGroup, ConditionalOffer
from oscarbluelight.voucher.models import Voucher


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
    offers = OfferSerializer(many=True)
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

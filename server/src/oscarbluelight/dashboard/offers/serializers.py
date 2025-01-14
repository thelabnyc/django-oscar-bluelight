from __future__ import annotations

from collections.abc import Iterable
from typing import Any

from rest_framework import serializers
from rest_framework.exceptions import NotFound
from rest_framework.pagination import PageNumberPagination
from rest_framework.utils.serializer_helpers import ReturnList

from oscarbluelight.offer.models import ConditionalOffer, OfferGroup
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

    def get_desktop_image(self, obj: Voucher) -> str:
        offer = obj.offers.first()
        if offer:
            return offer.desktop_image.url if offer.desktop_image else ""
        return ""

    def get_mobile_image(self, obj: Voucher) -> str:
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

    def get_vouchers(self, obj: ConditionalOffer) -> list[dict[str, Any]]:
        ser = VoucherSerializer(many=True, context=self.context)
        return ser.to_representation(  # type:ignore[return-value]
            obj.vouchers.exclude_children().all()
        )

    def get_desktop_image(self, obj: ConditionalOffer) -> str:
        return obj.desktop_image.url if obj.desktop_image else ""

    def get_mobile_image(self, obj: ConditionalOffer) -> str:
        return obj.mobile_image.url if obj.mobile_image else ""


class OffersInGroupPagination(PageNumberPagination):
    page_query_param = "offers_page"
    page_size_query_param = "offers_page_size"
    page_size = 200
    max_page_size = 1000


class OfferGroupSerializer(serializers.ModelSerializer):
    update_link = serializers.HyperlinkedIdentityField(
        view_name="dashboard:offergroup-update"
    )
    delete_link = serializers.HyperlinkedIdentityField(
        view_name="dashboard:offergroup-delete"
    )
    offers = serializers.SerializerMethodField()
    total_offers_count = serializers.SerializerMethodField()

    class Meta:
        model = OfferGroup
        fields = (
            "id",
            "name",
            "slug",
            "priority",
            "is_system_group",
            "offers",
            "total_offers_count",
            "update_link",
            "delete_link",
        )

    def get_offers(self, obj: OfferGroup) -> ReturnList[Any]:
        offers = obj.offers.all()
        paginator = OffersInGroupPagination()
        request = self.context.get("request")
        page: Iterable[ConditionalOffer] | None
        try:
            page = paginator.paginate_queryset(offers, request)  # type:ignore[arg-type]
        except NotFound:
            page = obj.offers.none()
        return OfferSerializer(  # type:ignore[return-value]
            page, many=True, context=self.context
        ).data

    def get_total_offers_count(self, obj: OfferGroup) -> int:
        return obj.offers.count()

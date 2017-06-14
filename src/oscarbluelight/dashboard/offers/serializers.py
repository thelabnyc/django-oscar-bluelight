from rest_framework import serializers
from oscarbluelight.offer.models import OfferGroup, ConditionalOffer
from oscarbluelight.voucher.models import Voucher


class VoucherSerializer(serializers.ModelSerializer):
    details_link = serializers.HyperlinkedIdentityField(view_name='dashboard:voucher-stats')

    class Meta:
        model = Voucher
        fields = (
            'id',
            'name',
            'code',
            'is_active',
            'details_link',
        )


class OfferSerializer(serializers.ModelSerializer):
    vouchers = serializers.SerializerMethodField()
    details_link = serializers.HyperlinkedIdentityField(view_name='dashboard:offer-detail')

    class Meta:
        model = ConditionalOffer
        fields = (
            'id',
            'name',
            'priority',
            'is_available',
            'vouchers',
            'details_link',
        )

    def get_vouchers(self, obj):
        return VoucherSerializer(many=True, context=self.context).to_representation(obj.vouchers.exclude_children().all())


class OfferGroupSerializer(serializers.ModelSerializer):
    offers = OfferSerializer(many=True)
    update_link = serializers.HyperlinkedIdentityField(view_name='dashboard:offergroup-update')
    delete_link = serializers.HyperlinkedIdentityField(view_name='dashboard:offergroup-delete')

    class Meta:
        model = OfferGroup
        fields = (
            'id',
            'name',
            'priority',
            'offers',
            'update_link',
            'delete_link',
        )

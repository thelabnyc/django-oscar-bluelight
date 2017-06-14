from rest_framework import viewsets, permissions
from oscarbluelight.offer.models import OfferGroup
from .serializers import OfferGroupSerializer


class OfferGroupViewSet(viewsets.ModelViewSet):
    queryset = OfferGroup.objects.all()
    serializer_class = OfferGroupSerializer
    permission_classes = [
        permissions.IsAdminUser,
        permissions.DjangoModelPermissions,
    ]

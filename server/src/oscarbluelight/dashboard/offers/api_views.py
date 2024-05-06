from django.core.paginator import Paginator, EmptyPage
from django.http import JsonResponse
from django.views.generic import View
from oscar.core.loading import get_model
from rest_framework import viewsets, permissions
from oscarbluelight.offer.models import OfferGroup
from .serializers import OfferGroupSerializer

ConditionalOffer = get_model("offer", "ConditionalOffer")


class OfferGroupViewSet(viewsets.ModelViewSet):
    queryset = OfferGroup.objects.all()
    serializer_class = OfferGroupSerializer
    permission_classes = [
        permissions.IsAdminUser,
        permissions.DjangoModelPermissions,
    ]


class OfferAPIView(View):
    def get(self, request, *args, **kwargs):
        # Get the page parameter or set default to 1
        page_number = request.GET.get("page", 1)
        query_filter = {
            "name__icontains": request.GET.get("q", ""),
        }
        offer_type = request.GET.get("offer_type")
        if offer_type:
            query_filter["offer_type"] = offer_type
        offers = ConditionalOffer.objects.filter(**query_filter).order_by("id")
        # Paginate the results
        items_per_page = request.GET.get("items_per_page", 10)
        paginator = Paginator(offers, items_per_page)
        try:
            page_obj = paginator.get_page(page_number)
        except EmptyPage:
            # If page is out of range, return the last page
            page_obj = paginator.page(paginator.num_pages)
        return JsonResponse(
            {
                "results": [
                    {"text": offer.name, "id": offer.pk}
                    for offer in page_obj.object_list
                ],
                "pagination": {
                    "more": page_obj.has_next(),
                },
            }
        )

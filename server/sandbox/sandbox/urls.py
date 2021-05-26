from django.apps import apps
from django.conf import settings
from django.conf.urls import include, url, i18n
from django.contrib import admin
from django.views.static import serve
import debug_toolbar


urlpatterns = [
    url(r"^i18n/", include(i18n)),
    url(r"^admin/", admin.site.urls),
    url(
        r"^media/(?P<path>.*)$",
        serve,
        {"document_root": settings.MEDIA_ROOT, "show_indexes": True},
    ),
    url(r"^__debug__/", include(debug_toolbar.urls)),
    url(r"^", include(apps.get_app_config("oscar").urls[0])),
]

from django.apps import apps
from django.conf import settings
from django.conf.urls import i18n
from django.contrib import admin
from django.urls import include, path
from django.views.static import serve
import debug_toolbar

urlpatterns = [
    path("i18n/", include(i18n)),
    path("admin/", admin.site.urls),
    path(
        "media/<path:path>",
        serve,
        {"document_root": settings.MEDIA_ROOT, "show_indexes": True},
    ),
    path("__debug__/", include(debug_toolbar.urls)),
    path(
        "",
        include(apps.get_app_config("oscar").urls[0]),  # type:ignore[attr-defined]
    ),
]

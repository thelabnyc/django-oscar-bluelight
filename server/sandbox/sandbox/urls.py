from django.apps import apps
from django.conf import settings
from django.conf.urls import include, i18n
from django.urls import re_path
from django.contrib import admin
from django.views.static import serve
import debug_toolbar


urlpatterns = [
    re_path(r"^i18n/", include(i18n)),
    re_path(r"^admin/", admin.site.urls),
    re_path(
        r"^media/(?P<path>.*)$",
        serve,
        {"document_root": settings.MEDIA_ROOT, "show_indexes": True},
    ),
    re_path(r"^__debug__/", include(debug_toolbar.urls)),
    re_path(r"^", include(apps.get_app_config("oscar").urls[0])),
]

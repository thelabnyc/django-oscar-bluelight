from django.conf import settings
from django.conf.urls import include, url, i18n
from django.contrib import admin
from django.views.static import serve
from oscar.app import application

urlpatterns = [
    url(r'^i18n/', include(i18n)),
    url(r'^admin/', admin.site.urls),
    url(r'^media/(?P<path>.*)$', serve, {'document_root': settings.MEDIA_ROOT, 'show_indexes': True}),
    url(r'', application.urls),
]

from django.conf import settings
from django.conf.urls import patterns, include, url, i18n
from django.contrib import admin
from django.views.static import serve
from oscar.app import application

urlpatterns = patterns('',
    url(r'^i18n/', include(i18n)),
    url(r'^admin/', include(admin.site.urls)),
    url(r'^media/(?P<path>.*)$', serve, {'document_root': settings.MEDIA_ROOT, 'show_indexes': True}),
    url(r'', include(application.urls)),
)

from django import VERSION as DJANGO_VERSION
if DJANGO_VERSION < (4, 0, 0):
    from django.conf.urls import url
else:
    from django.urls import re_path as url
from flexselect.views import field_changed


urlpatterns = [
    url(r'field_changed', field_changed, name='flexselect_field_changed'),
]

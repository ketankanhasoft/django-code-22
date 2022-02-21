"""truckerpilot URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/3.0/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.conf import settings
from django.conf.urls import url
from django.contrib import admin
from django.urls import include, path
from django.views.static import serve
from drf_yasg import openapi
from drf_yasg.views import get_schema_view
from rest_framework import permissions

schema_view = get_schema_view(
    openapi.Info(
        title="django_demo api",
        default_version=1,
    ),
    public=True,
    permission_classes=(permissions.AllowAny,),
)
api_v1_urls = [
    url("account/", include("account.api_v1.urls", namespace="v1-account")),
    url("jobs/", include("job.api_v1.urls", namespace="v1-job")),
    url("match/", include("match.api_v1.urls", namespace="v1-match")),
]


urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/v1/", include(api_v1_urls)),
    path("explorer/", include("explorer.urls")),
    url(
        r"^swagger/$",
        schema_view.with_ui("swagger", cache_timeout=0),
        name="schema-swagger-ui",
    ),
    url(r"^static/(?P<path>.*)$", serve, {"document_root": settings.STATIC_ROOT}),
    url(r"^media/(?P<path>.*)$", serve, {"document_root": settings.MEDIA_ROOT}),
]

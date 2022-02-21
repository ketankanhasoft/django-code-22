from django.urls import path
from rest_framework import routers
from django.conf.urls import url
from job.api_v1.views import (
    JobModelViewSet,
    MyJobListApiView,
    JobListDetalApiView,
    AllJobListApiView,
    OpenJobListDetalApiView,
    JobListJSONApiView,
    FullJobListApiView,
)

router = routers.SimpleRouter()
router.register("job", JobModelViewSet, basename="job")

app_name = "job"
urlpatterns = router.urls + [
    url(r"my-job/$", MyJobListApiView.as_view()),
    url(r"my-job/(?P<pk>[\w.+_-]+)/$", JobListDetalApiView.as_view()),
    url(r"all-job/$", AllJobListApiView.as_view()),
    url(r"all-job/(?P<pk>[\w.+_-]+)/$", OpenJobListDetalApiView.as_view()),
    url(r"all-job-json/$", JobListJSONApiView.as_view()),
    url(r"full-jobs/$", FullJobListApiView.as_view()),
]

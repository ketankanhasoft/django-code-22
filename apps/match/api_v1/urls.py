from django.conf.urls import url
from django.urls import include
from rest_framework import routers

from match.api_v1 import views

router = routers.SimpleRouter()
router.register("matching", views.MatchViewSet)

chat_router = routers.SimpleRouter()
chat_router.register(r"chat", views.ChatModelViewSet)

interview_schedule_router = routers.SimpleRouter()

app_name = "match"
urlpatterns = router.urls + [
    url(r"matching/(?P<pk>[^/.]+)/company/$", views.ComapanyApiView.as_view()),
    url(r"matching/(?P<pk>[^/.]+)/applier/$", views.ApplierApiView.as_view()),
    url(r"matching/(?P<pk>[^/.]+)/history/$", views.MatchHistoryApiView.as_view()),
    url(r"matching/(?P<pk>[^/.]+)/mark-read/", views.MarkChatRead.as_view()),
    url(r"matching/(?P<pk>[^/.]+)/mark-match-read/", views.MarkMatchRead.as_view()),
    url(r"^matching/(?P<match_id>[^/.]+)/", include(chat_router.urls)),
    url(r"^matching/(?P<match_id>[^/.]+)/", include(interview_schedule_router.urls)),
    url(r"^", include(router.urls)),
]

from django.db.models import Q
from rest_framework import mixins, viewsets
from rest_framework.authentication import TokenAuthentication
from rest_framework.exceptions import NotFound, ValidationError
from rest_framework.generics import ListAPIView, RetrieveAPIView

from common import permissions
from common.paginations import PageNumberPagination50
from match.api_v1.serializers import (
    ApplierSerializer,
    ChatSerializer,
    ChatWriteSerializer,
    CompanyDetailSerializer,
    HistorySerializer,
    MatchSerializer,
    StatusSerializer,
    InterviewScheduleReadSerializer,
    InterviewScheduleWriteSerializer,
    InterviewDateSerializer,
)
from match.models import Chat, History, Match, InterviewSchedule, InterviewDate
from match.permissions import MatchPermission as SpecificMatchPermission
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.shortcuts import get_object_or_404
from rest_framework.permissions import SAFE_METHODS
from common.constants import MatchStatus


class MatchViewSet(
    viewsets.GenericViewSet,
    mixins.ListModelMixin,
    mixins.UpdateModelMixin,
    mixins.RetrieveModelMixin,
):
    serializer_class = MatchSerializer
    queryset = Match.objects.filter(is_active=True).order_by("-rating")
    authentication_classes = (TokenAuthentication,)
    permission_classes = (permissions.MatchPermission,)

    def get_serializer_class(self):
        if self.action == "update":
            return StatusSerializer
        return super(MatchViewSet, self).get_serializer_class()

    def get_queryset(self):
        qs = super(MatchViewSet, self).get_queryset()
        status = self.request.GET.get("status")
        if status is not None:
            status = status.split(",")
            qs = qs.filter(status__in=status)
        if self.request.user.is_admin:
            return qs
        return qs.filter(
            Q(company__user=self.request.user) | Q(applier__user=self.request.user)
        )

    def perform_update(self, serializer):
        old_status = self.get_object().status
        serializer.save()
        new_status = self.get_object().status
        if old_status != new_status:
            match = self.get_object()
            if new_status == MatchStatus.INTERVIEW_AGREED:
                interview_date_id = self.request.data.get("interview_date_id")
                interview_schedule = self.request.data.get("interview_schedule")
                interview_date_record = InterviewDate.objects.get(id=interview_date_id)
                History.objects.create(
                    old_status=old_status,
                    status=new_status,
                    match=match,
                    date=interview_date_record.date,
                    start_time=interview_date_record.start_time,
                    end_time=interview_date_record.end_time,
                    interview_schedule_id=interview_schedule,
                    created_by=self.request.user,
                )
            else:
                History.objects.create(
                    old_status=old_status,
                    status=new_status,
                    match=match,
                    created_by=self.request.user,
                )


class ComapanyApiView(RetrieveAPIView):
    serializer_class = CompanyDetailSerializer
    authentication_classes = (TokenAuthentication,)
    permission_classes = (permissions.ApplierOrAdminPermissions,)
    queryset = Match.objects.filter(is_active=True)

    def get_queryset(self):
        qs = super(ComapanyApiView, self).get_queryset()
        if self.request.user.is_admin:
            return qs
        return qs.filter(
            Q(company__user=self.request.user) | Q(applier__user=self.request.user)
        )

    def get_object(self):
        try:
            return self.get_queryset().get(id=self.kwargs["pk"]).company
        except Exception:
            raise NotFound


class ApplierApiView(RetrieveAPIView):
    serializer_class = ApplierSerializer
    authentication_classes = (TokenAuthentication,)
    permission_classes = (permissions.CompanyOrAdminPermissions,)
    queryset = Match.objects.filter(is_active=True)

    def get_queryset(self):
        qs = super(ApplierApiView, self).get_queryset()
        if self.request.user.is_admin:
            return qs
        return qs.filter(
            Q(company__user=self.request.user) | Q(applier__user=self.request.user)
        )

    def get_object(self):
        try:
            return self.get_queryset().get(id=self.kwargs["pk"]).applier
        except Exception:
            raise NotFound


class MatchHistoryApiView(ListAPIView):
    serializer_class = HistorySerializer
    authentication_classes = (TokenAuthentication,)
    permission_classes = (permissions.CompanyOrAdminPermissions,)
    queryset = History.objects.all()
    pagination_class = None

    def get_queryset(self):
        qs = super(MatchHistoryApiView, self).get_queryset()
        if self.request.user.is_admin:
            return qs
        return qs.filter(
            Q(match_id=self.kwargs["pk"])
            & Q(
                Q(match__company__user=self.request.user)
                | Q(match__applier__user=self.request.user)
            )
        )


class ChatModelViewSet(
    mixins.CreateModelMixin,
    mixins.UpdateModelMixin,
    mixins.DestroyModelMixin,
    mixins.ListModelMixin,
    viewsets.GenericViewSet,
):
    serializer_class = ChatSerializer
    queryset = Chat.objects.filter(is_deleted=False)
    permission_classes = (SpecificMatchPermission,)
    authentication_classes = (TokenAuthentication,)
    pagination_class = PageNumberPagination50

    def get_queryset(self):
        qs = super(ChatModelViewSet, self).get_queryset()
        return qs.filter(
            Q(match_id=self.kwargs["match_id"])
            & Q(
                Q(match__company__user=self.request.user)
                | Q(match__applier__user=self.request.user)
            )
        )

    def perform_create(self, serializer):
        serializer.save(match_id=self.kwargs["match_id"], created_by=self.request.user)

    def get_serializer_class(self):
        if self.request.method == "POST":
            return ChatWriteSerializer
        return self.serializer_class

    def perform_destroy(self, instance):
        latest = Chat.objects.filter(
            match_id=self.kwargs["match_id"], created_by=self.request.user
        ).latest("created_at")
        if instance == latest:
            instance.is_deleted = True
            instance.save()
        else:
            raise ValidationError("Alte Nachrichten können nicht gelöscht werden")


class InterviewScheduleModelViewSet(
    mixins.CreateModelMixin,
    mixins.UpdateModelMixin,
    mixins.DestroyModelMixin,
    mixins.ListModelMixin,
    viewsets.GenericViewSet,
):
    queryset = InterviewSchedule.objects.all()
    authentication_classes = (TokenAuthentication,)
    pagination_class = None

    def get_serializer_class(self):
        if self.request.method in SAFE_METHODS:
            return InterviewScheduleReadSerializer
        return InterviewScheduleWriteSerializer

    def get_queryset(self, *args, **kwargs):
        qs = super(InterviewScheduleModelViewSet, self).get_queryset()
        qs = qs.filter(Q(match=self.kwargs.get("match_id"))).order_by("-created_at")[:1]
        return qs

    def create(self, request, *args, **kwargs):
        request.data["created_by"] = self.request.user.id
        request.data["match"] = self.kwargs.get("match_id")
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        instance = self.perform_create(serializer)
        self.create_interview_dates(request, instance)

        return Response(
            data=InterviewScheduleReadSerializer(instance).data,
            status=status.HTTP_201_CREATED,
        )

    def perform_create(self, serializer):
        return serializer.save()

    def create_interview_dates(self, request, instance):
        interview_date_list = request.data.get("interview_date")
        for i_record in interview_date_list:
            i_record["interview_schedule"] = instance.id
            serializer = InterviewDateSerializer(data=i_record)
            serializer.is_valid(raise_exception=True)
            serializer.save()

    def update(self, request, *args, **kwargs):
        try:
            qs = super(InterviewScheduleModelViewSet, self).get_queryset()
            cur_record = qs.filter(Q(id=self.kwargs.get("pk")))
            qs = super(InterviewScheduleModelViewSet, self).get_queryset()
            cur_record = qs.get(Q(id=self.kwargs.get("pk")))
            if "applier_choice" in request.data:
                cur_record.is_applier_suggested = True
                cur_record.applier_notes = request.data.get("applier_notes")
                cur_record.applier_choice = request.data.get("applier_choice")
                cur_record.save()
            return Response(
                data=InterviewScheduleReadSerializer(cur_record).data,
                status=status.HTTP_200_OK,
            )
        except Exception:
            return Response(status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class MarkChatRead(RetrieveAPIView):
    authentication_classes = (TokenAuthentication,)
    permission_classes = (permissions.MatchPermission,)

    def get(self, request, *args, **kwargs):
        try:
            Chat.objects.filter(match_id=self.kwargs.get("pk")).exclude(
                created_by=self.request.user
            ).update(is_read=True)
            return Response(status=status.HTTP_200_OK)
        except Exception:
            return Response(status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class MarkMatchRead(RetrieveAPIView):
    authentication_classes = (TokenAuthentication,)
    permission_classes = (permissions.MatchPermission,)

    def get(self, request, *args, **kwargs):
        try:
            Match.objects.filter(id=self.kwargs.get("pk")).update(is_read=True)
            return Response(status=status.HTTP_200_OK)
        except Exception:
            return Response(status=status.HTTP_500_INTERNAL_SERVER_ERROR)

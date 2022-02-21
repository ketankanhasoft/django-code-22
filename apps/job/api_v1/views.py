from django.db.models import Q
from rest_framework import status, viewsets
from rest_framework.generics import ListAPIView, RetrieveAPIView, GenericAPIView
from rest_framework.permissions import SAFE_METHODS
from rest_framework.response import Response
from rest_framework.exceptions import NotFound
from common import permissions
from job.api_v1 import serializers
from job.models import Job
from rest_framework.permissions import AllowAny
from common.xmlrender import XMLRenderer
import datetime


class MyJobListApiView(ListAPIView):
    queryset = Job.objects.all().order_by("-is_active")
    permission_classes = (permissions.CompanyPermissions,)
    serializer_class = serializers.JobDetailSerializer

    def get_queryset(self):
        return self.queryset.filter(company__user=self.request.user)


class JobListDetalApiView(RetrieveAPIView):
    serializer_class = serializers.JobDetailSerializer
    permission_classes = (permissions.CompanyPermissions,)
    queryset = Job.objects.all()
    pagination_class = None

    def get_queryset(self):
        try:
            if self.kwargs.get("pk") is not None:
                return self.queryset.filter(Q(id=self.kwargs.get("pk")))
        except Exception:
            raise NotFound


class JobModelViewSet(viewsets.ModelViewSet):
    queryset = Job.objects.all()
    permission_classes = (permissions.CompanyOrAdminPermissions,)

    def get_serializer_class(self):
        if self.request.method in SAFE_METHODS:
            return serializers.JobReadSerializer
        return serializers.JobWriteSerializer

    def update(self, request, *args, **kwargs):
        partial = kwargs.pop("partial", False)
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)
        return Response(serializers.JobReadSerializer(instance).data)

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        instance = self.perform_create(serializer)
        return Response(
            data=serializers.JobReadSerializer(instance).data,
            status=status.HTTP_201_CREATED,
        )

    def get_permissions(self):
        if self.action == "list":
            return [permissions.AdminPermissions()]
        if self.action == "create":
            return [permissions.JobPermission()]
        return [permission() for permission in self.permission_classes]

    def perform_create(self, serializer):
        return serializer.save(company=self.request.user.company)

    def get_queryset(self):
        queryset = super(JobModelViewSet, self).get_queryset()
        if self.request.user.is_company:
            return queryset.filter(company=self.request.user.company)
        return queryset

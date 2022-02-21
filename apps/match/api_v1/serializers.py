from collections import OrderedDict
from rest_framework import serializers
from account.api_v1.serializers import ApplierUserSerializer
from account.models import Applier, Company
from match.models import (
    Match,
    History,
    Chat,
    InterviewSchedule,
    InterviewDate,
    Notification,
)
from common.location import get_lat_long
from common.constants import MatchStatus
from babel.dates import format_date


class StatusSerializer(serializers.ModelSerializer):
    class Meta:
        model = Match
        fields = (
            "status",
            "job_start_date",
        )


class ApplierSerializer(serializers.ModelSerializer):
    user = ApplierUserSerializer(read_only=True)

    class Meta:
        model = Applier
        fields = "__all__"


class CompanyDetailSerializer(serializers.ModelSerializer):
    class Meta:
        model = Company
        fields = "__all__"


class ChatWriteSerializer(serializers.ModelSerializer):
    class Meta:
        model = Chat
        exclude = ("match", "created_by")

    def validate(self, attrs):
        attrs = super(ChatWriteSerializer, self).validate(attrs)
        file = attrs.get("file")
        message = attrs.get("message")
        if not (file or message):
            raise serializers.ValidationError("Nachricht oder Datei erforderlich")
        return attrs


class InterviewScheduleWriteSerializer(serializers.ModelSerializer):
    class Meta:
        model = InterviewSchedule
        exclude = ("latitude", "longitude")

    def create(self, validated_data):
        postcode = validated_data.get("postcode", "")
        city = validated_data.get("city", "")
        street = validated_data.get("street", "")
        lat, long = get_lat_long(f"{street}, {city}, {postcode}")
        validated_data["latitude"] = lat
        validated_data["longitude"] = long
        return super(InterviewScheduleWriteSerializer, self).create(validated_data)


class NotificationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Notification
        fields = "__all__"
        depth = 3

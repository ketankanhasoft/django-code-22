from rest_framework import serializers
from account.models import Applier
from common.constants import (
    ToursTypes,
    AdditionalLicenseType,
    VehicleExperienceTypes,
    ShiftType,
)
from common.location import get_lat_long
from job.models import Job
from account.api_v1.serializers import ApplierUserSerializer, LanguageSerializer
from match.api_v1.serializers import MatchSerializer
from match.models import Match


class JobReadSerializer(serializers.ModelSerializer):
    class Meta:
        model = Job
        fields = "__all__"
        depth = 1


class ApplierReadSerializer(serializers.ModelSerializer):
    language = LanguageSerializer(many=True)
    user = ApplierUserSerializer(read_only=True)
    status = serializers.SerializerMethodField()
    rating = serializers.SerializerMethodField()

    class Meta:
        model = Applier
        exclude = ("created_at", "updated_at")

    def get_status(self, obj):
        try:
            return self.context["curr_obj"].rel_matches.get(applier=obj).status
        except Exception as e:
            print(str(e))

    def get_rating(self, obj):
        try:
            return self.context["curr_obj"].rel_matches.get(applier=obj).rating
        except Exception as e:
            print(str(e))


class JobWriteSerializer(serializers.ModelSerializer):
    shift = serializers.MultipleChoiceField(choices=ShiftType.CHOICES)
    tours = serializers.MultipleChoiceField(choices=ToursTypes.CHOICES)
    vehicle_experience = serializers.MultipleChoiceField(
        choices=VehicleExperienceTypes.CHOICES
    )
    additional_license = serializers.MultipleChoiceField(
        choices=AdditionalLicenseType.CHOICES
    )

    class Meta:
        model = Job
        exclude = ("company", "latitude", "longitude")

    def create(self, validated_data):
        postcode = validated_data.get("postcode", "")
        city = validated_data.get("city", "")
        street = validated_data.get("street", "")
        lat, long = get_lat_long(f"{street}, {city}, {postcode}")
        validated_data["latitude"] = lat
        validated_data["longitude"] = long
        return super(JobWriteSerializer, self).create(validated_data)

    def update(self, instance, validated_data):
        if "postcode" in validated_data:
            postcode = validated_data.get("postcode", instance.postcode)
            city = validated_data.get("city", instance.city)
            street = validated_data.get("street", instance.street)
            lat, long = get_lat_long(f"{street}, {city}, {postcode}")
            if lat and long:
                validated_data["latitude"], validated_data["longitude"] = lat, long
        return super(JobWriteSerializer, self).update(instance, validated_data)


class JobDetailSerializer(serializers.ModelSerializer):
    match = serializers.SerializerMethodField()

    class Meta:
        model = Job
        fields = "__all__"
        depth = 1

    def get_match(self, obj):
        data = MatchSerializer(
            Match.objects.filter(job=obj, status__gte=2, is_active=True)
            .exclude(rating=0, status__in=(8, 9))
            .order_by("-rating"),
            many=True,
            context=self.context,
        ).data
        return data


class OpenJobReadSerializer(serializers.ModelSerializer):
    class Meta:
        model = Job
        fields = (
            "id",
            "title",
            "city",
            "postcode",
            "tours",
            "shift",
            "external_title",
            "salary_minimum",
            "salary_maximum",
        )

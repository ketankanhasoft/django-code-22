from django.db import models
from multiselectfield import MultiSelectField

from common.constants import (
    LicenseTypes,
    ShiftType,
    ToursTypes,
    VehicleExperienceTypes,
    AdditionalLicenseType,
    Languages,
)
from common.model import EarthDistanceQuerySet, TimeStampedModel
from account.models import Language
import datetime


class Job(TimeStampedModel):
    external_id = models.IntegerField(null=True, blank=True)
    title = models.CharField(max_length=127)
    external_title = models.CharField(max_length=127, null=True, blank=True)
    external_created_at = models.DateTimeField(null=True, blank=True)
    company = models.ForeignKey(
        "account.Company", related_name="rel_jobs", on_delete=models.CASCADE
    )
    start_work = models.DateField()
    language = models.ManyToManyField("account.Language", related_name="rel_jobs")
    work_experience = models.PositiveSmallIntegerField()
    license = models.CharField(choices=LicenseTypes.CHOICES, max_length=30)
    shift = MultiSelectField(choices=ShiftType.CHOICES)
    tours = MultiSelectField(choices=ToursTypes.CHOICES, min_choices=1)
    vehicle_experience = MultiSelectField(
        choices=VehicleExperienceTypes.CHOICES, min_choices=1
    )
    postcode = models.CharField(max_length=20)
    city = models.CharField(max_length=155)
    street = models.CharField(blank=True, null=True, max_length=155)
    latitude = models.FloatField(max_length=15)
    longitude = models.FloatField(max_length=15)
    is_active = models.BooleanField(default=True)
    additional_license = MultiSelectField(
        choices=AdditionalLicenseType.CHOICES, default=AdditionalLicenseType.NO_LICENSE
    )
    being_transported = models.TextField(default=None, null=True, blank=True)
    specific_tasks = models.TextField(default=None, null=True, blank=True)
    benefit = models.TextField(default="", blank=True, null=True)
    salary_minimum = models.IntegerField(blank=True, null=True)
    salary_maximum = models.IntegerField(blank=True, null=True)
    is_need_additional_driver_license = models.BooleanField(default=False)
    is_need_driver_license = models.BooleanField(default=False)
    is_need_language_skills = models.BooleanField(default=False)
    is_need_vehicle_type_experience = models.BooleanField(default=False)
    is_need_work_experience = models.BooleanField(default=False)
    is_need_professional_license = models.BooleanField(default=False)

    def __str__(self):
        return self.title

    @property
    def language_skill(self):
        return ",".join(
            [
                f"{lng.get_name_display()} {lng.get_rating_display()}"
                for lng in self.language.filter(
                    name__in=[Languages.ENGLISH, Languages.GERMAN, Languages.POLISH]
                )
            ]
        )

    @property
    def language_skill_rating(self):
        return ",".join(
            [
                f"{lng.get_rating_display()}"
                for lng in self.language.filter(
                    name__in=[Languages.ENGLISH, Languages.GERMAN, Languages.POLISH]
                )
            ]
        )

    @property
    def language_skill_rating_german(self):
        return ",".join(
            [
                f"{lng.get_rating_display()}"
                for lng in self.language.filter(name__in=[Languages.GERMAN])
            ]
        )

    @property
    def xml_language(self):
        return "".join(
            [
                f"<language><item>{lng.get_name_display()}</item><skill>{lng.get_rating_display()}</skill></language>"
                for lng in self.language.filter(
                    name__in=[Languages.ENGLISH, Languages.GERMAN, Languages.POLISH]
                )
            ]
        )

    def save(self, *args, **kwargs):
        if self.id is None:
            self.external_title = self.title
            self.external_created_at = datetime.datetime.now()
        super(Job, self).save(*args, **kwargs)


class JobStatus(models.Model):
    status_id = models.PositiveSmallIntegerField()
    english_name = models.CharField(blank=True, null=True, max_length=255)
    german_name = models.CharField(blank=True, null=True, max_length=255)

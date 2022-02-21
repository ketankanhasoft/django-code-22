from decimal import Decimal

from account.models import Applier
from common.constants import Languages, MatchStatus, AdditionalLicenseType, LicenseTypes
from common.location import find_duration_distance
from common.model import EarthDistance, LlToEarth
from job.models import Job
from match.models import Match
from job.api_v1 import serializers


class Matching(object):
    def __init__(self, job=None, applier=None):
        self.job = job
        self.applier = applier
        self.calculate_rate()

    def calculate_rate(self):
        if not (isinstance(self.job, Job) and isinstance(self.applier, Applier)):
            self.save(job_distance=Decimal(0), rate=0)
            return
        if not all(
            [
                self.applier.latitude,
                self.applier.longitude,
                self.job.latitude,
                self.job.longitude,
            ]
        ):
            self.save(job_distance=Decimal(0), rate=0)
            return
        rating = 20

        job_distance, job_duration = find_duration_distance(
            self.job.latitude,
            self.job.longitude,
            self.applier.latitude,
            self.applier.longitude,
        )
        if job_duration is not None:
            self.save(job_distance=Decimal(0), rate=0, job_duration=job_duration)

        tour_list = list(self.job.tours)
        applier_tour_list = list(self.applier.tours)
        max_distance = 35
        if "national" in applier_tour_list or "international" in applier_tour_list:
            max_distance = 60
        else:
            max_distance = 35

        if (
            "national" in tour_list or "international" in tour_list
        ) and job_distance <= max_distance:
            pass
        elif "local" in tour_list and job_distance <= max_distance:
            pass
        else:
            return

        distance_rate = self.calculate_distance_rate(
            job_distance, self.applier.distance
        )
        license_rate = self.calculate_license_rate(
            self.job.license, self.applier.license
        )

        stv_rate = self.calculate_shift_tour_vehicle_experience_rate(
            (self.job.shift, self.job.tours, self.job.vehicle_experience),
            (self.applier.shift, self.applier.tours, self.applier.vehicle_experience),
        )
        total_rate = (
            distance_rate
            + license_rate
            + stv_rate
            + self.calculate_language_rate()
            + rating
        )
        self.save(job_distance=job_distance, rate=total_rate)
        return True

    @staticmethod
    def get_language_rating(instnse=None):
        try:
            return max(
                instnse.language.filter(name=Languages.GERMAN).values_list(
                    "rating", flat=True
                )
            )
        except Exception:
            return 0

    def calculate_language_rate(self):
        job_rate, applier_rate = self.get_language_rating(
            self.job
        ), self.get_language_rating(self.applier)
        if job_rate <= applier_rate:
            return 8
        elif applier_rate == 0:
            return 0
        return 4

    def save(self, job_distance, rate, job_duration=None):
        if rate > 0:
            match, _ = Match.objects.get_or_create(
                applier=self.applier,
                company=self.job.company,
                job=self.job,
            )
            match.distance = round(job_distance, 3)
            match.rating = rate
            match.is_read = False
            # match.is_active = True
            if job_duration is not None:
                match.duration = job_duration
            match.save()

    @staticmethod
    def calculate_license_rate(job_license, applier_license):
        license_dict = {"CE": 4, "C": 3, "C1E": 2}
        applier_license_point = license_dict.get(applier_license, 1)
        job_license_point = license_dict.get(job_license, 1)
        if applier_license_point == 4:
            return 15
        elif applier_license_point == job_license_point:
            return 15
        else:
            return 0

    @staticmethod
    def calculate_distance_rate(distance, applier_distance_range):
        rating = 0
        if distance <= 10:
            rating += 20
        elif distance > applier_distance_range:
            return 0
        else:
            rating += (1 - (distance - 10) / (applier_distance_range - 10)) * 20
        return rating

    @staticmethod
    def calculate_shift_tour_vehicle_experience_rate(job_stv, applier_stv):
        job_shift, job_tour, job_vehicle_experience = job_stv
        applier_shift, applier_tour, applier_vehicle_experience = applier_stv
        rating = 0
        if bool(set(job_shift).intersection(set(applier_shift))):
            rating += 15

        if bool(set(job_tour).intersection(set(applier_tour))):
            rating += 10

        if bool(
            set(job_vehicle_experience).intersection(set(applier_vehicle_experience))
        ):
            rating += 10

        return rating


def update_job_and_matching(applier):
    applier_tour_list = list(applier.tours)

    # Need to select all jobs within 100KM distance #
    active_jobs = Job.objects.filter(is_active=True).in_distance(
        distance=60 * 1000.0,
        fields=("latitude", "longitude"),
        points=(applier.latitude, applier.longitude),
    )

    for job in active_jobs:
        tour_list = list(job.tours)

        must_have_break = check_must_have(job=job, applier=applier)

        if not must_have_break:
            job_distance = job._ed_distance / 1000.0

            max_distance = 35
            if "national" in applier_tour_list or "international" in applier_tour_list:
                max_distance = 60
            else:
                max_distance = 35

            if (
                "national" in tour_list or "international" in tour_list
            ) and job_distance <= max_distance:
                Matching(job=job, applier=applier)
            elif "local" in tour_list and job_distance <= max_distance:
                Matching(job=job, applier=applier)
        else:
            try:
                match = Match.objects.get(
                    applier=applier,
                    company=job.company,
                    job=job,
                )
                if match.status == MatchStatus.MATCHED:
                    match.is_active = False
                    match.save()
            except Match.DoesNotExist:
                pass

    active_jobs = active_jobs.values_list("id", flat=True)
    for match in Match.objects.filter(applier_id=applier.id, is_active=True):
        if match.job_id in active_jobs:
            continue
        elif match.status == MatchStatus.MATCHED:
            match.is_active = False
            match.save()
        else:
            job_distance, job_duration = find_duration_distance(
                match.job.latitude,
                match.job.longitude,
                match.applier.latitude,
                match.applier.longitude,
            )
            match.distance = round(job_distance, 3)
            match.duration = job_duration
            match.is_active = True
            match.save()


def update_matching(job):
    tour_list = list(job.tours)

    for applier in Applier.objects.filter().annotate(
        distance_meter=EarthDistance(
            [
                LlToEarth([job.latitude, job.longitude]),
                LlToEarth(["latitude", "longitude"]),
            ]
        )
    ):

        applier_tour_list = list(applier.tours)
        must_have_break = check_must_have(job=job, applier=applier)

        if must_have_break:
            try:
                match = Match.objects.get(
                    applier=applier,
                    company=job.company,
                    job=job,
                )
                if match.status == MatchStatus.MATCHED:
                    match.is_active = False
                    match.save()
            except Match.DoesNotExist:
                pass
        else:
            if applier.distance_meter is not None:
                job_distance = applier.distance_meter / 1000.0

                if job.is_active:
                    max_distance = 35

                    if (
                        "national" in applier_tour_list
                        or "international" in applier_tour_list
                    ):
                        max_distance = 60
                    else:
                        max_distance = 35

                    if (
                        "national" in tour_list or "international" in tour_list
                    ) and job_distance <= max_distance:
                        Matching(job=job, applier=applier)
                    elif "local" in tour_list and job_distance <= max_distance:
                        Matching(job=job, applier=applier)
                    else:
                        try:
                            match = Match.objects.get(
                                applier=applier,
                                company=job.company,
                                job=job,
                            )
                            if match.status == MatchStatus.MATCHED:
                                match.is_active = False
                                match.save()
                            else:
                                job_distance, job_duration = find_duration_distance(
                                    job.latitude,
                                    job.longitude,
                                    applier.latitude,
                                    applier.longitude,
                                )
                                match.distance = round(job_distance, 3)
                                match.duration = job_duration
                                match.is_active = True
                                match.save()
                        except Match.DoesNotExist:
                            pass
                else:
                    try:
                        match = Match.objects.get(
                            applier=applier,
                            company=job.company,
                            job=job,
                        )
                        if (
                            match.status == MatchStatus.MATCHED
                            or match.status == MatchStatus.COMPANY_CANCEL
                            or match.status == MatchStatus.APPLICANT_CANCEL
                        ):
                            match.is_active = False
                            match.save()
                    except Match.DoesNotExist:
                        pass


def check_must_have(job, applier):
    try:
        if job.is_need_additional_driver_license:
            applier_additional_license = list(applier.additional_license)
            job_additional_license = list(job.additional_license)
            if not all(
                item in applier_additional_license for item in job_additional_license
            ):
                return True

        if job.is_need_driver_license and applier.license != LicenseTypes.CE:
            if job.license != applier.license:
                return True

        if job.is_need_language_skills:
            job_rate, applier_rate = Matching.get_language_rating(
                job
            ), Matching.get_language_rating(applier)
            if applier_rate < job_rate:
                return True

        if job.is_need_work_experience:
            if job.work_experience > applier.work_experience:
                return True

        if job.is_need_vehicle_type_experience:
            applier_vahicle_exp = list(applier.vehicle_experience)
            job_vahicle_exp = list(job.vehicle_experience)
            if not all(item in applier_vahicle_exp for item in job_vahicle_exp):
                return True

        if job.is_need_professional_license:
            if not applier.professional_license:
                return True

        return False
    except Exception:
        return False

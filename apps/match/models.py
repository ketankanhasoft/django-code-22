from django.db import models

from common.constants import MatchStatus
from common.model import TimeStampedModel
from common.constants import InterviewSlot
from django.core.exceptions import ValidationError


class Match(TimeStampedModel):
    status = models.PositiveSmallIntegerField(
        choices=MatchStatus.CHOICES, default=MatchStatus.MATCHED
    )
    applier = models.ForeignKey(
        "account.Applier", related_name="rel_matches", on_delete=models.CASCADE
    )
    company = models.ForeignKey(
        "account.Company", related_name="rel_mathces", on_delete=models.CASCADE
    )
    job = models.ForeignKey(
        "job.Job", related_name="rel_matches", on_delete=models.CASCADE
    )
    distance = models.FloatField(default=0.0)
    rating = models.PositiveSmallIntegerField(default=0)
    duration = models.PositiveSmallIntegerField(default=0)
    is_read = models.BooleanField(default=False, blank=True, null=True)
    is_active = models.BooleanField(default=True)
    job_start_date = models.DateField(blank=True, null=True)

    class Meta:
        unique_together = ("applier", "job")
        verbose_name = "Match"
        verbose_name_plural = "Match"
        ordering = ["-created_at"]

    def __str__(self):
        return "{}{}{}{}".format(self.applier, self.job, self.company, self.status)


class InterviewDate(TimeStampedModel):
    date = models.DateField()
    start_time = models.TimeField()
    end_time = models.TimeField()
    interview_schedule = models.ForeignKey(
        "InterviewSchedule", related_name="interview_date", on_delete=models.CASCADE
    )


class Notification(TimeStampedModel):
    match = models.ForeignKey(
        "Match", related_name="rel_notification", on_delete=models.CASCADE
    )
    for_user = models.ForeignKey("account.User", on_delete=models.CASCADE)
    is_read = models.BooleanField(default=False, blank=True, null=True)
    message = models.TextField(null=True, blank=True)
    status = models.PositiveSmallIntegerField(choices=MatchStatus.CHOICES)
    interview_date = models.DateField(blank=True, null=True)

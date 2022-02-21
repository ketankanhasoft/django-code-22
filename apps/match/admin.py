from django.contrib import admin

from match import models
from import_export.admin import ImportExportModelAdmin
from common.constants import MatchStatus

# Register your models here.

from import_export import resources


class MatchResource(resources.ModelResource):
    class Meta:
        model = models.Match
        fields = (
            "applier__user__first_name",
            "applier__user__last_name",
            "applier__user__email",
            "applier__phone_number",
            "company__name",
            "company__user__first_name",
            "company__user__last_name",
            "company__user__email",
            "company__phone_number",
            "job__title",
            "distance",
            "rating",
            "status",
            "created_at",
            "updated_at",
        )


@admin.register(models.History)
class HistoryAdmin(admin.ModelAdmin):
    class Meta:
        model = models.History

    list_display = ["match", "old_status", "status", "created_at"]


@admin.register(models.Match)
class MatchApplied(ImportExportModelAdmin):
    resource_class = MatchResource

    list_display = [
        "status",
        "applier",
        "company",
        "job",
        "distance",
        "rating",
        "created_at",
        "updated_at",
    ]
    search_fields = ("applier__user__email", "company__user__email")
    list_filter = ("status", "company")


@admin.register(models.Chat)
class ChatAdmin(admin.ModelAdmin):
    list_display = ["match", "message"]


@admin.register(models.InterviewSchedule)
class InterviewScheduleAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "match",
        "postcode",
        "city",
        "street",
        "note",
        "is_applier_suggested",
        "applier_choice",
        "notes",
        "applier_notes",
    )


@admin.register(models.InterviewDate)
class InterviewDateAdmin(admin.ModelAdmin):
    list_display = ("interview_schedule", "date", "start_time", "end_time")

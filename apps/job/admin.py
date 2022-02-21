from django.contrib import admin

from job import models


@admin.register(models.Job)
class JobAdmin(admin.ModelAdmin):
    list_display = (
        "title",
        "company",
        "is_active",
        "external_id",
        "external_title",
        "external_created_at",
    )

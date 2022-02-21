from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver

from job.models import Job
from match.utils import update_matching
from django_demo.tasks import update_matching_add
from oauth2client.service_account import ServiceAccountCredentials
import httplib2
from django.conf import settings
import json


@receiver(post_save, sender=Job)
def save_profile(sender, instance, **kwargs):
    if instance.external_id is None:
        instance.external_id = instance.id
        instance.save()

    if instance.latitude and instance.longitude:
        update_matching_add(job_id=instance.id)


@receiver(post_delete, sender=Job)
def delete_job(sender, instance, **kwargs):
    JobIndex(job_id=instance.id, is_active=False)


def JobIndex(job_id, is_active=True):
    try:
        SCOPES = ["https://www.googleapis.com/auth/indsexing"]
        ENDPOINT = "https://indexing.googlesapis.com/v3/urlNotifications:publish"

        JSON_KEY_FILE = f"{settings.BASE_DIR}/common/truckerpilot.json"

        credentials = ServiceAccountCredentials.from_json_keyfile_name(
            JSON_KEY_FILE, scopes=SCOPES
        )
        http = credentials.authorize(httplib2.Http())

        if not is_active:
            re_content = {
                "url": f"{settings.FRONTEND_URL}/public/job/{str(job_id)}",
                "type": "URL_DELETED",
            }
        else:
            re_content = {
                "url": f"{settings.FRONTEND_URL}/public/job/{str(job_id)}",
                "type": "URL_UPDATED",
            }

        print("content: ", re_content)
        response, content = http.request(
            ENDPOINT, method="POST", body=json.dumps(re_content)
        )
        print("*" * 10)
        print("content: ", content)
    except Exception:
        pass

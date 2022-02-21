from __future__ import absolute_import
from celery import shared_task
from django_demo.celery import app
from account.models import Applier, User, Company
from job.models import Job
from match.models import Match, Chat, History
from match.utils import update_job_and_matching, update_matching
from celery.task.schedules import crontab
from celery.task import periodic_task
import datetime
from datetime import timedelta
from common import mailjet
from common.constants import MatchStatus
import dateutil.parser
from babel.dates import format_date
from django.conf import settings


@shared_task
def update_matching_add(job_id):
    try:
        job = Job.objects.get(id=job_id)
        update_matching(job)
    except Exception:
        pass


@shared_task
def update_job_and_matching_add(applier_id):
    try:
        applier = Applier.objects.get(id=applier_id)
        update_job_and_matching(applier)
    except Exception:
        pass


@periodic_task(run_every=crontab(minute=0, hour=16, day_of_week="sun"))
def send_weekly_email():
    date_before_7_days = datetime.datetime.now() - timedelta(days=7)
    last_sunday_4_pm = datetime.datetime(
        date_before_7_days.year,
        date_before_7_days.month,
        date_before_7_days.day,
        16,
        0,
        0,
    )
    applier_list = Applier.objects.all()
    for applier in applier_list:
        get_match_count = Match.objects.filter(
            status=MatchStatus.MATCHED,
            applier=applier,
            created_at__gte=last_sunday_4_pm,
            rating__gte=60,
        ).count()
        if get_match_count > 0:
            pass


@periodic_task(run_every=crontab(minute=0, hour=0))
def deactivate_cancelled_match():
    date_before_7_days = datetime.datetime.now().date() - timedelta(days=7)
    Match.objects.filter(
        updated_at__date__lte=date_before_7_days,
        status__in=(MatchStatus.APPLICANT_CANCEL, MatchStatus.COMPANY_CANCEL),
    ).update(is_active=False)
    pass


@periodic_task(run_every=crontab(minute=0, hour=18))
def unfinished_applier_email_send():

    now = datetime.datetime.now()
    yesterday = datetime.datetime.now() - timedelta(days=1)
    today_5_pm = datetime.datetime(now.year, now.month, now.day, 17, 0, 0)

    applier_list = User.objects.filter(
        role=2, created_at__gte=yesterday, created_at__lte=today_5_pm
    )

    for applier in applier_list:
        if not applier.has_completed_profile:
            mailjet.send_unfinish_applier_registration_email(email=applier.email)
    pass


@periodic_task(
    run_every=crontab(minute=0, hour=0, day_of_month="1-7", day_of_week="fri")
)
def not_answered_match_or_chat_message_to_company_email():
    before_3_day = (datetime.datetime.now() - timedelta(days=3)).replace(tzinfo=None)
    company_list = Company.objects.filter(ppa=False)

    for company in company_list:
        unanswered_match_list = {}

        match_list = Match.objects.filter(
            job__company=company,
            updated_at__lte=before_3_day,
            status__in=(
                MatchStatus.APPLIED,
                MatchStatus.CHECKED,
                MatchStatus.INTERVIEW_PROPOSED_BY_COMPANY,
                MatchStatus.ALTERNETE_DATE_FROM_APPLIER,
                MatchStatus.ANOTHER_INTERVIEW_PROPOSED_C,
                MatchStatus.INTERVIEW_AGREED,
            ),
            is_active=True,
        )
        for match in match_list:

            job_tital = match.job.title
            _str_job_id = str(match.job.id)
            if _str_job_id not in unanswered_match_list:
                unanswered_match_list[_str_job_id] = {}
                unanswered_match_list[_str_job_id]["job_title"] = job_tital
                unanswered_match_list[_str_job_id]["job_city"] = match.job.city
                unanswered_match_list[_str_job_id]["match_list"] = []

            applier_info = {
                "name": match.applier.user.get_full_name(),
                "status": match.get_status_display(),
                "message": "0",
            }
            unanswered_match_list[_str_job_id]["match_list"].append(applier_info)

        match_list = Match.objects.filter(job__company=company, is_active=True)
        for match in match_list:
            last_chat = Chat.objects.filter(match=match).last()
            if (
                last_chat is not None
                and last_chat.created_by.is_applier
                and (dateutil.parser.parse(str(last_chat.created_at))).replace(
                    tzinfo=None
                )
                < before_3_day
            ):
                job_tital = match.job.title
                _str_job_id = str(match.job.id)
                if _str_job_id not in unanswered_match_list:
                    unanswered_match_list[_str_job_id] = {}
                    unanswered_match_list[_str_job_id]["job_title"] = job_tital
                    unanswered_match_list[_str_job_id]["job_city"] = match.job.city
                    unanswered_match_list[_str_job_id]["match_list"] = []
                applier_info = {
                    "name": match.applier.user.get_full_name(),
                    "status": match.get_status_display(),
                    "message": "1",
                }
                unanswered_match_list[_str_job_id]["match_list"].append(applier_info)

        if len(unanswered_match_list) > 0:
            mailjet.send_email_not_answered_match_or_chat_message_to_company_email(
                email=company.user.email,
                username=company.user.get_full_name(),
                unanswered_match_list=unanswered_match_list,
            )


@periodic_task(run_every=crontab(minute=0, hour=18))
def interview_proposed_by_c_user_remiender_sms():
    before_2_day = (datetime.datetime.now() - timedelta(days=2)).replace(tzinfo=None)
    match_list = Match.objects.filter(
        updated_at__date=before_2_day,
        status__in=(MatchStatus.INTERVIEW_PROPOSED_BY_COMPANY,),
        is_active=True,
    )
    for match in match_list:
        mailjet.send_interview_proposed_c_remiender_sms(
            phone_number=match.applier.phone_number, match=match
        )
    pass


@periodic_task(run_every=crontab(minute=30, hour=8))
def after_interview_remiender_email():
    before_1_day = (datetime.datetime.now() - timedelta(days=1)).date()
    match_list = History.objects.filter(
        match__status__in=(MatchStatus.INTERVIEW_AGREED,),
        status__in=(MatchStatus.INTERVIEW_AGREED,),
        date=before_1_day,
    )
    for h in match_list:
        url = (
            f"{settings.FRONTEND_URL}/job-profile/{h.match.job.id}/{h.match.applier.id}"
        )
        mailjet.after_interview_remiender_to_company(
            email=h.match.company.user.email,
            username=h.match.company.user.get_full_name(),
            applier=h.match.applier.user.get_full_name(),
            match_link=url,
        )

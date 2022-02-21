from django.db.models.signals import post_save
from django.dispatch import receiver
from django.conf import settings
from common import mailjet
from common.constants import MatchStatus
from match.models import Chat, History, InterviewSchedule, InterviewDate, Notification
from babel.dates import format_date, format_datetime, format_time
import datetime
from datetime import timedelta


@receiver(post_save, sender=Chat)
def save_profile(sender, instance, **kwargs):

    file_name = ""
    if not instance.is_deleted:
        if instance.file:
            file_name = str(instance.file).split("/")[1]

        if instance.created_by.is_applier:
            redirect_url = f"{settings.FRONTEND_URL}/job-profile/{instance.match.job.id}/{instance.match.applier.id}"
            mailjet.send_chat_message_mail(
                email=instance.match.company.user.email,
                username=instance.match.company.user.get_full_name(),
                job_title=instance.match.job.title,
                author=instance.match.applier.user.get_full_name(),
                message=instance.message,
                redirect_url=redirect_url,
                city_of_job=instance.match.job.city,
                file_name=file_name,
                file_url="",
            )
            create_notification(
                match=instance.match,
                user=instance.match.company.user,
                status=MatchStatus.NOTIFICATION_AFTER_MESSAGE,
            )
        if instance.created_by.is_company:
            redirect_url = f"{settings.FRONTEND_URL}/applications/{instance.match.id}"
            mailjet.send_chat_message_mail(
                email=instance.match.applier.user.email,
                username=instance.match.applier.user.get_full_name(),
                job_title=instance.match.job.title,
                author=instance.match.company.name,
                message=instance.message,
                redirect_url=redirect_url,
                city_of_job=instance.match.job.city,
                file_name=file_name,
                file_url="",
            )

            mailjet.send_chat_sms(
                phone_number=instance.match.applier.phone_number, match=instance.match
            )

            # CREATE NOTIFICATION FOR APPLIER #
            create_notification(
                match=instance.match,
                user=instance.match.applier.user,
                status=MatchStatus.NOTIFICATION_AFTER_MESSAGE,
            )


@receiver(post_save, sender=History)
def send_proper_email(sender, instance, **kwargs):

    # CREATE NOTIFICATION #
    if (
        instance.status == MatchStatus.CHECKED
        or instance.status == MatchStatus.INTERVIEW_PROPOSED_BY_COMPANY
        or instance.status == MatchStatus.ANOTHER_INTERVIEW_PROPOSED_C
        or instance.status == MatchStatus.INTERVIEW_AGREED
        or instance.status == MatchStatus.COMPANY_AGREED
        or instance.status == MatchStatus.COMPANY_CANCEL
    ):

        # CREATE NOTIFICATION FOR APPLIER #
        create_notification(
            match=instance.match,
            user=instance.match.applier.user,
            status=instance.status,
            interview_date=instance.date,
        )

    if (
        instance.status == MatchStatus.APPLIED
        or instance.status == MatchStatus.INTERVIEW_AGREED
        or instance.status == MatchStatus.ALTERNETE_DATE_FROM_APPLIER
        or instance.status == MatchStatus.APPLICANT_AGREED
        or instance.status == MatchStatus.APPLICANT_CANCEL
    ):
        # CREATE NOTIFICATION FOR COMPANY #
        create_notification(
            match=instance.match,
            user=instance.match.company.user,
            status=instance.status,
            interview_date=instance.date,
        )

    if instance.status == MatchStatus.APPLIED:

        applier = instance.match.applier
        match = instance.match
        pdf_variables = {
            "email": applier.user.email,
            "username": applier.user.get_full_name(),
            "postalcode": applier.postcode,
            "city": applier.city,
            "phone_number": applier.phone_number,
            "driver_licence": applier.license,
            "drivercode": "Ja" if applier.professional_license else "Nein",
            "language_skill": applier.language_skill,
            "work_experience": applier.work_experience,
            "vehicle_experience": applier.vehicle_experience,
            "additional_driver_licence": applier.additional_license,
            "shifts": applier.shift,
            "tours": applier.tours,
            "start_to_work": format_date(
                applier.start_work, format="d. MMMM y", locale="de_DE"
            ),
            "birth_year": applier.birth_year,
            "last_employers": applier.employer_info,
        }
        mailjet.send_email_applicant_after_application(
            email=match.applier.user.email,
            username=match.applier.user.get_full_name(),
            company_name=match.company.name,
            job_title=match.job.title,
            dashboard_link="#",
            pdf_variables=pdf_variables,
            match_id=match.id,
            c_user_name=match.company.user.get_full_name(),
            c_user_phone=match.company.phone_number,
        )
        mailjet.send_email_company_after_application(
            email=match.company.user.email,
            c_contact_email=match.company.contact_email,
            company_username=match.company.user.get_full_name(),
            applier=match.applier.user.get_full_name(),
            job_position=match.job.title,
            pdf_variables=pdf_variables,
            applier_id=match.applier.id,
            job_id=match.job.id,
            city_of_job=match.job.city,
        )

    if instance.status == MatchStatus.INTERVIEW_PROPOSED_BY_COMPANY:
        company = instance.match.company
        applier = instance.match.applier
        org_reply_date = datetime.datetime.now().date() + timedelta(days=3)
        proposed_dates = []

        # try:
        interview_schedule = InterviewSchedule.objects.filter(
            match=instance.match
        ).order_by("-created_at")[:1]
        interview_dates = InterviewDate.objects.filter(
            interview_schedule=interview_schedule
        )

        for interview_date in interview_dates:
            start_time = format_date(interview_date.start_time, format="HH:mm")
            end_time = format_date(interview_date.end_time, format="HH:mm")
            i_date = f"{format_date(interview_date.date, format='E d.MM.y', locale='de_DE')}, {start_time} - {end_time} Uhr"
            proposed_dates.append(i_date)
            if interview_date.date <= org_reply_date:
                org_reply_date = interview_date.date - timedelta(days=1)

        reply_date = format_date(org_reply_date, format="d.MM.y", locale="de_DE")

        URL = f"{settings.FRONTEND_URL}/applications/{instance.match.id}"

        mailjet.send_mail_date_proposal_for_job_interview(
            email=applier.user.email,
            username=applier.user.get_full_name(),
            company=company.name,
            company_adress=company.address,
            proposed_dates=proposed_dates,
            reply_date=reply_date,
            company_chat_link=URL,
        )

        # SMS #
        mailjet.send_interview_proposed_c_sms(
            phone_number=applier.phone_number, match=instance.match
        )

    if instance.status == MatchStatus.ANOTHER_INTERVIEW_PROPOSED_C:
        company = instance.match.company
        applier = instance.match.applier
        org_reply_date = datetime.datetime.now().date() + timedelta(days=3)
        proposed_dates = []

        # try:
        interview_schedule = InterviewSchedule.objects.filter(
            match=instance.match
        ).order_by("-created_at")[:1]
        interview_dates = InterviewDate.objects.filter(
            interview_schedule=interview_schedule
        )

        for interview_date in interview_dates:
            start_time = format_date(interview_date.start_time, format="HH:mm")
            end_time = format_date(interview_date.end_time, format="HH:mm")
            i_date = f"{format_date(interview_date.date, format='E d.MM.y', locale='de_DE')}, {start_time} - {end_time} Uhr"
            proposed_dates.append(i_date)
            if interview_date.date <= org_reply_date:
                org_reply_date = interview_date.date - timedelta(days=1)

        reply_date = format_date(org_reply_date, format="d.MM.y", locale="de_DE")

        URL = f"{settings.FRONTEND_URL}/applications/{instance.match.id}"

        mailjet.send_mail_alternative_date_proposal_for_job_interview(
            email=applier.user.email,
            username=applier.user.get_full_name(),
            company=company.name,
            company_adress=company.address,
            proposed_dates=proposed_dates,
            reply_date=reply_date,
            company_chat_link=URL,
        )

    if instance.status == MatchStatus.ALTERNETE_DATE_FROM_APPLIER:
        match = instance.match
        url = f"{settings.FRONTEND_URL}/job-profile/{match.job.id}/{match.applier.id}"

        mailjet.send_mail_applier_alternative(
            email=match.company.user.email,
            c_contact_email=match.company.contact_email,
            username=match.company.user.get_full_name(),
            applicant_username=match.applier.user.get_full_name(),
            applicant_match_link=url,
        )
        pass

    if instance.status == MatchStatus.INTERVIEW_AGREED:
        accepted_date_for_job_interview = f"{format_date(instance.date, format='E d.MM.y', locale='de_DE')}, {instance.start_time} - {instance.end_time} Uhr"
        address = f"{instance.interview_schedule.street}, {instance.interview_schedule.city}, {instance.interview_schedule.postcode}"
        company = instance.match.company
        applier = instance.match.applier

        url = f"{settings.FRONTEND_URL}/job-profile/{instance.match.job.id}/{instance.match.applier.id}"

        mailjet.send_mail_date_confirm_for_job_interview(
            email=company.user.email,
            c_contact_email=company.contact_email,
            username=company.user.get_full_name(),
            job_position=instance.match.job.title,
            accepted_date_for_job_interview=accepted_date_for_job_interview,
            applicantusername=instance.match.applier.user.get_full_name(),
            applicant_match_link=url,
            interview_address=address,
            applier_phone_number=instance.match.applier.phone_number,
        )

        mailjet.send_mail_date_confirm_for_job_interview_to_applier(
            email=applier.user.email,
            username=applier.user.get_full_name(),
            company_name=company.name,
            accepted_date_for_job_interview=accepted_date_for_job_interview,
            interview_address=address,
            job_title=instance.match.job.title,
            company_user=company.user.get_full_name(),
            applier_phone_number=instance.match.company.phone_number,
            applicant_match_link="",
        )

    if instance.status == MatchStatus.COMPANY_AGREED:

        applier_url = f"{settings.FRONTEND_URL}/applications/{instance.match.id}"

        match = instance.match
        applier = instance.match.applier
        date = ""
        try:
            interview_agreed = History.objects.get(
                match=instance.match, status=MatchStatus.INTERVIEW_AGREED
            )
            date = format_date(interview_agreed.date, format="E d.MM.y", locale="de_DE")
        except Exception:
            pass
        company = instance.match.company
        mailjet.send_mail_job_offer_to_applicant(
            email=applier.user.email,
            username=applier.user.get_full_name(),
            job_position=match.job.title,
            company=company.name,
            date=date,
            link_to_match=applier_url,
        )

    if instance.status == MatchStatus.APPLICANT_AGREED:

        url = f"{settings.FRONTEND_URL}/job-profile/{instance.match.job.id}/{instance.match.applier.id}"
        mailjet.send_mail_job_accepted_by_applicant(
            email=instance.match.company.user.email,
            c_contact_email=instance.match.company.contact_email,
            username=instance.match.company.user.get_full_name(),
            job_position=instance.match.job.title,
            applicantusername=instance.match.applier.user.get_full_name(),
            url=url,
        )

    if instance.status == MatchStatus.COMPANY_CANCEL:
        applier = instance.match.applier
        company = instance.match.company
        mailjet.send_email_company_canceled(
            email=applier.user.email,
            username=applier.user.get_full_name(),
            company=company.name,
            url=settings.FRONTEND_DASHBOARD_URL,
        )

    if instance.status == MatchStatus.APPLICANT_CANCEL:
        applier = instance.match.applier
        company = instance.match.company
        if instance.old_status != MatchStatus.MATCHED:
            mailjet.send_email_applicant_canceled(
                email=company.user.email,
                c_contact_email=company.contact_email,
                company_username=company.user.get_full_name(),
                applicant_username=applier.user.get_full_name(),
            )
        elif instance.old_status == MatchStatus.MATCHED:
            match = instance.match
            match.is_active = False
            match.save()

    if instance.status == MatchStatus.MATCH_REFUSED:
        match = instance.match
        match.is_active = False
        match.save()


def create_notification(match, user, status, interview_date=None):
    Notification.objects.create(
        match=match, for_user=user, status=status, interview_date=interview_date
    )

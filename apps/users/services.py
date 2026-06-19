from django.contrib.sessions.models import Session
from django.core.mail import send_mail
from django.utils import timezone

from apps.common.logging_utils import get_client_ip, log_action
from apps.users.models import EmailVerificationCode, User, WorkSession


def invalidate_user_sessions(user):
    user_id = str(user.pk)
    for session in Session.objects.all():
        data = session.get_decoded()
        if data.get('_auth_user_id') == user_id:
            session.delete()


def start_work_session(user, ip_address=None):
    WorkSession.objects.filter(user=user, is_active=True).update(
        is_active=False,
        logout_at=timezone.now(),
    )
    session = WorkSession.objects.create(user=user, ip_address=ip_address, is_active=True)
    user.update_activity()
    return session


def close_active_sessions(user, invalidate_sessions=False):
    now = timezone.now()
    WorkSession.objects.filter(user=user, is_active=True).update(
        is_active=False,
        logout_at=now,
    )
    if invalidate_sessions:
        invalidate_user_sessions(user)


def send_verification_email(user, code):
    from django.conf import settings

    subject = 'Plant CRM — tasdiqlash kodi'
    message = (
        f'Salom, {user.full_name}!\n\n'
        f'Sizning tasdiqlash kodingiz: {code}\n'
        f'Kod 5 daqiqa amal qiladi.\n\n'
        f'Plant CRM'
    )
    send_mail(
        subject,
        message,
        settings.DEFAULT_FROM_EMAIL,
        [user.email],
        fail_silently=False,
    )


def authenticate_credentials(email, password):
    try:
        user = User.objects.get(email=email.lower())
    except User.DoesNotExist:
        return None

    if not user.check_password(password):
        return None
    if not user.is_active or user.is_archived or user.is_blocked:
        return None
    return user


def send_employee_verification_code(user, request):
    EmailVerificationCode.objects.filter(user=user, is_used=False).update(is_used=True)
    verification = EmailVerificationCode.create_for_user(user)
    send_verification_email(user, verification.code)
    log_action(
        request=request,
        action='auth.verification_sent',
        model_name='users.User',
        object_id=user.pk,
    )
    return verification


def verify_employee_code(user, code, request):
    verification = (
        EmailVerificationCode.objects
        .filter(user=user, code=code, is_used=False)
        .order_by('-created_at')
        .first()
    )
    if not verification or not verification.is_valid():
        return False

    verification.is_used = True
    verification.save(update_fields=['is_used'])
    start_work_session(user, get_client_ip(request))
    log_action(
        request=request,
        action='auth.login',
        model_name='users.User',
        object_id=user.pk,
        new_value={'user_type': 'employee', 'verified': True},
    )
    return True


def complete_admin_login(user, request):
    start_work_session(user, get_client_ip(request))
    log_action(
        request=request,
        action='auth.login',
        model_name='users.User',
        object_id=user.pk,
        new_value={'user_type': 'admin'},
    )


def record_client_view(user, client_id, request=None):
    """Call from clients module; logs client.view for anomaly detection."""
    log_action(
        user=user,
        request=request,
        action='client.view',
        model_name='clients.Client',
        object_id=client_id,
    )
    from apps.users.tasks import check_user_anomaly

    check_user_anomaly.delay(user.id)


def notify_admin_user_blocked(user):
    from django.conf import settings

    subject = f'[Plant CRM] Foydalanuvchi bloklandi: {user.email}'
    message = (
        f'Foydalanuvchi avtomatik bloklandi.\n\n'
        f'Email: {user.email}\n'
        f'Ism: {user.full_name}\n'
        f'Sabab: {user.blocked_reason}\n'
        f'Vaqt: {user.blocked_at}\n'
    )
    send_mail(
        subject,
        message,
        settings.DEFAULT_FROM_EMAIL,
        [settings.ADMIN_NOTIFICATION_EMAIL],
        fail_silently=False,
    )

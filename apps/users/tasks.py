from datetime import timedelta

from celery import shared_task
from django.conf import settings
from django.db.models import Count
from django.utils import timezone

from apps.common.models import ActionLog
from apps.users.models import User
from apps.users.services import close_active_sessions, notify_admin_user_blocked


@shared_task
def close_inactive_sessions():
    threshold = timezone.now() - timedelta(hours=settings.INACTIVITY_LOGOUT_HOURS)
    inactive_users = User.objects.filter(
        last_activity_at__lt=threshold,
        work_sessions__is_active=True,
    ).distinct()

    closed_count = 0
    for user in inactive_users:
        close_active_sessions(user, invalidate_sessions=True)
        closed_count += 1

    return f'Closed sessions for {closed_count} users'


@shared_task
def check_anomaly_client_views():
    window = timezone.now() - timedelta(minutes=settings.ANOMALY_WINDOW_MINUTES)
    threshold = settings.ANOMALY_CLIENT_VIEWS_THRESHOLD

    suspicious = (
        ActionLog.objects
        .filter(action='client.view', created_at__gte=window)
        .values('user_id')
        .annotate(view_count=Count('id'))
        .filter(view_count__gt=threshold, user_id__isnull=False)
    )

    blocked_count = 0
    for row in suspicious:
        user = User.objects.filter(
            pk=row['user_id'],
            user_type=User.UserType.EMPLOYEE,
            is_blocked=False,
            is_active=True,
        ).first()
        if user:
            _block_user_for_anomaly(user, row['view_count'])
            blocked_count += 1

    return f'Blocked {blocked_count} users for anomaly'


@shared_task
def check_user_anomaly(user_id):
    user = User.objects.filter(pk=user_id).first()
    if not user or user.is_blocked or user.user_type != User.UserType.EMPLOYEE:
        return

    window = timezone.now() - timedelta(minutes=settings.ANOMALY_WINDOW_MINUTES)
    view_count = ActionLog.objects.filter(
        user=user,
        action='client.view',
        created_at__gte=window,
    ).count()

    if view_count > settings.ANOMALY_CLIENT_VIEWS_THRESHOLD:
        _block_user_for_anomaly(user, view_count)


def _block_user_for_anomaly(user, view_count):
    reason = (
        f'Anomaliya: {view_count} ta mijoz kartochkasi '
        f'{settings.ANOMALY_WINDOW_MINUTES} daqiqa ichida ochilgan'
    )
    user.block(reason)
    close_active_sessions(user, invalidate_sessions=True)
    notify_admin_user_blocked(user)

from django.utils import timezone

from apps.users.models import User


class ActivityTrackingMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        self._update_activity(request)
        return response

    def _update_activity(self, request):
        user = getattr(request, 'user', None)
        if not user or not user.is_authenticated:
            return
        if not isinstance(user, User):
            return
        now = timezone.now()
        if user.last_activity_at and (now - user.last_activity_at).total_seconds() < 30:
            return
        User.objects.filter(pk=user.pk).update(last_activity_at=now)

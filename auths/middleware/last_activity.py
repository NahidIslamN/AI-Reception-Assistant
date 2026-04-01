from auths.tasks import update_last_activity
from django.utils import timezone
from datetime import timedelta

class UpdateLastActivityMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)

        if request.user.is_authenticated:
            last_activity = request.user.last_activity

            if not last_activity or timezone.now() - last_activity > timedelta(minutes=5):
                update_last_activity.delay(user_id=request.user.id)
        return response

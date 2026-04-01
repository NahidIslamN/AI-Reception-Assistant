from django.utils import timezone
from datetime import timedelta
from .tasks import update_messages_delivered
from .utils import should_enqueue_task

class UpdateLastActivityMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)

        if request.user.is_authenticated and request.path.startswith('/api/v1/chats/'):
            now = timezone.now()

            # last_activity throttle
            if not request.user.last_activity or (now - request.user.last_activity) > timedelta(minutes=3):
                request.user.last_activity = now
                request.user.save(update_fields=['last_activity'])

            # celery throttle by redis
            if should_enqueue_task(request.user.id):
                update_messages_delivered.delay(request.user.id)

        return response

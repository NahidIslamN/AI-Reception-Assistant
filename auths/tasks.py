from celery import shared_task
from django.core.mail import send_mail

from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from django.utils import timezone
from datetime import timedelta
from django.contrib.auth import get_user_model


@shared_task(bind=True, autoretry_for=(Exception,), retry_backoff=True, max_retries=2)
def send_email_to(self, email, text, subject):
    send_mail(subject, text, 'from@example.com', [email])
    return "Email sent successfully."


@shared_task
def update_last_activity(user_id):
    User = get_user_model()
    updated = User.objects.filter(id=user_id).update(
        last_activity=timezone.now()
    )
    
    if updated:
        return "last_activity timestamp updated."
    return "User not found."

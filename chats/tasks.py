
from celery import shared_task

from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from .models import Chat, NoteModel





@shared_task
def sent_note_to_user(user_id: int, title: str, content: str, note_type: str):
    User = get_user_model()
    try:
        user = User.objects.get(id=user_id)
        NoteModel.objects.create(
            user=user,
            title=title,
            content=content,
            note_type=note_type
        )
    except User.DoesNotExist:
        return "User not found"

    channel_layer = get_channel_layer()
    message = {
        "title": title,
        "content": content,
        "note_type":note_type
    }

    group_name = f"notification_{user_id}"
    async_to_sync(channel_layer.group_send)(
        group_name,
        {
            "type": note_type,
            "message": message,
            "saved": True
        }
    )

    return "success fully sent note to user"




# @shared_task
# def sent_message_to_chat(chat_id: int, json_message: dict):
#     channel_layer = get_channel_layer()
#     try:
#         users = Chat.objects.get(id=chat_id).participants.all()
#     except Chat.DoesNotExist:
    
#         return "chat does not exist"
    
#     json_message["chat_id"] = chat_id

#     for user in users:
#         group_name = f"chats_{user.id}"
#         async_to_sync(channel_layer.group_send)(
#             group_name,
#             {
#                 "type": "chat_message",
#                 "message": json_message,
#             }
#         )
#     return "success fully sent message to chat participants"



@shared_task
def sent_message_to_chat(chat_id: int, json_message: dict):
    channel_layer = get_channel_layer()
    try:
        users = Chat.objects.get(id=chat_id).participants.all()
    except Chat.DoesNotExist:
        return "chat does not exist"
    
    json_message["chat_id"] = chat_id

    for user in users:
        group_name = f"chats_{user.id}"
        async_to_sync(channel_layer.group_send)(
            group_name,
            {
                "type": "chat_message",
                "message": json_message,
            }
        )
    return "success fully sent message to chat participants"





# chat/tasks.py

from celery import shared_task
from django.utils import timezone
from datetime import timedelta
from .models import Chat, Message
from django.contrib.auth import get_user_model

@shared_task
def update_messages_delivered(user_id):
    User = get_user_model()

    try:
        user = User.objects.get(id=user_id)
    except User.DoesNotExist:
        return

    recent_time = timezone.now() - timedelta(hours=24)

    chats = Chat.objects.filter(participants=user)

    Message.objects.filter(
        chat__in=chats,
        status='sent',
        created_at__gte=recent_time
    ).exclude(sender=user).update(status='delivered')

    return "All messages received successfully and last_activity timestamp updated."

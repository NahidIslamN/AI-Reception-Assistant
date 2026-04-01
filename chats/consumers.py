import json
import base64
from django.core.files.base import ContentFile
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.generic.websocket import AsyncJsonWebsocketConsumer
from channels.db import database_sync_to_async
from .models import NoteModel, Chat, Message, MessageFiles, MessageReaction
import asyncio
from channels.consumer import AsyncConsumer
from channels.exceptions import StopConsumer






# sent notification to user
class NotificationConsumer(AsyncConsumer):
    async def websocket_connect(self, event):
        user = self.scope.get("user")

        if user.is_anonymous:
            await self.close()   # unauthorized হলে বন্ধ
            return
        else:
            self.room_group_name = f"notification_{user.id}"
            await self.channel_layer.group_add(
                self.room_group_name,
                self.channel_name
            )
            await self.send({
                "type": "websocket.accept"
            })

    async def websocket_receive(self, event):

        text_data = event['text']
        try:
            message = json.loads(text_data)
        except json.JSONDecodeError:
            message = {"text": text_data}

        await self.channel_layer.group_send(
            self.room_group_name,
            {
                "type": "sent.note",
                "message": message,
            }
        )

    async def sent_note(self, event):
        data = event['message']
        user = self.scope.get("user")
      
        if not event.get('saved', False):
            await self.save_notification(user=user, data=data)

        await self.send({
            "type": "websocket.send",
            "text": json.dumps(event['message']),
        })

    async def success(self, event):
        await self.sent_note(event)

    async def warning(self, event):
        await self.sent_note(event)

    async def normal(self, event):
        await self.sent_note(event)

    @database_sync_to_async
    def save_notification(self, user, data):
        from .models import NoteModel
        
        return NoteModel.objects.create(
            user=user,
            title=data.get('title'),
            content=data.get('content'),
            note_type = data.get('note_type')
        )

    async def websocket_disconnect(self, event):
        await self.channel_layer.group_discard(
            self.room_group_name,
            self.channel_name
        )
        raise StopConsumer()
    







class UpdateChatConsumerMessageGet(AsyncWebsocketConsumer):
    async def connect(self):
        self.user = self.scope.get("user")
        if not self.user or getattr(self.user, "is_anonymous", True):
            await self.close(code=4001)
            return
        # keep personal group for pushing messages to this user's sockets
        self.user_group = f"chats_{self.user.id}"
        await self.channel_layer.group_add(self.user_group, self.channel_name)
        await self.accept()

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(self.user_group, self.channel_name)

    async def receive(self, text_data):
        try:
            data = json.loads(text_data)
        except Exception:
            return

        message_text = data.get("message", "")
        chat_id = data.get("chat_id")
        files_data = data.get("files", [])  # list of {title, file_base64}

        if not chat_id or (not message_text and not files_data):
            return

        # save message and files
        try:
            message_obj = await self.save_message_to_database(message_text, files_data, chat_id)
        except Exception:
            return

        files_urls = await self.get_message_files(message_obj)

        username = getattr(self.user, "username", None) or getattr(self.user, "email", "Anonymous")
        profile_image = None
        try:
            if getattr(self.user, "image", None):
                profile_image = self.user.image.url
        except Exception:
            profile_image = None

        payload = {
            "id": message_obj.id,
            "text": message_obj.text,
            "status": getattr(message_obj, "status", None),
            "chat_id": chat_id,
            "sender": {"id": self.user.id, "username": username, "profile_image": profile_image},
            "last_activity": str(getattr(self.user, "last_activity", None)),
            "files": files_urls,
            "created_at": message_obj.created_at.isoformat() if message_obj.created_at else None
        }

        # broadcast to each participant's personal group (non-blocking)
        participant_ids = await self.get_chat_participants(chat_id)
        for pid in participant_ids:
            await self.channel_layer.group_send(
                f"chats_{pid}",
                {"type": "chat_message", "message": payload}
            )

    async def chat_message(self, event):
        msg = event.get("message", {})
        await self.send(text_data=json.dumps({
            "success": True,
            "message": msg,
            "chat_id": msg.get("chat_id"),
            "username": (msg.get("sender") or {}).get("username"),
            "image": (msg.get("sender") or {}).get("profile_image"),
            "last_activity": msg.get("last_activity"),
            "files": msg.get("files", [])
        }))

    @database_sync_to_async
    def get_message_files(self, message_obj):
        return [f.file.url for f in message_obj.files.all()]

    @database_sync_to_async
    def save_message_to_database(self, message_text, files, chat_id):
        chat = Chat.objects.get(id=chat_id)
        msg_obj = Message.objects.create(chat=chat, sender=self.user, text=message_text or None)
        for f in files:
            title = f.get("title", "")
            file_base64 = f.get("file_base64")
            if file_base64:
                format_part, imgstr = file_base64.split(';base64,')
                ext = format_part.split('/')[-1]
                data = ContentFile(base64.b64decode(imgstr), name=f"{title}.{ext}")
                file_obj = MessageFiles.objects.create(title=title, file=data)
                msg_obj.files.add(file_obj)
        chat.save()
        return msg_obj

    @database_sync_to_async
    def get_chat_participants(self, chat_id):
        chat = Chat.objects.get(id=chat_id)
        return list(chat.participants.values_list("id", flat=True))


# class UpdateChatConsumerMessageGet(AsyncWebsocketConsumer):
#     async def connect(self):
#         self.user = self.scope.get("user")
#         if self.user.is_anonymous:
#             await self.close(code=4001)   # No ERROR
#             return
#         self.room_group_name = f"chats_{self.user.id}"
      
#         await self.channel_layer.group_add(self.room_group_name, self.channel_name)
#         await self.accept()

#     async def receive(self, text_data):
#         text_data_json = json.loads(text_data)
#         message = text_data_json.get("message")

#         await self.channel_layer.group_send(
#             self.room_group_name,
#             {
#                 "type": "chat_message",
#                 "message": message
#             }
#         )


#     async def chat_message(self, event):
#         message = event["message"]      
#         await self.send(text_data=json.dumps(message))

    
#     async def receive(self, text_data):
#         data = json.loads(text_data)
#         message_text = data.get("message", "")
#         chat_id = data.get("chat_id")
#         files_data = data.get("files", []) 
        
#         message_obj = await self.save_message_to_database(message_text, files_data, chat_id)
#         files_urls = await self.get_message_files(message_obj)

#         # Broadcast to users        
#         await self.channel_layer.group_send(
#             self.room_group_name,
#             {
#                 "type": "chat_message",
#                 "message": message_text,
#                 "chat_id": chat_id,
#                 "username": getattr(self.user, "username", "Anonymous"),
#                 "profile_image": self.user.image.url if self.user and self.user.image else None,
#                 "last_activity": str(self.user.last_activity) if self.user.last_activity else None,
#                 "files": files_urls
#             }
#         )
        
#     async def chat_message(self, event):
#         await self.send(text_data=json.dumps({
#             "message": event["message"],
#             "username": event["username"],
#             "chat_id": event['chat_id'],
#             "image": event["profile_image"],
#             "last_activity":event['last_activity'],
#             "files": event.get("files", [])
#         }))

    
#     # sent file to users
#     @database_sync_to_async
#     def get_message_files(self, message_obj):
#         return [f.file.url for f in message_obj.files.all()]

#     @database_sync_to_async
#     def save_message_to_database(self, message_text, files, chat_id):
#         from.models import Chat, Message, MessageFiles
#         chat = Chat.objects.get(id=chat_id)
#         msg_obj = Message.objects.create(chat=chat, sender=self.user, text=message_text)

#         for f in files:
#             title = f.get("title", "")
#             file_base64 = f.get("file_base64")
#             if file_base64:
#                 format, imgstr = file_base64.split(';base64,')
#                 ext = format.split('/')[-1]  # e.g., png, jpg
#                 data = ContentFile(base64.b64decode(imgstr), name=f"{title}.{ext}")
#                 file_obj = MessageFiles.objects.create(title=title, file=data)
#                 msg_obj.files.add(file_obj)
#         chat.save()
#         return msg_obj






# class MessageSeenStatusUpdate(AsyncWebsocketConsumer):
#     async def connect(self):
#         self.user = self.scope.get("user")
#         self.room_name = self.scope['url_route']['kwargs']['chat_id']
#         self.room_group_name = f"message_update_seen_{self.room_name}"

#         if await self.check_able_connect_or_not():
#             await self.channel_layer.group_add(self.room_group_name, self.channel_name)
#             await self.accept()

#             # Start the broadcast loop as a background task
#             self.loop_task = asyncio.create_task(self.broadcast_loop())
#         else:
#             await self.close()

#     async def disconnect(self, close_code):
#         # Stop the background loop
#         if hasattr(self, "loop_task"):
#             self.loop_task.cancel()
#             try:
#                 await self.loop_task
#             except asyncio.CancelledError:
#                 pass

#         await self.channel_layer.group_discard(self.room_group_name, self.channel_name)

#     async def receive(self, text_data=None, bytes_data=None):
#         # Handle messages from client (optional)
#         if text_data:
#             data = json.loads(text_data)
#             print("Received from client:", data)

#     async def broadcast_loop(self):

#         try:
#             while True:
#                 await self.chat_object_message_object_update()
#                 message_text = "successfully done"
#                 await self.channel_layer.group_send(
#                     self.room_group_name,
#                     {
#                         "type": "update_message",
#                         "message": message_text
#                     }
#                 )
#                 await asyncio.sleep(1)  # wait 5 seconds before sending next
#         except asyncio.CancelledError:
#             # Loop stops when disconnect is called
#             print(f"Broadcast loop stopped for user {self.user.username}")

#     async def update_message(self, event):
#         # await self.chat_object_message_object_update()
#         # Send the message to WebSocket client
#         await self.send(text_data=json.dumps({
#             "message": event["message"]
#         }))

#     @database_sync_to_async
#     def check_able_connect_or_not(self):
#         chat = Chat.objects.get(id=self.room_name)
#         return self.user in chat.participants.all()

#     @database_sync_to_async
#     def chat_object_message_object_update(self):
#         from .models import Chat, Message
#         chat = Chat.objects.get(id=self.room_name)
#         mgs = Message.objects.filter(chat=chat, seen_users = self.user).first()
#         if mgs:
#             mgs.seen_users.remove(self.user)
#             mgs.save()
#         letest_message = Message.objects.filter(chat=chat).order_by("-created_at").first()
#         letest_message.seen_users.add(self.user)
#         letest_message.save()

#         return self.user 







# class Sent_Reaction_ON_Message(AsyncWebsocketConsumer):
#     async def connect(self):
#         self.user = self.scope.get("user")
#         self.room_name = self.scope['url_route']['kwargs']['message_id']
#         self.room_group_name = f"react_to_{self.room_name}"

#         if await self.check_able_connect_or_not():
#             await self.channel_layer.group_add(self.room_group_name, self.channel_name)
#             await self.accept()
#         else:
#             await self.close()

#     async def disconnect(self, close_code):
#         await self.channel_layer.group_discard(self.room_group_name, self.channel_name)

#     async def receive(self, text_data):
#         data = json.loads(text_data)
#         emuji = data.get("message", "")
#         print(emuji)

#         await self.save_reaction_into_message(emuji)


#         # Broadcast to group
#         await self.channel_layer.group_send(
#             self.room_group_name,
#             {
#                 "type": "emoji_sender",
#                 "message": emuji,
#                 "username": getattr(self.user, "username", None),
#                 "profile_image": getattr(self.user, "profile_image", None).url if getattr(self.user, "profile_image", None) else None,             
#             }
#         )

#     async def emoji_sender(self, event):
#         await self.send(text_data=json.dumps({
#             "emuji": event["message"],
#             "username": event["username"],
#             "profile_image": event["profile_image"], 
#             "message_id":self.room_name
            
#         }))

#     # ---------------- DB helpers ----------------

#     @database_sync_to_async
#     def check_able_connect_or_not(self):
#         from .models import Message
#         message = Message.objects.get(id=self.room_name)
#         return self.user in message.chat.participants.all()

#     @database_sync_to_async
#     def save_reaction_into_message(self, emuji):
#         try:
#             from .models import Message, MessageReaction

#             message = Message.objects.get(id = self.room_name)
            
#             if message.reactions.filter(user=self.user).exists():
#                 my_reaction = message.reactions.filter(user=self.user).first()
#                 message.reactions.remove(my_reaction)
#                 message.save()

            

#             if MessageReaction.objects.filter(user = self.user, emoji = emuji).exists():
#                 new_reaction = MessageReaction.objects.filter(user = self.user, emoji = emuji).first()
#             else:
#                 new_reaction = MessageReaction.objects.create(
#                     user=self.user,
#                     emoji = emuji
#                 )

            
#             message.reactions.add(new_reaction)
#             message.save()
#             return emuji
#         except:
#             return "message not found"



# class Location_Change_Websocket(AsyncConsumer):
#     async def websocket_connect(self,event):
#         user = self.scope.get("user")
#         if user.is_anonymous:
#             await self.send(
#                 {
#                     "type":"websocket.discard",
#                     "text":"unauthorized user"
#                 }
#             )
#             return
        
#         else:
#             self.room_group_name = f"locationchange_{user.id}"
#             await self.channel_layer.group_add(
#                 self.room_group_name,
#                 self.channel_name
#             )
        
#             await self.send(
#                 {
#                     "type":"websocket.accept",
#                     "text":"connected"
#                 }
#             )
        
#     async def websocket_receive(self,event):
#         message = event['text']  

#         # Send message to the group
#         await self.channel_layer.group_send(
#             self.room_group_name,
#             {
#                 "type": "location.change",
#                 "message": message,
#             }
#         )
#     async def location_change(self, event):
#         message = event['message']
#         data = json.loads(message)
#         try:
#             current_user = self.scope.get("user")
#             longitude = data.get("longitude")
#             latitude = data.get("latitude")
#             await self.update_user_location(user=current_user,latitude =latitude,  longitude=longitude)
#         except:
#             pass

#         await self.send(
#             {
#                 "type":"websocket.send",
#                 "text": "change location successfully!"
#             }
#         )
    
#     @database_sync_to_async
#     def update_user_location(self, user, latitude, longitude):
#         user.latitude = latitude
#         user.longitude = longitude

#         user.save()
#         return user
#     async def websocket_discard(self,event):
#         await self.channel_layer.group_discard(
#             self.room_group_name,
#             self.channel_name
#         )
#         raise StopConsumer()

#     async def websocket_disconnect(self, event):
#         await self.channel_layer.group_discard(
#             self.room_group_name,
#             self.channel_name
#         )
#         raise StopConsumer()
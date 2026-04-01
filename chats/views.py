from rest_framework.response import Response
from rest_framework import status
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated, IsAdminUser
from .models import *
from .serializers import *
from django.db.models import Q
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from .tasks import sent_message_to_chat
from .tasks import sent_note_to_user
from AI_Strming.pagination import CustomPagination
from rest_framework.throttling import UserRateThrottle, AnonRateThrottle



class Unseen_Notifications_count(APIView):
    permission_classes=[IsAuthenticated]
    throttle_classes = [UserRateThrottle, AnonRateThrottle]
    def get(self, request):
        notifications = NoteModel.objects.filter(user=request.user, is_seen=False).count()       
        return Response({"success":True,"message":"data fatched!","total_unseen_note":notifications}, status=status.HTTP_200_OK)
    

class Notifications(APIView):
    permission_classes=[IsAuthenticated]
    throttle_classes = [UserRateThrottle, AnonRateThrottle]
    pagination_class = CustomPagination
    def get(self, request):
        notifications = NoteModel.objects.filter(user=request.user)
        notifications_update = NoteModel.objects.filter(user=request.user,is_seen=False)
        notifications_update.update(is_seen=True)

        paginator = CustomPagination()
        page = paginator.paginate_queryset(notifications, request)
        serializer = NotificationSerializer(page, many=True, context={'request': request})
        return paginator.get_paginated_response(serializer.data)


    

class Chat_Create_lists(APIView):
    permission_classes = [IsAuthenticated]
    pagination_class = CustomPagination
    throttle_classes = [UserRateThrottle, AnonRateThrottle]

    def get(self, request):
        chats_qs = Chat.objects.filter(participants=request.user).order_by("-updated_at")
        paginator = CustomPagination()
        paginator.page_size = 250
        paginator.page_size_query_param = None
        page = paginator.paginate_queryset(chats_qs, request)
        serializer = ChatListSerializer(page, many=True, context={'request': request})
        return paginator.get_paginated_response(serializer.data)
        
    def post(self, request):
        serializer = Chat_or_Group_CreateSerializer(data=request.data)
        if serializer.is_valid():
            perticipance = request.data.get("user_list")
            try:
                perticipance.append(request.user.id)
            except:
                return Response({"success":False,"message":"validation errors!", "errors":{"message":"invalid python list! plece semt an arry to add user"}}, status=status.HTTP_400_BAD_REQUEST)
            
            if len(perticipance) == 2:
                id = perticipance[0]
                invitee = User.objects.get(id=id)
                if Chat.objects.filter( Q(inviter=request.user, invitee=invitee) | Q(inviter=invitee, invitee=request.user),  chat_type='private').exists():
                    chat = Chat.objects.filter( Q(inviter=request.user, invitee=invitee) | Q(inviter=invitee, invitee=request.user)).first()
                    serializer = ChatListSerializerCreate(chat, context={'request': request})
                    return Response({"success":True,"message":"already exiest chat!", "data":serializer.data}, status=status.HTTP_200_OK)
                else:
                    chats = Chat.objects.create(
                        chat_type = 'private',
                        name = serializer.data.get("group_name"),
                        inviter = request.user,
                        invitee = invitee
                    )
                    try:
                        for us in perticipance:
                            user = User.objects.get(id=us)
                            chats.participants.add(user)
                    except:
                        pass
                    
            else:
                chats = Chat.objects.create(
                    chat_type = 'group',
                    name = serializer.data.get("group_name"),
                    inviter = request.user,
                    is_accepted_invitee=True
                )
                chats.participants.add(request.user)

                try:
                    for us in perticipance:
                        user = User.objects.get(id=us)
                        chats.participants.add(user)
                except:
                    pass
                # Notify all participants about group creation
                for us in perticipance:
                    if us != request.user.id:
                        sent_note_to_user.delay(user_id=us, title=f"Added to Group", content=f"You've been added to group '{chats.name}' by {request.user.first_name} {request.user.last_name}", note_type='normal')
                    pass
            serializer = ChatListSerializerCreate(chats, context={'request': request})
            return Response({"success":True,"message":"successfully created!", "data":serializer.data}, status=status.HTTP_201_CREATED)
        else:
            return Response({
                "success":False, "message":"validation errors!", "errors":serializer.errors
            }, status= status.HTTP_400_BAD_REQUEST)
    



class MessageList_Chats(APIView):
    permission_classes = [IsAuthenticated]
    pagination_class = CustomPagination
    throttle_classes = [UserRateThrottle, AnonRateThrottle]

    def get(self, request, inbox_id):
        user = request.user
        try:
            chat = Chat.objects.get(id=inbox_id)
            # mark delivered/sent -> seen for other users
            Message.objects.filter(
                chat=chat,
                status__in=["delivered", "sent"]
            ).exclude(sender=user).update(status="seen")
        except Chat.DoesNotExist:
            return Response({"success":False,"message":"inbox not found!" }, status=status.HTTP_404_NOT_FOUND)

        if request.user not in chat.participants.all():
            return Response({"success":False,"message":"You are not a member of this chat!"}, status=status.HTTP_400_BAD_REQUEST)

        messages_qs = Message.objects.filter(chat=chat).order_by("-created_at")
        paginator = CustomPagination()
        page = paginator.paginate_queryset(messages_qs, request)
        serializer = Message_List_Serializer(page, many=True, context={'request': request})
        return paginator.get_paginated_response(serializer.data)
    






# class SpamChatList(APIView):
#     permission_classes = [IsAuthenticated]
#     def get(self, request):
#         chats = Chat.objects.filter(
#             Q(participants=request.user) &
#             (Q(is_accepted_invitee=False) & Q(invitee=request.user))
#         )
#         page = request.GET.get('page', 1)
#         page_size = int(request.GET.get('page_size', 100))

#         paginator = Paginator(chats, page_size)

#         try:
#             chats = paginator.page(page)
#         except PageNotAnInteger:
#             chats = paginator.page(1)
#         except EmptyPage:
#             chats = paginator.page(paginator.num_pages)

#         serializers = ChatListSerializer(chats, many=True)
        
#         return Response({"success":True,"message":"data fatched!","data":serializers.data}, status=status.HTTP_200_OK)



# class Accept_Leave_Add_People_Chat(APIView):
#     permission_classes = [IsAuthenticated]
#     def get(self, request,pk):

#         try:
#             chats = Chat.objects.get(id = pk)
#         except:
#             return Response({"success":False,"message":"chat not found!" }, status= status.HTTP_404_NOT_FOUND)
#         if chats.invitee == request.user:
#             chats.is_accepted_invitee = True
#             chats.save()
#             # Notify inviter about chat acceptance
#             sent_note_to_user.delay(user_id=chats.inviter.id, title=f"Chat Request Accepted", content=f"{request.user.first_name} {request.user.last_name} accepted your chat request", note_type='success')
#             return Response({"success":True,"message":"you are now connected!"}, status=status.HTTP_200_OK)
#         else:
#             return Response({"success":False,"message":"you are not able to access this!","error":"invalid message id!",}, status=status.HTTP_400_BAD_REQUEST)
    
#     def post(self, request, pk):
#         try:
#             chats = Chat.objects.get(id = pk)
#         except:
#             return Response({"success":False,"message":"chat not found!" }, status= status.HTTP_404_NOT_FOUND)
#         if request.user in chats.participants.all():
#             chats.participants.remove(request.user)
#             chats.save()
#             return Response({"success":True,"message":"successfully leave form the chat!"}, status=status.HTTP_200_OK)
#         else:
#             return Response({"success":False,"message":"you are no a memeber of the chat!"}, status=status.HTTP_400_BAD_REQUEST)
    
#     def put(self, request, pk):
#         try:
#             chats = Chat.objects.get(id = pk)
#         except:
#             return Response({"success":False,"message":"chat not found!" }, status= status.HTTP_404_NOT_FOUND)
#         if request.user in chats.participants.all():

#             serializer = Add_People_Group_CreateSerializer(data=request.data)
            
#             if serializer.is_valid():
#                 perticipance = serializer.data.get('user_list')
#                 # Notify newly added users
#                 for us in perticipance:
#                     sent_note_to_user.delay(user_id=us, title=f"Added to Group", content=f"You've been added to group '{chats.name}'", note_type='normal')
#                 chats.chat_type = "group"
#                 chats.save()
#                 try:
#                     for us in perticipance:
#                         user = User.objects.get(id=us)
#                         chats.participants.add(user)
#                 except:
#                     pass
#                 chats.save()

#                 return Response({"success":True,"message":"successfully added!","user_list":perticipance}, status= status.HTTP_200_OK)
#             else:
#                 return Response({"success":False,"messsage":"validatiaon errors", "errors":serializer.errors}, status=status.HTTP_400_BAD_REQUEST)
            
#         else:
#             return Response({"success":False,"message":"you are not a member of the chat!"}, status=status.HTTP_400_BAD_REQUEST)


#     def patch(self, request, pk):
#         try:
#             chats = Chat.objects.get(id = pk)
#         except:
#             return Response({"success":False,"message":"chat not found!" }, status= status.HTTP_404_NOT_FOUND)
#         if request.user in chats.participants.all() and chats.inviter == request.user:
#             serializer = Add_People_Group_CreateSerializer(data=request.data)
#             if serializer.is_valid():
#                 perticipance = serializer.data.get('user_list')
#                 # Notify removed users
#                 for us in perticipance:
#                     sent_note_to_user.delay(user_id=us, title=f"Removed from Group", content=f"You've been removed from group '{chats.name}'", note_type='warning')
#                 chats.chat_type = "group"
#                 try:
#                     for us in perticipance:
#                         user = User.objects.get(id=us)
#                         chats.participants.remove(user)
#                 except:
#                     pass

#                 return Response({"success":True,"message":"successfully removed!","user_list":perticipance}, status= status.HTTP_200_OK)
#             else:
#                 return Response({"success":False,"messsage":"validatiaon errors", "errors":serializer.errors}, status=status.HTTP_400_BAD_REQUEST) 
#         else:
#             return Response({"success":False,"message":"you can't remove a user from this chat!"}, status=status.HTTP_400_BAD_REQUEST)
    



class Sent_Message_Chats(APIView):
    permission_classes = [IsAuthenticated]
    throttle_classes = [UserRateThrottle, AnonRateThrottle]
    
    def post(self, request, inbox_id):
        """Send a message with optional files to a chat."""
        try:
            chat = Chat.objects.get(id=inbox_id)
        except Chat.DoesNotExist:
            return Response({
                "success": False,
                "message": "chat not found!"
            }, status=status.HTTP_404_NOT_FOUND)
        
        if request.user not in chat.participants.all():
            return Response({
                "success": False,
                "message": "you are not a member of this chat!"
            }, status=status.HTTP_403_FORBIDDEN)
        


        serializer = Send_Message_Serializer(data=request.data)
        if not serializer.is_valid():
            return Response({
                "success": False,
                "message": "validation errors!",
                "errors": serializer.errors
            }, status=status.HTTP_400_BAD_REQUEST)
        
        message_text = serializer.validated_data.get("message", "").strip()
        files = request.FILES.getlist('files') if 'files' in request.FILES else []
        
        # Validate: message must have text or files
        if not message_text and not files:
            return Response({
                "success": False,
                "message": "message must contain either text or files"
            }, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            # Create message
            message_obj = Message.objects.create(
                chat=chat,
                sender=request.user,
                text=message_text if message_text else None
            )
            
            # Attach files to message
            for file in files:
                try:
                    msg_file = MessageFiles.objects.create(
                        title=file.name,
                        file=file
                    )
                    message_obj.files.add(msg_file)
                except Exception as e:
                    print(f"Error saving file {file.name}: {str(e)}")
                    continue
            
            # Update chat timestamp
            chat.save()
            
            # Serialize and return response
            message_serializer = Message_List_Serializer(message_obj)

            sent_message_to_chat.delay(chat.id, message_serializer.data)
            return Response({
                "success": True,
                "message": "message sent successfully!",
                "data": message_serializer.data
            }, status=status.HTTP_201_CREATED)
        
        except Exception as e:
            return Response({
                "success": False,
                "message": "error sending message",
                "error": str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
        



    

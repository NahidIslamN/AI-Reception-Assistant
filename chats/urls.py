from django.urls import path
from .views import *

urlpatterns = [
    # chat rest
    path('chats/inboxes', Chat_Create_lists.as_view(), name="chat-create-list"), 
    path('chats/messages/<int:inbox_id>', MessageList_Chats.as_view(), name='messages'),
    path("chats/sent-message/<int:inbox_id>", Sent_Message_Chats.as_view(), name="send-message"),   
    # path('spam-chat-list/', SpamChatList.as_view(), name='spam-chat-list'), 
    # path("accept-private-chat/<int:pk>/", Accept_Leave_Add_People_Chat.as_view(),name='accept-leave-add-chat'),  
    

    # notification rest
    path('notes/notifications', Notifications.as_view(), name='notifications'),
    path('notes/unseen-count', Unseen_Notifications_count.as_view(), name='unseen-notifications-count'),

]

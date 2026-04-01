from django.urls import path

from .views import StreamLiveCallPageView, VisitorConversationView, VisitorCreateOrUpdateView

urlpatterns = [
    path("stream/live-call", StreamLiveCallPageView.as_view(), name="stream-live-call"),
    path("stream/visitor", VisitorCreateOrUpdateView.as_view(), name="stream-visitor"),
    path(
        "stream/visitor/<int:visitor_id>/conversation",
        VisitorConversationView.as_view(),
        name="stream-visitor-conversation",
    ),
]

from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView
from django.views.generic import TemplateView

from .models import Visitor
from .serializers import VisitorConversationSerializer, VisitorCreateSerializer


class VisitorCreateOrUpdateView(APIView):
	permission_classes = [AllowAny]

	def post(self, request):
		serializer = VisitorCreateSerializer(data=request.data)
		if not serializer.is_valid():
			return Response(
				{
					"success": False,
					"message": "validation errors",
					"errors": serializer.errors,
				},
				status=status.HTTP_400_BAD_REQUEST,
			)

		data = serializer.validated_data
		visitor, created = Visitor.objects.update_or_create(
			email=data["email"],
			defaults={
				"name": data.get("name"),
				"phone": data.get("phone"),
			},
		)

		return Response(
			{
				"success": True,
				"message": "visitor saved" if created else "visitor updated",
				"data": {
					"id": visitor.id,
					"name": visitor.name,
					"email": visitor.email,
					"phone": visitor.phone,
					"ws_url": f"/ws/ai-striming/voice/?visitor_id={visitor.id}",
				},
			},
			status=status.HTTP_201_CREATED if created else status.HTTP_200_OK,
		)


class VisitorConversationView(APIView):
	permission_classes = [AllowAny]

	def get(self, request, visitor_id):
		try:
			visitor = Visitor.objects.get(id=visitor_id)
		except Visitor.DoesNotExist:
			return Response(
				{"success": False, "message": "visitor not found"},
				status=status.HTTP_404_NOT_FOUND,
			)

		serializer = VisitorConversationSerializer(visitor)
		return Response(
			{"success": True, "message": "data fetched", "data": serializer.data},
			status=status.HTTP_200_OK,
		)


class StreamLiveCallPageView(TemplateView):
	template_name = "ai_striming/stream_live_call.html"

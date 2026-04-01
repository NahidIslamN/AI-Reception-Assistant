from rest_framework import serializers

from .models import Visitor


class VisitorCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Visitor
        fields = ["id", "name", "email", "phone"]


class VisitorConversationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Visitor
        fields = ["id", "name", "email", "phone", "conversission"]

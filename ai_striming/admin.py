from django.contrib import admin
from .models import Visitor


@admin.register(Visitor)
class VisitorAdmin(admin.ModelAdmin):
	list_display = ["id", "name", "email", "phone"]
	search_fields = ["name", "email", "phone"]

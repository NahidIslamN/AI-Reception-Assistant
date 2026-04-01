from django.contrib import admin
from .models import CustomUser, OtpTable
# Register your models here.
admin.site.register(CustomUser)
admin.site.register(OtpTable)

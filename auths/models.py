from django.contrib.auth.models import AbstractUser
from django.db import models
from .managers import CustomUserManager



class CustomUser(AbstractUser):

    username = None
    email = models.EmailField(unique=True)
    full_name = models.CharField(max_length=250, default='')
    status = models.BooleanField(default=False)
    phone = models.CharField(max_length=15, null=True, blank=True)
    is_email_verified = models.BooleanField(default=False)
    is_phone_verified = models.BooleanField(default=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    image = models.ImageField(null=True, blank=True, upload_to="profile")

    last_activity = models.DateTimeField(null=True, blank=True)
    latitude = models.FloatField(null=True, blank=True)
    longitude = models.FloatField(null=True, blank=True)

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = []
    objects = CustomUserManager()

    def __str__(self):
        return self.email




class OtpTable(models.Model):
    user = models.OneToOneField(CustomUser, on_delete= models.CASCADE)
    otp = models.CharField(max_length=8, null=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.user.email
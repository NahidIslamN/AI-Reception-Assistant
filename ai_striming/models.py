from django.db import models

# Create your models here.


class Visitor(models.Model):
    name = models.CharField(max_length=250, null=True, blank=True)
    email = models.EmailField(unique=True)
    phone = models.CharField(max_length=20)
    conversission = models.TextField(blank=True)

    def __str__(self, request):
        return f"{self.name}-+-{self.email}-+-{self.phone}"

  

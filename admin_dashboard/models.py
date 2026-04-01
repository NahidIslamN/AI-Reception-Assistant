from django.db import models

# Create your models here.

class ImagesFiles(models.Model):
    file = models.ImageField(upload_to='images')

class Features(models.Model):
    features_heading = models.CharField(max_length=250)
    discription = models.TextField(blank=True)
    images = models.ManyToManyField(ImagesFiles, blank=True, related_name='features-images')

    def __str__ (self, request):

        return self.features_heading
   


class Projects(models.Model):
    project_name = models.CharField(max_length=250)
    discription = models.TextField()
    value_max = models.DecimalField(max_digits=9, decimal_places=2, default=0.00)
    value_min = models.DecimalField(max_digits=9, decimal_places=2, default=0.00)
    features = models.ManyToManyField(Features, blank=True, related_name='features')
    
    def __str__ (self, request):

        return self.project_name

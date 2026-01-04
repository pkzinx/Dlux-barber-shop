from django.db import models


class Service(models.Model):
    title = models.CharField(max_length=120)
    price = models.DecimalField(max_digits=8, decimal_places=2)
    duration_minutes = models.PositiveIntegerField(default=30)
    active = models.BooleanField(default=True)
    order = models.PositiveIntegerField(default=0)
    description = models.TextField(blank=True, default="")

    class Meta:
        ordering = ['order']

    def __str__(self):
        return self.title

# Create your models here.

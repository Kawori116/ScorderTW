# In app_staff_dashboard/models.py

from django.db import models
from app_owner_admin_panel.models import Restaurant

class Staff(models.Model):
    staff_id = models.AutoField(primary_key=True)
    restaurant = models.ForeignKey(Restaurant, on_delete=models.CASCADE)
    name = models.CharField(max_length=100)
    role = models.CharField(max_length=50)
    username = models.CharField(max_length=50, unique=True)
    password = models.CharField(max_length=128)
    other_details = models.TextField()
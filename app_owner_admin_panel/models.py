# In app_owner_admin_panel/models.py

from django.db import models
from django.contrib.auth.models import User 
from django.core.files.uploadedfile import InMemoryUploadedFile
from django.conf import settings
from PIL import Image
import io
import sys
import os
from datetime import datetime
import glob

class Restaurant(models.Model):
    restaurant_id = models.AutoField(primary_key=True)
    name = models.CharField(max_length=100)
    address = models.CharField(max_length=200)
    contact = models.CharField(max_length=15)
    other_details = models.TextField()
    min_table_number = models.IntegerField(default=1)
    max_table_number = models.IntegerField(default=5)
    dish_time_warning = models.IntegerField(default=30, help_text="Time in minutes after which the order timestamp turns red")

    def is_valid_table_number(self, table_number):
        return self.min_table_number <= table_number <= self.max_table_number
    
    def __str__(self):
        return self.name
    
    def get_dish_time_display(self):
        """Convert total minutes into hours and minutes for display."""
        total_minutes = self.dish_time_warning
        hours = total_minutes // 60
        minutes = total_minutes % 60
        if hours > 0:
            return f"{hours} hour{'s' if hours > 1 else ''} {minutes} minute{'s' if minutes != 1 else ''}"
        return f"{minutes} minute{'s' if minutes != 1 else ''}"

class SystemConfiguration(models.Model):
    system_open = models.BooleanField(default=False, null=True)
    opening_time = models.TimeField(default="10:00:00")
    closing_time = models.TimeField(default="20:00:00")
    automatic_management = models.BooleanField(default=True)

    def __str__(self):
        return f'System Open: {self.system_open}'
    
class ClientProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    restaurant = models.ForeignKey(Restaurant, on_delete=models.CASCADE)

    def __str__(self):
        return self.user.username

class MenuCategory(models.Model):
    category_id = models.AutoField(primary_key=True)
    restaurant = models.ForeignKey(Restaurant, on_delete=models.CASCADE)
    name = models.CharField(max_length=100)
    description = models.TextField(null=True, blank=True)

    def __str__(self):
        return self.name

class CustomizationCategory(models.Model):
    name = models.CharField(max_length=100, null=False, blank=False)
    max_selection = models.PositiveIntegerField(default=1)

    def __str__(self):
        return self.name

class CustomizationOption(models.Model):
    name = models.CharField(max_length=100, null=False, blank=False)
    price = models.DecimalField(max_digits=6, decimal_places=2)
    category = models.ForeignKey(CustomizationCategory, on_delete=models.CASCADE)
    
    def __str__(self):
        return self.name

class Dish(models.Model):
    dish_id = models.AutoField(primary_key=True)
    restaurant = models.ForeignKey(Restaurant, on_delete=models.CASCADE)
    category = models.ForeignKey(MenuCategory, on_delete=models.CASCADE)
    name = models.CharField(max_length=100)
    description = models.TextField(null=True, blank=True)
    price = models.DecimalField(max_digits=8, decimal_places=2)
    customization_available = models.BooleanField(default=False)
    customization_categories = models.ManyToManyField(CustomizationCategory, blank=True)
    customization_options = models.ManyToManyField(CustomizationOption, blank=True)
    is_sold_out = models.BooleanField(default=False)
    image_1x1 = models.ImageField(upload_to='dish_images/1x1/', null=True, blank=True, help_text="1x1 ratio image")
    image_16x9 = models.ImageField(upload_to='dish_images/16x9/', null=True, blank=True, help_text="16x9 ratio image")

    def __str__(self):
        return self.name 
    
    def save(self, *args, **kwargs):
        changed_fields = []
        original = None

        if self.pk:
            original = Dish.objects.get(pk=self.pk)
            for field_name in ['image_1x1', 'image_16x9']:
                original_image = getattr(original, field_name)
                current_image = getattr(self, field_name)
                original_name = original_image.name if original_image else None
                current_name = current_image.name if current_image else None
                if original_name != current_name:
                    changed_fields.append(field_name)
        else:
            for field_name in ['image_1x1', 'image_16x9']:
                if getattr(self, field_name):
                    changed_fields.append(field_name)

        for field_name in changed_fields:
            image_field = getattr(self, field_name)

            if image_field.size > 2 * 1024 * 1024:  # 2MB
                compressed_image = compress_image(image_field)
                setattr(self, field_name, compressed_image)
                image_field = compressed_image

            if self.dish_id:
                ext = os.path.splitext(image_field.name)[1]
                date_str = datetime.now().strftime('%Y%m%d')
                prefix = '1x1' if field_name == 'image_1x1' else '16x9'
                new_name = f'dish_{self.dish_id}_{prefix}_{date_str}{ext}'
                image_field.name = new_name

        super().save(*args, **kwargs)

        # Cleanup old files for changed fields
        for field_name in changed_fields:
            current_image = getattr(self, field_name)
            current_path = current_image.path if current_image else None

            if original:
                original_image = getattr(original, field_name)
                original_path = original_image.path if original_image else None
                if original_path and original_path != current_path and os.path.exists(original_path):
                    os.remove(original_path)

            if self.dish_id and current_path:
                image_dir = os.path.dirname(current_path)
                prefix = '1x1' if field_name == 'image_1x1' else '16x9'
                pattern = os.path.join(image_dir, f'dish_{self.dish_id}_{prefix}_*')
                all_images = glob.glob(pattern)
                for image_path in all_images:
                    if image_path != current_path and os.path.exists(image_path):
                        os.remove(image_path)
        

def compress_image(image):
    """Compress the image to reduce its size."""
    img = Image.open(image)
    output = io.BytesIO()
    img.save(output, format='JPEG', quality=85)
    output.seek(0)
    return InMemoryUploadedFile(
        output, 'ImageField', f"{image.name.split('.')[0]}.jpg", 
        'image/jpeg', sys.getsizeof(output), None
    )
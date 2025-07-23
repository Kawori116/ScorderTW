# In app_customer_interface/models.py
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from django.db import models
from app_owner_admin_panel.models import Restaurant, Dish
from django.db.models import Max

class Order(models.Model):
    ORDER_TYPE_CHOICES = [
        ('eat_in', 'Eat In'),
        ('take_out', 'Take Out'),
        ('delivery', 'Delivery'),
    ]
    
    STATUS_CHOICES = [
        ('placed', 'placed'),
        ('processing', 'processing'),
        ('confirmed', 'confirmed'),
        ('completed', 'completed'),
        ('canceled', 'canceled'),
    ]
    
    order_id = models.AutoField(primary_key=True)
    order_number = models.CharField(max_length=10)
    restaurant = models.ForeignKey(Restaurant, on_delete=models.CASCADE)
    table_number = models.IntegerField(blank=True, null=True)
    status = models.CharField(max_length=50, choices=STATUS_CHOICES, default='placed')
    timestamp = models.DateTimeField()
    total_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    other_details = models.TextField(blank=True, null=True)
    order_type = models.CharField(max_length=20, choices=ORDER_TYPE_CHOICES, default='eat_in')
    phone_number = models.CharField(max_length=15, blank=True, null=True)
    delivery_address = models.TextField(blank=True, null=True)

    def calculate_total_amount(self):
        total_amount = 0
        order_items = self.orderitem_set.all()

        for order_item in order_items:
            total_amount += (order_item.dish.price + order_item.extra_charges) * order_item.quantity

        # print("Total amount: ", total_amount)    
        return total_amount
    
    def get_aggregate_status(self):
        """Optional: Derive overall order status from OrderItems."""
        items = self.orderitem_set.all()
        if not items:
            return 'placed'
        statuses = set(item.status for item in items)
        if len(statuses) == 1:
            return statuses.pop()  # All items have the same status
        if 'canceled' in statuses and len(statuses) == 1:
            return 'canceled'
        if 'completed' in statuses and len(statuses) == 1:
            return 'completed'
        if 'processing' in statuses or 'confirmed' in statuses:
            return 'processing'
        return 'placed'
    

class OrderItem(models.Model):
    STATUS_CHOICES = [
        ('placed', 'placed'),
        ('processing', 'processing'),
        ('confirmed', 'confirmed'),
        ('completed', 'completed'),
        ('canceled', 'canceled'),
    ]
     
    order_item_id = models.AutoField(primary_key=True)
    order = models.ForeignKey(Order, on_delete=models.CASCADE)
    dish = models.ForeignKey(Dish, on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField()
    extra_charges = models.DecimalField(max_digits=10, decimal_places=2, default=0.0)
    customization_details = models.TextField(blank=True, null=True)
    item_total_price = models.DecimalField(max_digits=10, decimal_places=2, default=0.0)
    status = models.CharField(max_length=50, choices=STATUS_CHOICES, default='placed')

    def save(self, *args, **kwargs):
        # Calculate item total price
        self.item_total_price = (self.dish.price + self.extra_charges) * self.quantity
        super().save(*args, **kwargs)

        # Calculate and update the total_amount of the associated Order
        order = self.order
        if order:
            order.total_amount = order.calculate_total_amount()
            order.save()
    

    def __str__(self):
        return f"{self.dish.name} (x{self.quantity}) - {self.status}"
    

@receiver(post_save, sender=OrderItem)
@receiver(post_delete, sender=OrderItem)
def update_order_total_amount(sender, instance, **kwargs):
    # Update the total_amount of the associated Order whenever an OrderItem is saved or deleted
    order = instance.order
    order.total_amount = order.calculate_total_amount()
    order.save()

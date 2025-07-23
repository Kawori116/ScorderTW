# app_customer_interface/admin.py
from django.contrib import admin
from .models import Order, OrderItem

# Create a custom inline model admin for OrderItem
class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0
    # Customize the fields to display in the inline order item
    fields = ('dish', 'dish_price', 'quantity', 'extra_charges', 'item_total_price', 'status', 'customization_details')
    readonly_fields = ('item_total_price', 'dish_price')

    # def item_total_price(self, obj):
    #     return obj.dish.price * obj.quantity

    def dish_price(self, obj):
        return obj.dish.price
    
    # item_total_price.short_description = 'Item Total Price'  
    dish_price.short_description = 'Dish Price'


# Register the Order model with the admin site
@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ('order_id', 'restaurant', 'table_number', 'order_number', 'get_order_type_display',  'status', 'timestamp', 'total_amount')
    list_filter = ('restaurant', 'status', 'order_type', 'timestamp')
    search_fields = ('order_id', 'restaurant__name', 'table_number', 'phone_number', 'delivery_address')
    inlines = [OrderItemInline]

    fieldsets = (
        ('Order Information', {
            'fields': (
                'order_id', 
                'restaurant', 
                'order_number', 
                'status', 
                'timestamp', 
                'total_amount'
            ),
        }),
        ('Order Type & Location', {
            'fields': (
                'order_type',
                'table_number',
            ),
            'description': 'For eat-in orders, specify table number. For take-out/delivery, table number should be empty.'
        }),
        ('Contact Information', {
            'fields': (
                'phone_number',
                'delivery_address',
            ),
            'description': 'Phone number required for take-out and delivery. Address required only for delivery orders.'
        }),
        ('Additional Details', {
            'fields': ('other_details',),
            'classes': ('collapse',), 
        }),
    )
    readonly_fields = ('order_id', 'total_amount')
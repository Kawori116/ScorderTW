# app_staff_dashboard/views.py
from django.contrib.auth import authenticate, login
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, permission_required
from app_owner_admin_panel.models import Dish, SystemConfiguration, ClientProfile, Restaurant
from app_customer_interface.models import Order, OrderItem
from django.http import JsonResponse
import json
from django.views.decorators.csrf import csrf_exempt
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync
import re
from app_owner_admin_panel.decorators import allowed_user
from django.db.models import Sum
from django.utils import timezone

@login_required(login_url='login')
@allowed_user(allowed_roles=['Staff'])
def update_management_mode_view(request):
    

    if request.method == 'POST':
        mode = request.POST.get('management_mode')

        if mode == 'automatic':
            SystemConfiguration.objects.update(automatic_management=True)
            print("Automatic mode enabled")
        elif mode == 'manual':
            SystemConfiguration.objects.update(automatic_management=False)
            SystemConfiguration.objects.update(system_open=True)
            print("Manual mode enabled")


    # Fetch the system_open status
    system_config = SystemConfiguration.objects.first()
    system_open = system_config.system_open
    automatic_management = system_config.automatic_management
    
    print("system open:", system_open,"auto_management:", automatic_management)
    context = {
        'system_open': system_open,
        'automatic_management': automatic_management,
    }
 
    return render(request, 'app_staff_dashboard/system_management.html', context)
    # return redirect('orders_dashboard')


@login_required(login_url='login')
def open_system_view(request):
    if request.method == 'POST':
        print("Open system configuration")
        # Check if the system is already open
        if not SystemConfiguration.objects.get().system_open:
            SystemConfiguration.objects.update(system_open=True)
    return redirect('update_management_mode')
    # return redirect('orders_dashboard')

@login_required(login_url='login')
def close_system_view(request):
    if request.method == 'POST':
        print('Closing system configuration')
        # Check if the system is already closed
        if SystemConfiguration.objects.get().system_open:
            SystemConfiguration.objects.update(system_open=False)
    return redirect('update_management_mode')
    # return redirect('orders_dashboard')

@login_required(login_url='login')
@allowed_user(allowed_roles=['Staff'])
def orders_dashboard_view(request):

    today_start = timezone.now().replace(hour=0, minute=0, second=0, microsecond=0)
    today_end = today_start + timezone.timedelta(days=1) - timezone.timedelta(seconds=1)

    # Filter only today's orders
    incoming_orders = Order.objects.filter(timestamp__gte=today_start, timestamp__lte=today_end)
    
    # incoming_orders = Order.objects.all()
    
    order_dish_items = {}
    
    for order in incoming_orders:
        # Retrieve the related dishes and their quantities for each order
        order.dishes = [{'name': item.dish.name, 'quantity': item.quantity, 'order_item_id': item.order_item_id} for item in order.orderitem_set.all()]

        # See order item id
        for item in order.orderitem_set.all():
            order_dish_items[item.dish_id] = item.order_item_id

    # Fetch the system_open status
    system_config = SystemConfiguration.objects.first()
    system_open = system_config.system_open
    automatic_management = system_config.automatic_management
    # print("system open:", system_open,"auto_management:", automatic_management)
    context = {
        'incoming_orders': incoming_orders,
        'order_dish_items': order_dish_items,
        'system_open': system_open,
        'automatic_management': automatic_management,
    }
    # print(context)
    return render(request, 'app_staff_dashboard/orders_dashboard.html', context)

@login_required(login_url='login')
@allowed_user(allowed_roles=['Staff'])
def order_details_view(request, order_id):
    try:
        order = Order.objects.get(pk=order_id)
        quantities = range(1, 16)  # Range from 1 to 15 for quantity options
        available_dishes = Dish.objects.all()

        return render(request, 'app_staff_dashboard/order_details.html', {
            'order': order,
            'quantities': quantities,
            'available_dishes': available_dishes,
        })

    except Order.DoesNotExist:
        # Handle the case where the order does not exist or is not associated with the correct restaurant
        return render(request, 'app_staff_dashboard/order_not_found.html')

@csrf_exempt  
def update_order_item_view(request):
    if request.method == 'POST' and request.META.get('HTTP_X_REQUESTED_WITH') == 'XMLHttpRequest':
        item_id = request.POST.get('item_id')
        quantity = request.POST.get('quantity')

        if not item_id or not quantity:
            return JsonResponse({'error': 'Missing item_id or quantity.'}, status=400)
        
        try:
            item_id = int(item_id)
            quantity = int(quantity)

            if quantity <= 0:
                return JsonResponse({'error': 'Quantity must be a positive integer.'}, status=400)

           # Retrieve the order item and update its quantity
            order_item = OrderItem.objects.get(pk=item_id)
            order = order_item.order

            # Update the quantity for the order item
            order_item.quantity = quantity

            # Calculate the updated item total price, including extra charges
            order_item.item_total_price = (order_item.dish.price + order_item.extra_charges) * quantity
            order_item.save()

            # Recalculate the total amount for the order
            total_amount = sum(item.item_total_price for item in order.orderitem_set.all())
            order.total_amount = total_amount
            order.save()

            return JsonResponse({
                'quantity': order_item.quantity,
                'total_amount': order.total_amount,
            })

        except (OrderItem.DoesNotExist, ValueError):
            return JsonResponse({'error': 'Invalid request.'}, status=400)

    return JsonResponse({'error': 'Invalid request.'}, status=400)

@csrf_exempt
def delete_order_item_view(request):
    if request.method == 'POST' and request.META.get('HTTP_X_REQUESTED_WITH') == 'XMLHttpRequest':
        # Get the item_id from the AJAX request
        item_id = request.POST.get('item_id')

        if not item_id:
            return JsonResponse({'status': 'error', 'message': 'Invalid request data.'}, status=400)
        
        try:            
            order_item = OrderItem.objects.get(pk=item_id)

            order = order_item.order

            order_item.delete()

            order.total_amount = order.calculate_total_amount()
            order.save()

            # Return a JSON response indicating the success of the deletion
            return JsonResponse({'status': 'success', 'total_amount': order.total_amount})

        except OrderItem.DoesNotExist:
            return JsonResponse({'status': 'error', 'message': 'Invalid order item.'}, status=400)

    else:
        return JsonResponse({'status': 'error', 'message': 'Invalid request.'}, status=400)

@csrf_exempt
def cancel_order_view(request):
    if request.method == 'POST' and request.META.get('HTTP_X_REQUESTED_WITH') == 'XMLHttpRequest':
        order_id = request.POST.get('order_id')

        if order_id is None:
            return JsonResponse({'status': 'error', 'message': 'Missing order ID.'}, status=400)
        
        try:
            order_id = int(order_id)

            # Check if the Order exists and has at least one item
            order = Order.objects.get(pk=order_id)
            if order.orderitem_set.exists():
                order.status = 'canceled'
                order.save()

                return JsonResponse({'status': 'success', 'message': 'Order has been canceled.'})

            else:
                return JsonResponse({'status': 'error', 'message': 'Order cannot be canceled as it has no items.'}, status=400)

        except Order.DoesNotExist:
            return JsonResponse({'status': 'error', 'message': 'Invalid order ID.'}, status=400)

    else:
        return JsonResponse({'status': 'error', 'message': 'Invalid request.'}, status=400)

def confirm_order_view(request):
    if request.method == 'POST' and request.META.get('HTTP_X_REQUESTED_WITH') == 'XMLHttpRequest':
        try:
            
            # Get the order ID from the POST data
            order_id = request.POST.get('order_id')

            if not order_id:
                return JsonResponse({'status': 'error', 'message': 'Invalid order ID.'}, status=400)

            order = Order.objects.get(pk=order_id)

            order.status = 'confirmed'
            order.save()

            order_items = order.orderitem_set.all()
            for item in order_items:
                item.status = 'confirmed'
                item.save()

            formatted_timestamp = order.timestamp.strftime('%Y-%m-%d %H:%M')

            order_details = {
                'order_id': order.order_id,
                'order_number': order.order_number,
                'order_type': order.order_type,
                'table_number': order.table_number,
                'order_status': order.status,
                'order_time': formatted_timestamp,
                'dishes': [
                    {
                        'name': item.dish.name,
                        'quantity': item.quantity,
                        'customization_details': item.customization_details or '',
                        'status': item.status, 
                        'order_item_id': item.order_item_id
                    }
                    for item in order.orderitem_set.all()
                ]
            }

            # Send real-time notification to kitchen staff with order details
            channel_layer = get_channel_layer()

            ping_data = {
                'type': 'ping',
            }

            # Send the ping message to the 'staff_notifications' channel group
            async_to_sync(channel_layer.group_send)('kitchen', ping_data)
            async_to_sync(channel_layer.group_send)('kitchen', {'type': 'order.notification', 'order_details': order_details})

            return JsonResponse({'status': 'success', 'message': 'Order confirmed successfully.'})

        except Order.DoesNotExist:
            return JsonResponse({'status': 'error', 'message': 'Order not found.'}, status=404)
        except Exception as e:
            # Log the error message to help identify the issue
            print("Error confirming order: %s", str(e))
            return JsonResponse({'status': 'error', 'message': 'An error occurred. Please try again later.'}, status=500)
    else:
        return JsonResponse({'status': 'error', 'message': 'Invalid request.'}, status=400)

@login_required(login_url='login')
@allowed_user(allowed_roles=['Staff'])
def kitchen_interface_view(request):
    today_start = timezone.now().replace(hour=0, minute=0, second=0, microsecond=0)
    today_end = today_start + timezone.timedelta(days=1) - timezone.timedelta(seconds=1)

    # Filter only today's orders
    # incoming_orders = Order.objects.filter(timestamp__gte=today_start, timestamp__lte=today_end)

    # Retrieve confirmed orders from the database
    confirmed_orders = Order.objects.filter(
        timestamp__gte=today_start,
        timestamp__lte=today_end,
        orderitem__status__in=['confirmed', 'processing', 'completed']
    ).distinct()

    # Create a dictionary to map dish_id to order_item_id for each confirmed order
    order_dish_items = {}
    
    for order in confirmed_orders:
        order.dishes = [
            {
                'name': item.dish.name,
                'quantity': item.quantity,
                'order_item_id': item.order_item_id,
                'customization_details': item.customization_details or '',
                'status': item.status
            }
            for item in order.orderitem_set.all()
        ]

        # See order item id
        for item in order.orderitem_set.all():
            order_dish_items[item.dish_id] = item.order_item_id

    client_profile = ClientProfile.objects.get(user=request.user)
    restaurant = client_profile.restaurant
    dish_time_warning = restaurant.dish_time_warning

    context = {
        'confirmed_orders': confirmed_orders,
        'order_dish_items': order_dish_items,
        'dish_time_warning': dish_time_warning
    }
    return render(request, 'app_staff_dashboard/kitchen_interface.html', context)

def get_order_status(order):
    items = order.orderitem_set.all()
    statuses = set(item.status for item in items)
    
    if all(status == 'completed' for status in statuses):
        return 'completed'
    elif 'processing' in statuses:
        return 'processing'
    elif all(status == 'confirmed' for status in statuses):
        return 'confirmed'
    elif all(status == 'placed' for status in statuses):
        return 'placed'
    elif all(status == 'canceled' for status in statuses):
        return 'canceled'
    else:
        return 'processing'

def accept_order_view(request):
    if request.method == 'POST' and request.META.get('HTTP_X_REQUESTED_WITH') == 'XMLHttpRequest':
        try:
            order_item_id = request.POST.get('order_item_id')

            if not order_item_id:
                return JsonResponse({'status': 'error', 'message': 'Invalid order item ID.'}, status=400)

            order_item = OrderItem.objects.get(pk=order_item_id)
            order = order_item.order

            order_item.status = 'processing'
            order_item.save()

            # Calculate the new order status
            order_status = get_order_status(order)
            order.status = order_status
            order.save()
            
            # Prepare the order details for the WebSocket message
            accepted_item = {
                'order_id': order.order_id,
                'order_number': order.order_number,
                'order_item_id': order_item.order_item_id,
                'dish_name': order_item.dish.name,
                'quantity': order_item.quantity,
                'table_number': order.table_number,
                'order_type': order.order_type,
                'item_status': order_item.status,
            }

            # Send real-time notification to staff
            channel_layer = get_channel_layer()

            ping_data = {'type': 'ping'}
            async_to_sync(channel_layer.group_send)('kitchen', ping_data)

            async_to_sync(channel_layer.group_send)('kitchen', {
                'type': 'accept_order',
                'accepted_item': accepted_item,
                'order_status': order_status,
            })

            return JsonResponse({'status': 'success', 'message': 'Order accepted successfully.'})
        except OrderItem.DoesNotExist:
            return JsonResponse({'status': 'error', 'message': 'Order item not found.'}, status=404)
        except Order.DoesNotExist:
            return JsonResponse({'status': 'error', 'message': 'Order not found.'}, status=404)
        
def mark_order_completed(request):
    if request.method == 'POST' and request.META.get('HTTP_X_REQUESTED_WITH') == 'XMLHttpRequest':
        try:
            # Get the order ID and dish ID from the POST data
            order_item_id = request.POST.get('order_item_id')

            if not order_item_id:
                return JsonResponse({'status': 'error', 'message': 'Invalid order item ID.'}, status=400)

            order_item = OrderItem.objects.get(pk=order_item_id)
            order = order_item.order

            order_item.status = 'completed'
            order_item.save()

            # Calculate the new order status
            order_status = get_order_status(order)
            order.status = order_status
            order.save()

            # Prepare the order details for the WebSocket message
            completed_dish_data = {
                'order_id': order.order_id,
                'order_number': order.order_number,
                'order_item_id': order_item.order_item_id,
                'dish_name': order_item.dish.name,
                'quantity': order_item.quantity,
                'table_number': order.table_number,
                'order_type': order.order_type,
                'item_status': order_item.status,
            }

            # Send real-time update to the WebSocket consumer
            channel_layer = get_channel_layer()

            ping_data = {'type': 'ping'}
            async_to_sync(channel_layer.group_send)('kitchen', ping_data)

            async_to_sync(channel_layer.group_send)('kitchen', {
                'type': 'dish_completed',
                'completed_dish_data': completed_dish_data,
                'order_status': order_status,
            })

            # Return success JSON response
            return JsonResponse({'status': 'success','completed_dish_data': completed_dish_data, 'message': 'Dish marked as done successfully.'})
        except OrderItem.DoesNotExist:
            return JsonResponse({'status': 'error', 'message': 'Order item not found.'}, status=404)
        except Order.DoesNotExist:
            return JsonResponse({'status': 'error', 'message': 'Order not found.'}, status=404)
        

@login_required(login_url='login')
@allowed_user(allowed_roles=['Staff'])
def dish_management_view(request):
    dishes = Dish.objects.all()
    return render(request, 'app_staff_dashboard/dish_management.html', {'dishes': dishes})

def mark_dish_sold_out(request):
    if request.method == 'POST' and request.META.get('HTTP_X_REQUESTED_WITH') == 'XMLHttpRequest':
        try:
            dish_id = request.POST.get('dish_id')
            is_sold_out = request.POST.get('is_sold_out') == 'true'
           
            dish = Dish.objects.get(pk=dish_id)
            dish.is_sold_out = is_sold_out
            dish.save()
            print(dish, dish.is_sold_out)

            return JsonResponse({'message': 'Status updated successfully'})

        except Dish.DoesNotExist:
            return JsonResponse({'message': 'Dish not found'}, status=404)
        except Exception as e:
            return JsonResponse({'message': 'An error occurred'}, status=500)

    return JsonResponse({'message': 'Invalid request'}, status=400)

@csrf_exempt
def get_total_amount(request):
    if request.method == 'POST' and request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        try:

            start_of_today = timezone.now().replace(hour=0, minute=0, second=0, microsecond=0)
            
            end_of_today = start_of_today + timezone.timedelta(days=1) - timezone.timedelta(seconds=1)


            total_amount_today = Order.objects.filter(timestamp__gte=start_of_today, timestamp__lte=end_of_today).aggregate(total_amount=Sum('total_amount'))['total_amount'] or 0.0

            return JsonResponse({'total_amount': total_amount_today}, status=200)
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=400)
    return JsonResponse({'error': 'Invalid request'}, status=400)

# app_customer_interface/views.py
from django.shortcuts import render, redirect, get_object_or_404
from app_owner_admin_panel.models import Restaurant, MenuCategory, Dish, CustomizationOption, SystemConfiguration, CustomizationCategory
from app_customer_interface.models import Order, OrderItem
from .forms import AddToCartForm, UpdateCartForm
from django.http import JsonResponse, HttpResponseBadRequest, HttpResponseForbidden
from django.middleware.csrf import get_token
from django.db import transaction
from django.core.exceptions import ValidationError
from datetime import datetime
import json
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync
from decimal import Decimal
from django.core.cache import cache
import hashlib, secrets
from django.utils import timezone
import jwt
from datetime import datetime, timedelta
from cryptography.fernet import Fernet
from .decorators import jwt_required 

def handle_qr_scan_view(request):
    encrypted_table_number = getattr(request, 'encrypted_table_number', None) 
    
    if request.session.get('first_time') is None:
        request.session['first_time'] = True

    request.session.pop('auth_token', None)  

    return redirect('welcome_splash',encrypted_table_number=encrypted_table_number)

def welcome_splash_view(request):   
    encrypted_table_number = getattr(request, 'encrypted_table_number', None) 
    context = {
        'encrypted_table_number': encrypted_table_number
    }
    return render(request, 'app_customer_interface/splash.html', context)

def generate_jwt(table_number):
    secret_key = '0iseESfRYHk-4PQuAhXDCp64iUnN-bFIPZlYLDUHJNg='
    
    current_time = timezone.localtime(timezone.now())
    expiration = current_time + timedelta(hours=3)

    print("expiration:", expiration)
    token = jwt.encode({'table_number': table_number, 'exp': expiration}, secret_key, algorithm='HS256')

    return token, expiration

def validate_jwt(token):
    secret_key = '0iseESfRYHk-4PQuAhXDCp64iUnN-bFIPZlYLDUHJNg='

    try:
        payload = jwt.decode(token, secret_key, algorithms=['HS256'])
        return payload  # Token is valid
    except jwt.ExpiredSignatureError:
        return "Expired"  # Token has expired
    except jwt.InvalidTokenError:
        return "Invalid"  # Token is invalid

def index_view(request):
    table_number = getattr(request, 'decrypted_table_number', None)
    encrypted_table_number = getattr(request, 'encrypted_table_number', None) 

    if 'first_time' not in request.session:
        return HttpResponseBadRequest("Invalid Page")
    else:
        first_time = request.session['first_time']

    # Initialize context variables
    context_table_number = None
    order_type = None
    show_order_type_selection = False

    # Handle "out" case
    if table_number == "out":
        order_type = "takeout_delivery"
        context_table_number = 000
    else:
        try:
            table_number_int = int(table_number)
            restaurant = Restaurant.objects.get(restaurant_id=1) 
            
            if not restaurant.is_valid_table_number(table_number_int):
                return HttpResponseBadRequest("Invalid table number")
            
            order_type = "eat_in"
            context_table_number = table_number_int
        except ValueError:
            return HttpResponseBadRequest("Invalid table number")
    
    restaurant = Restaurant.objects.get(restaurant_id=1) 
    menu_categories = MenuCategory.objects.filter(restaurant=restaurant)
    dishes = Dish.objects.filter(restaurant=restaurant)
    system_open = system_config()
        
    context = {
        'restaurant': restaurant,
        'menu_categories': menu_categories,
        'table_number': context_table_number,
        'dishes': dishes,
        'system_open': system_open,
        'encrypted_table_number': encrypted_table_number,
        'order_type': order_type,
        'show_order_type_selection': show_order_type_selection 
    }
    print("conet", context)

    first_time = request.session['first_time'] 

    if first_time == True:
        new_token, token_expiration = generate_jwt(table_number)
        print("expiration:", token_expiration)
        max_age = int((token_expiration - timezone.localtime()).total_seconds())
        response = render(request, 'app_customer_interface/index.html', context)
        response.set_cookie('auth_token', new_token, max_age=max_age, httponly=True, secure=True)
        # response.set_cookie('auth_token', new_token, max_age=max_age, httponly=True, secure=True, path='/', domain='yourdomain.com')

        request.session['first_time'] = False
        
        return response
    elif first_time == False:
        existing_token = request.COOKIES.get('auth_token')
        valid_payload = validate_jwt(existing_token)

        if valid_payload == "Expired":
            request.session.flush()
            return HttpResponseForbidden("Expired page. Please scan QR code again.")
        elif valid_payload == "Invalid":
            request.session.flush()
            return HttpResponseForbidden("Invalid page. Please scan QR code again.")
        else:
            return render(request, 'app_customer_interface/index.html', context)


def system_config():
    # Fetch the system status from the cache
    system_open = cache.get('system_status', False)
    return system_open

@jwt_required
def item_details_view(request, dish_id):
    table_number = getattr(request, 'decrypted_table_number', None)
    # table_number = int(table_number)

    context_table_number = None

    if table_number == "out":
        context_table_number = 000
    else:
        try:
            table_number_int = int(table_number)
            context_table_number = table_number_int
        except ValueError:
            return HttpResponseBadRequest("Invalid table number")

    encrypted_table_number = getattr(request, 'encrypted_table_number', None) 

    dish = get_object_or_404(Dish, pk=dish_id)

    if request.method == 'POST':
        form = AddToCartForm(request.POST)
        if form.is_valid():
            quantity = form.cleaned_data['quantity']
            print("form valid")
        
            # Check if 'cart' exists in the session. If not, initialize an empty cart (a dictionary).
            cart = request.session.get('cart', {})
            
            if dish.customization_available:
                cart_item_identifier = generate_cart_item_identifier(dish_id)
            else:
                cart_item_identifier = f"{dish_id}_"

            if cart_item_identifier in cart:
                # Item with same customization options already exists, update quantity
                cart[cart_item_identifier]['quantity'] += quantity
                item_total_price = dish.price * cart[cart_item_identifier]['quantity']
                cart[cart_item_identifier]['item_total_price'] = str(item_total_price)
            else:
                if dish.customization_available:
                    
                    extra_charges = Decimal('0.00')
                    selected_options = {}

                    for key, value in request.POST.items():
                        if '_option_' in key and value != '0':
                            _, category_id, _, option_id = key.split('_')
                            selected_quantity = int(value)
                            
                            # Assuming you want to collect option names and their quantities
                            if selected_quantity > 0:
                                option = CustomizationOption.objects.get(pk=option_id)
                                category = CustomizationCategory.objects.get(pk=category_id)

                                # Remove prefix from category name
                                category_name = category.name.split(f"{dish.name}_", 1)[1] if f"{dish.name}_" in category.name else category.name

                                # Remove prefix from option name
                                option_name = option.name.split(f"{dish.name}_", 1)[1] if f"{dish.name}_" in option.name else option.name

                                if category_id not in selected_options:
                                    selected_options[category_id] = {
                                        'category_name': category_name,
                                        'options': []
                                    }

                                extra_charges += option.price
                                
                                # Format the option as "option_name x selected_quantity"
                                formatted_option = f"{option_name} x {selected_quantity}"

                                # Append the formatted option
                                selected_options[category_id]['options'].append(formatted_option)
                        
                        elif key.endswith('_options'):
                            # Extract category id from the key
                            category_id = key.split('_')[1]
                            category = get_object_or_404(CustomizationCategory, pk=category_id)

                            # Remove prefix from category name
                            category_name = category.name.split(f"{dish.name}_", 1)[1] if f"{dish.name}_" in category.name else category.name

                            # Correctly retrieve the list of selected option IDs for this category
                            options_list = request.POST.getlist(key)

                            for option_id in options_list:
                                option = CustomizationOption.objects.get(pk=option_id)
                                extra_charges += option.price

                                # Remove prefix from option name
                                option_name = option.name.split(f"{dish.name}_", 1)[1] if f"{dish.name}_" in option.name else option.name

                                if category_id not in selected_options:
                                    selected_options[category_id] = {
                                        'category_name': category_name,
                                        'options': []
                                    }

                                formatted_option = f"{option_name}"
                                
                                # Append the formatted option
                                selected_options[category_id]['options'].append(formatted_option)

                    item_total_price = (dish.price + extra_charges) * quantity
                    cart[cart_item_identifier] = {
                        'dish_id': dish_id,
                        'selected_options': selected_options,
                        'extra_charges': str(extra_charges),
                        'quantity': quantity,
                        'item_total_price': str(item_total_price)
                    }
                else:
                    item_total_price = dish.price * quantity
                    cart[cart_item_identifier] = {
                        'dish_id': dish_id,
                        'quantity': quantity,
                        'item_total_price': str(item_total_price)
                    }
                    
            print("cart", cart)
            request.session['cart'] = cart

            return redirect('cart_page', encrypted_table_number=encrypted_table_number)
    else:
        form = AddToCartForm()
    
    customization_categories = dish.customization_categories.all()
    cleaned_customization_categories = []

    for category in customization_categories:
        if f"{dish.name}_" in category.name:
            category_name = category.name.split(f"{dish.name}_", 1)[1]
        else:
            category_name = category.name
        
        options = category.customizationoption_set.all()
        cleaned_options = []
        for option in options:
            if f"{dish.name}_" in option.name:
                option_name = option.name.split(f"{dish.name}_", 1)[1]
            else:
                option_name = option.name
            cleaned_options.append({
                'id': option.id,
                'name': option_name,
                'price': option.price,
            })

        cleaned_customization_categories.append({
            'id': category.id,
            'name': category_name,
            'max_selection': category.max_selection,
            'options': cleaned_options
        })

    system_open = system_config()

    context = {
        'dish': dish,
        'form': form,
        'table_number':context_table_number,
        'system_open': system_open,
        'encrypted_table_number': encrypted_table_number,
        'customization_categories': cleaned_customization_categories,
    }

    return render(request, 'app_customer_interface/item_details.html', context)

def generate_cart_item_identifier(dish_id):
    dish_id_str = str(dish_id)

    # Convert the dish_id string to bytes
    dish_id_bytes = dish_id_str.encode('utf-8')

    # Create a hash object using hashlib (you can choose a hash algorithm)
    hash_obj = hashlib.sha256()
    hash_obj.update(dish_id_bytes)

    # Get the hexadecimal representation of the hash
    hash_hex = hash_obj.hexdigest()

    random_hex = secrets.token_hex(8)  # 8 bytes, 16 characters

    cart_item_identifier = f"{dish_id_str}_{hash_hex}_{random_hex}"

    return cart_item_identifier

def check_cart_for_sold_out_items_view(request):
    if request.method == 'POST' and request.META.get('HTTP_X_REQUESTED_WITH') == 'XMLHttpRequest':
        cart_items_ids = request.POST.getlist('cart_items_ids[]')

        sold_out_items = []

        # Loop through the cart_item_ids and check each dish's availability
        for cart_item_id in cart_items_ids:
            try:
                cart_item_id = int(cart_item_id)
                # Retrieve the cart item from your database, including the associated Dish
                dish = Dish.objects.get(pk=cart_item_id)

                # Check if the dish is sold out (you can implement your own logic here)
                if dish.is_sold_out:
                    # Add the cart item ID to the list of sold-out items
                    sold_out_items.append(cart_item_id)
            except (Dish.DoesNotExist, ValueError):
                # Handle errors as needed
                pass
        
        if sold_out_items:
            response_data = {
                'has_sold_out_items': True,
                'sold_out_items': sold_out_items,
            }
        else:
            response_data = {
                'has_sold_out_items': False,
            }

        return JsonResponse(response_data)

    # Handle other cases (e.g., non-AJAX requests)
    return JsonResponse({'error': 'Invalid request.'}, status=400)

@jwt_required
def cart_page_view(request):
    # Retrieve the cart items from the session
    cart = request.session.get('cart', {})
    cart_items = []
    total_amount = 0

    table_number = getattr(request, 'decrypted_table_number', None)
    context_table_number = None

    if table_number == "out":
        context_table_number = 000
    else:
        try:
            table_number_int = int(table_number)
            context_table_number = table_number_int
        except ValueError:
            return HttpResponseBadRequest("Invalid table number")
    
    encrypted_table_number = getattr(request, 'encrypted_table_number', None)
    
    for cart_item_identifier, item_data in cart.items():
        dish_id = int(cart_item_identifier.split('_')[0])  # Get the dish_id from the identifier
        dish = Dish.objects.get(pk=dish_id)     
        quantity = item_data['quantity']
    
        # Check if the dish has customization available
        if dish.customization_available:
            selected_options = item_data.get('selected_options', {})
            extra_charges = Decimal(item_data.get('extra_charges', '0.00'))
            item_total_price = (dish.price + extra_charges) * quantity
            # print("Stored selected options:", selected_options, "Extra charges:", extra_charges, "Item total price:", item_total_price)
        else:
            selected_options = {}
            extra_charges = Decimal('0.00')
            item_total_price = Decimal(item_data.get('item_total_price', '0.00'))
            # item_total_price =  dish.price * quantity
            # print("Stored selected options(noncustomizable):", selected_options)
        
        total_amount += item_total_price
        cart_items.append({
            'dish': dish,
            'quantity': quantity,
            'item_total_price': item_total_price,
            'selected_options': selected_options,
            'extra_charges': extra_charges,
            'cart_item_identifier': cart_item_identifier
        })

    # print('cart_items:', cart_items)
    
    # Check if the cart is empty
    is_empty_cart = not bool(cart_items)

    # Generate the quantities for the dropdown options (1 to 15)
    quantities = range(1, 16)
    system_open = system_config()
    context = {
        'cart_items': cart_items,
        'total_amount': total_amount,
        'quantities': quantities,
        'is_empty_cart': is_empty_cart,
        'table_number': context_table_number,
        'system_open': system_open,
        'encrypted_table_number': encrypted_table_number,
    }

    return render(request, 'app_customer_interface/cart_page.html', context)

def clear_cart_view(request):
    encrypted_table_number = getattr(request, 'encrypted_table_number', None) 
    request.session['cart'] = {}  # Clear the cart by setting it to an empty dictionary
    print("Clearing cart:", request.session['cart'])
    return redirect('cart_page', encrypted_table_number=encrypted_table_number)  # Redirect to the cart page after clearing the cart

def update_cart_view(request):
    if request.method == 'POST' and request.META.get('HTTP_X_REQUESTED_WITH') == 'XMLHttpRequest':
        # Ensure the CSRF token is included in the response headers
        response = JsonResponse({'message': 'success'})
        response['X-CSRFToken'] = get_token(request)

        cart_item_identifier = request.POST.get('cart_item_identifier')

         # Create an instance of UpdateCartForm with the POST data
        form = UpdateCartForm(request.POST)

        if form.is_valid():
            new_quantity = form.cleaned_data['quantity']

            cart = request.session.get('cart', {})
            item_data = cart.get(cart_item_identifier, {})

            # Fetch dish details based on dish_id from item_data
            dish_id = item_data.get('dish_id')
            dish = Dish.objects.get(pk=dish_id)

            # Check if the dish has customization available
            if dish.customization_available:
                extra_charges = Decimal(item_data.get('extra_charges', '0.00'))
                # selected_options = item_data.get('selected_options', {})

                # Calculate the updated item total price based on the new quantity
                new_item_total_price = (dish.price + extra_charges) * new_quantity

                # Update the item_data with the new quantity and item_total_price
                item_data['quantity'] = new_quantity
                item_data['item_total_price'] = str(new_item_total_price)

                # Update the cart with the modified item_data
                cart[cart_item_identifier] = item_data
                # print("Item data:", item_data,"cart:",cart)
            else:
                # Calculate the updated item total price for non-customizable dishes
                new_item_total_price = dish.price * new_quantity

                # Update the item_data with the new quantity and item_total_price
                item_data['quantity'] = new_quantity
                item_data['item_total_price'] = str(new_item_total_price)

                # Update the cart with the modified item_data
                cart[cart_item_identifier] = item_data
                # print("Item total price(noncustomizable):", item_total_price)
                # print("Item data:", item_data,"cart:",cart)

            request.session['cart'] = cart

            total_amount = Decimal('0.00')

            for item_data in cart.values():
                item_total_price = Decimal(item_data.get('item_total_price', '0.00'))
                total_amount += item_total_price
            
            response_data = {
                'cart_item_identifier': cart_item_identifier,
                'item_total_price': new_item_total_price,
                'total_amount': total_amount,
            }

            return JsonResponse(response_data)
            
        else:
            return JsonResponse({'error': 'Invalid form data.'}, status=400)
    else:
        return JsonResponse({'error': 'Invalid form submission.'}, status=400)



def remove_item_from_cart_view(request):
    encrypted_table_number = getattr(request, 'encrypted_table_number', None) 

    if request.method == 'POST':
        cart_item_identifier = request.POST.get('cart_item_identifier')
        cart = request.session.get('cart', {})
        print("Cart:",cart)
        print("Clicked cart:",cart_item_identifier)
        if cart_item_identifier in cart:
            del cart[cart_item_identifier]
            request.session['cart'] = cart

    return redirect('cart_page', encrypted_table_number=encrypted_table_number)


@transaction.atomic
def place_order_view(request, table_number=0):
    encrypted_table_number = getattr(request, 'encrypted_table_number', None)
    if request.method == 'POST' and request.META.get('HTTP_X_REQUESTED_WITH') == 'XMLHttpRequest':
        # Get the order data from the AJAX request
        cart_items = request.POST.get('cart_items')
        timestamp_str = request.POST.get('timestamp')
        phone_number = request.POST.get('phone_number')
        order_type = request.POST.get('order_type')
        delivery_address = request.POST.get('delivery_address')
        # print("table place", request.POST.get('table_number'),request.POST.get('cart_items') )
        
        context_table_number = None

        # Handle both scenarios
        if table_number is 0:
            # This is a takeout/delivery order
            order_type = request.POST.get('order_type', 'take_out')  # from localStorage
            context_table_number = 000
        else:
            # This is an eat-in order
            order_type = 'eat_in'
            context_table_number = table_number
        
        
        table_number = request.POST.get('table_number')

        try:
            
            # Check if any required data is missing or invalid
            if not cart_items or not table_number or not timestamp_str:
                return JsonResponse({'status': 'error', 'message': 'Invalid order data.'}, status=400)
            
            # Convert the JSON string back to a Python list of dictionaries
            cart_items = json.loads(cart_items)
            timestamp = datetime.strptime(timestamp_str, '%Y-%m-%d %H:%M')

            # print("table number wrong")
            # Perform any necessary server-side validation on the order data
            for cart_item in cart_items:
                dish_id = cart_item.get('item_id')
                quantity = int(cart_item.get('quantity', 0))  # Convert to an integer, default to 0 if not present

                # Check if the dish exists and the quantity is a positive integer
                dish = Dish.objects.filter(pk=dish_id).first()

                if not dish or not isinstance(quantity, int) or quantity <= 0:
                    return JsonResponse({'status': 'error', 'message': 'Invalid order data.'}, status=400)
            
            # Generate the order number
            order_number = generate_order_number()
            print("Order number below")
            order = Order.objects.create(
                restaurant_id=1,
                table_number=context_table_number,
                timestamp=timestamp,
                order_type=order_type,
                order_number=order_number,
                phone_number=phone_number,
                delivery_address=delivery_address
            )
            
            # print("Saved UTC timestamp:", order.timestamp, timestamp)
            order.save()
            
            print("order saved to database")

            total_amount = Decimal('0.00')
            
            # Iterate through cart items and create OrderItem objects
            for cart_item in cart_items:
                # Create a dictionary to group selected options by category
                selected_options_by_category = {}
                
                # Iterate through the selected options received from AJAX
                # When using checkbox
                # selected_options_by_category = cart_item.get('selected_options', [])


                # Iterate through the selected options received from AJAX
                for selected_option in cart_item.get('selected_options', []):
                    category = selected_option['category']
                    options = selected_option['options'].split(', ')
                    
                    if category in selected_options_by_category:
                        selected_options_by_category[category].extend(options)
                    else:
                        selected_options_by_category[category] = options

                # Create a list to store formatted selected options
                formatted_selected_options = []
                print("selected option by cate",selected_options_by_category)

                # Iterate through the grouped options and format them
                for category, options in selected_options_by_category.items():
                    formatted_options = ', '.join(options)
                    formatted_selected_options.append(f"{category}: {formatted_options}")

                # Join the formatted options with line breaks
                formatted_customization_details = '\n'.join(formatted_selected_options)

                order_item = OrderItem.objects.create(
                    order=order,
                    dish_id=cart_item.get('item_id'),
                    quantity=int(cart_item.get('quantity', 0)),
                    extra_charges=Decimal(cart_item.get('extra_charges', 0.0)),
                    item_total_price=cart_item.get('item_total_price',0.0),
                    customization_details=formatted_customization_details
                )
                order_item.save()

                # Calculate the total price for this order item
                item_total_price = (order_item.dish.price + order_item.extra_charges) * order_item.quantity

                # Add the item total price to the total amount
                total_amount += item_total_price


            print("order item saved")
            
            # Update the order with the calculated total amount
            order.total_amount = total_amount
            order.save()

            print("from cart_item:", dish_id, quantity, total_amount)

            # Clear the cart session after successful order placement
            request.session['cart'] = {}

             # Send real-time notification to staff members
            send_realtime_notification(order)

            print("order placed successfully")
            # Return a JSON response indicating the success of the order placement
            return JsonResponse({'status': 'success', 'message': 'Order placed successfully.', 'order_id': order.order_id ,'order_number': order.order_number, 'table_number': order.table_number, 'encrypted_table_number': encrypted_table_number})

        except (json.JSONDecodeError, Dish.DoesNotExist, ValidationError) as e:
            # Log the error message to help identify the issue
            print("Error placing order: %s", str(e))
            # Rollback the transaction in case of any errors
            transaction.set_rollback(True)
            return JsonResponse({'status': 'error', 'message': 'Invalid order data.'}, status=400)

    else:
        return JsonResponse({'status': 'error', 'message': 'Invalid request.'}, status=400)
    
def generate_order_number():

    latest_order = Order.objects.order_by('-timestamp').first()

    if latest_order:
        latest_date = latest_order.timestamp.date()
        today = timezone.now().date()
        if latest_date == today:
            # Extract the numeric part of the order number and increment it
            numeric_part = int(latest_order.order_number.split('-')[1]) + 1
        else:
            # Reset to 1 if the latest order was not from today
            numeric_part = 1
    else:
        # If no orders exist, start with the first order number
        numeric_part = 1

    new_order_number = f"ORD-{str(numeric_part).zfill(3)}"

    print("Order number", new_order_number)

    return new_order_number

    
def send_realtime_notification(order):
    channel_layer = get_channel_layer()

    order_items = order.orderitem_set.all()
    order_items_data = []

    for order_item in order_items:
        dish = order_item.dish

        dish_data = {
            'order_item_id': order_item.order_item_id,
            'dish_id': order_item.dish_id,
            'dish_name': dish.name,
            'quantity': order_item.quantity,
            'extra_charges': float(order_item.extra_charges),
            'item_total_price': float(order_item.item_total_price),
            'customization_details': order_item.customization_details,
            'status': order_item.status
        }
        order_items_data.append(dish_data)

    formatted_timestamp = order.timestamp.strftime('%Y-%m-%d %H:%M')
    
    notification_data = {
        'type': 'order.notification',
        'order_id': order.order_id,
        'order_number': order.order_number,
        'table_number': order.table_number,
        'order_type': order.order_type,
        'order_item': order_items_data,
        'order_time': formatted_timestamp,
        'order_status': 'placed',
    }

    ping_data = {'type': 'ping'}
    async_to_sync(channel_layer.group_send)('staff_notifications', ping_data)
    async_to_sync(channel_layer.group_send)('staff_notifications', notification_data)
    
@jwt_required
def order_confirmation_view(request, order_id, order_number):
    encrypted_table_number = getattr(request, 'encrypted_table_number', None) 
    decrypted_table_number = getattr(request, 'decrypted_table_number', None) 

    try:
        order = get_object_or_404(Order, pk=order_id)
        if order.restaurant_id != 1 and order.table_number != decrypted_table_number:
            # Handle unauthorized access to order details (optional)
            return redirect('index', encrypted_table_number=encrypted_table_number) # Redirect to home page or error page
        
        table_number = order.table_number
        # Check if the order_number matches the order's order_number
        if order.order_number != order_number:
            return render(request, 'app_customer_interface/order_error.html',{'table_number': table_number, 'encrypted_table_number': encrypted_table_number})
        
        return render(request, 'app_customer_interface/order_confirmation.html', {'order': order, 'encrypted_table_number': encrypted_table_number})

    except Order.DoesNotExist:
        return render(request, 'app_customer_interface/order_error.html',{'table_number': table_number, 'encrypted_table_number': encrypted_table_number})

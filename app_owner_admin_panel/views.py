# app_owner_admin_panel/views.py

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.urls import reverse
from django.http import JsonResponse
from django.contrib.auth import authenticate, login, logout
from .models import Restaurant, MenuCategory, Dish, ClientProfile, CustomizationCategory, CustomizationOption
from app_customer_interface.models import Order
from .decorators import unauthenticated_user, allowed_user
from django.contrib import messages
from axes.decorators import axes_dispatch
from django.contrib.messages import get_messages
from .forms import LoginForm
from django.views.decorators.csrf import csrf_exempt
from django.utils import timezone
import base64, os
from django.core.files.base import ContentFile
from django.db import transaction

def welcome_splash_view(request):   
     
    if request.session.get('splashed') is None:
        request.session['splashed'] = True

    return render(request, 'app_owner_admin_panel/splash.html')

@axes_dispatch
@unauthenticated_user
def login_view(request):
    
    if request.method == 'POST':
        form = LoginForm(request.POST)
        if form.is_valid():
            username = form.cleaned_data.get('username')
            password = form.cleaned_data.get('password')
            user = authenticate(request, username=username, password=password)
            if user is not None:
                login(request, user)
                if user.groups.filter(name='Restaurant Owner').exists():
                    try:
                        return redirect('admin_panel')
                    except ClientProfile.DoesNotExist:
                        messages.error(request, 'User profile not found.')
                        return redirect('welcome_splash')
                elif user.groups.filter(name='Staff').exists():
                    return redirect('orders_dashboard')
            else:
                # Clear any existing error messages before adding a new one
                storage = get_messages(request)
                storage.used = True
            
            # Add the new error message
            messages.error(request, 'Login attempt failed. Please check your credentials.')
            return redirect('welcome_splash')
        else:
            print("INVALID")
    else:
        
        if 'splashed' not in request.session:
            return redirect('welcome_splash')
        else:
            form = LoginForm()

    return render(request, 'app_owner_admin_panel/login.html', {'form': form})

def logout_view(request):
    logout(request)
    request.session.pop('splashed', None)  
    return redirect('welcome_splash')

@login_required(login_url='login')
@allowed_user(allowed_roles=['Restaurant Owner'])
def admin_panel_view(request):

    # Assuming you have a ClientProfile object associated with the logged-in user
    try:
        client_profile = request.user.clientprofile
    except ClientProfile.DoesNotExist:
        return redirect('welcome_splash')

    today_start = timezone.now().replace(hour=0, minute=0, second=0, microsecond=0)
    today_end = today_start + timezone.timedelta(days=1) - timezone.timedelta(seconds=1)

    restaurant = client_profile.restaurant
    orders = Order.objects.filter(timestamp__gte=today_start, timestamp__lte=today_end)

    return render(request, 'app_owner_admin_panel/admin_panel.html', {'restaurant': restaurant, 'orders': orders})

@login_required(login_url='login')
@allowed_user(allowed_roles=['Restaurant Owner'])
def edit_profile_view(request):
    client_profile = ClientProfile.objects.get(user=request.user)
    restaurant = client_profile.restaurant

    if request.method == 'POST':
        restaurant.name = request.POST.get('name')
        restaurant.address = request.POST.get('address')
        restaurant.contact = request.POST.get('contact')
        restaurant.other_details = request.POST.get('other_details')
        restaurant.save()
        return redirect('edit_profile')

    return render(request, 'app_owner_admin_panel/edit_profile.html', {'restaurant': restaurant})

@login_required(login_url='login')
@allowed_user(allowed_roles=['Restaurant Owner'])
def edit_settings_view(request):
    client_profile = ClientProfile.objects.get(user=request.user)
    restaurant = client_profile.restaurant

    if request.method == 'POST':
        dish_time_warning = request.POST.get('dish_time_warning', restaurant.dish_time_warning)
        try:
            restaurant.dish_time_warning = int(dish_time_warning)
        except ValueError:
            restaurant.dish_time_warning = restaurant.dish_time_warning

        restaurant.save()
        return redirect('edit_settings')

    context = {
        'restaurant': restaurant,
        'dish_time_display': restaurant.get_dish_time_display()
    }
    return render(request, 'app_owner_admin_panel/edit_settings.html', context)

@login_required(login_url='login')
@allowed_user(allowed_roles=['Restaurant Owner'])
def menu_management_view(request):
    client_profile = ClientProfile.objects.get(user=request.user)
    restaurant = client_profile.restaurant
    print("Restaurant:", restaurant.name)
    menu_categories = MenuCategory.objects.filter(restaurant=restaurant)
    customization_categories = CustomizationCategory.objects.all()

    context = {
            'restaurant': restaurant,
            'menu_categories': menu_categories,
            'customization_categories': customization_categories,
    }
    # return render(request, 'app_owner_admin_panel/category_add.html', context)
    return render(request, 'app_owner_admin_panel/menu_management.html', context)

# category start
@login_required(login_url='login')
@allowed_user(allowed_roles=['Restaurant Owner'])
def category_view(request):
    client_profile = ClientProfile.objects.get(user=request.user)
    restaurant = client_profile.restaurant
    menu_categories = MenuCategory.objects.filter(restaurant=restaurant)
    customization_categories = CustomizationCategory.objects.all()

    context = {
            'restaurant': restaurant,
            'menu_categories': menu_categories,
            'customization_categories': customization_categories,
    }
    return render(request, 'app_owner_admin_panel/category.html', context)

@login_required(login_url='login')
def edit_category_view(request, category_id):
    category = get_object_or_404(MenuCategory, pk=category_id)    
    return render(request, 'app_owner_admin_panel/category_edit.html', {'category': category})

@login_required(login_url='login')
def add_category_page_view(request):
    return render(request, 'app_owner_admin_panel/category_add.html')

@login_required(login_url='login')
def add_category_view(request):
     if request.method == 'POST' and request.META.get('HTTP_X_REQUESTED_WITH') == 'XMLHttpRequest':
        try:
            print("successfull request added")
            category_name = request.POST.get('name')
            category_description = request.POST.get('description')
            MenuCategory.objects.create(
                restaurant=request.user.clientprofile.restaurant,
                name=category_name,
                description=category_description
            )
            return JsonResponse({'success': True})
        except Exception as e:
            print("Error adding category:", str(e))
            return JsonResponse({'success': False, 'error': str(e)}, status=500)

@login_required(login_url='login')
def update_category_view(request):
    if request.method == "POST":
        category_id = request.COOKIES.get('category_id')
        if category_id:
            category = get_object_or_404(MenuCategory, pk=category_id)
            name = request.POST.get('name')
            description = request.POST.get('description')
            category.name = name
            category.description = description
            category.save()

            # messages.success(request, 'Category updated successfully.')
            return redirect('edit_category', category_id=category_id)
        else:
            return JsonResponse({'success': False, 'message': 'Category ID not found in cookie.'})
    return redirect('category')

@login_required(login_url='login')
def delete_category_view(request, category_id):
    category = get_object_or_404(MenuCategory, pk=category_id)
    try:
        if request.method == "POST":
            dishes = Dish.objects.filter(category=category)
            
            for dish in dishes:
                for cat in dish.customization_categories.all():
                    cat.delete()
                
                for option in dish.customization_options.all():
                    option.delete()
            
            category.delete()
            return redirect(reverse('category'))
    except Exception as e:
        messages.error(request, 'Error deleting category. Please try again later.')
    return redirect(reverse('category'))

# menu item start
@login_required(login_url='login')
@allowed_user(allowed_roles=['Restaurant Owner'])
def menu_items_view(request):
    client_profile = ClientProfile.objects.get(user=request.user)
    restaurant = client_profile.restaurant
    menu_categories = MenuCategory.objects.filter(restaurant=restaurant)
    customization_categories = CustomizationCategory.objects.all()

    context = {
        'menu_categories': menu_categories,
        'customization_categories': customization_categories,
    }
    return render(request, 'app_owner_admin_panel/menu_item.html', context)

@login_required(login_url='login')
def edit_dish_view(request, dish_id):
    client_profile = ClientProfile.objects.get(user=request.user)
    restaurant = client_profile.restaurant
    menu_categories = MenuCategory.objects.filter(restaurant=restaurant)
    dish = get_object_or_404(Dish, pk=dish_id)  
    customization_categories = dish.customization_categories.all() 

    customization_data = []

    for category in customization_categories:
        if '_' in category.name:
            category_name = category.name.split('_', 1)[1]
        else:
            category_name = category.name

        options = category.customizationoption_set.all()
        options_without_prefix = []
        
        for option in options:
            if '_' in option.name:
                option_name = option.name.split('_', 1)[1]
            else:
                option_name = option.name
            
            options_without_prefix.append({
                'id': option.id,
                'name': option_name,
                'price': option.price
            })
        
        customization_data.append({
            'name': category_name,
            'max_selection': category.max_selection,
            'options': options_without_prefix
    })
    
    # print('Customization data, options, and customization', customization_data)
    context = {
        'dish': dish,
        'menu_categories': menu_categories,
        'image_1x1_url': dish.image_1x1.url if dish.image_1x1 else '',
        'image_16x9_url': dish.image_16x9.url if dish.image_16x9 else '',
        'customization_categories':customization_data,
    }
    
    return render(request, 'app_owner_admin_panel/menu_item_edit.html', context)

@login_required(login_url='login')
def delete_dish_view(request, dish_id):
    menu_item = get_object_or_404(Dish, pk=dish_id)
    try:
        if request.method == "POST":
            with transaction.atomic():
                current_categories = list(menu_item.customization_categories.all())
                current_options = list(menu_item.customization_options.all())

                menu_item.customization_categories.clear()
                menu_item.customization_options.clear()

                for option in current_options:
                    if not option.dish_set.exists():
                        option.delete()

                for category in current_categories:
                    if not category.dish_set.exists():
                        category.delete()

                menu_item.delete()

            messages.success(request, "Dish deleted successfully.")
            return redirect(reverse('menu_items'))
    except Exception as e:
            print("Error deleting item:", str(e))
            messages.error(request, 'Error deleting item. Please try again later.')
    return redirect(reverse('menu_items'))

@login_required(login_url='login')
def update_dish_view(request):
    if request.method == "POST":
        dish_id = request.COOKIES.get('dish_id')
        
        if not dish_id:
            messages.error(request, "No dish ID provided.")
            return redirect(reverse('menu_items'))
        
        if dish_id:
            dish = get_object_or_404(Dish, pk=dish_id)
            
            dish.name = request.POST.get('name')
            dish.description = request.POST.get('description')
            dish.price = request.POST.get('price')
            dish.customization_available = bool(request.POST.get('customizable', False))
            category_id = request.POST.get('category')
            dish.category = get_object_or_404(MenuCategory, pk=category_id)

            if 'image_1x1' in request.FILES:
                dish.image_1x1 = request.FILES['image_1x1']
            if 'image_16x9' in request.FILES:
                dish.image_16x9 = request.FILES['image_16x9']

            if dish.customization_available:
                current_categories = list(dish.customization_categories.all())
                current_options = list(dish.customization_options.all())
                updated_options = []
                updated_categories = [] 

                dish.customization_categories.clear()
                dish.customization_options.clear()

                category_count = len([key for key in request.POST if key.startswith('customization_category_name')])

                for category_index in range(category_count):
                    category_name = request.POST.get(f'customization_category_name[{category_index}]')
                    max_option = request.POST.get(f'max_options[{category_index}]')

                    full_category_name = f"{dish.name}_{category_name}"

                    customization_category, created = CustomizationCategory.objects.get_or_create(
                        name=full_category_name, 
                        defaults={'max_selection': max_option}
                    )

                    if not created:
                        customization_category.max_selection = max_option
                        customization_category.save()
                    
                    dish.customization_categories.add(customization_category)

                    option_count = len([key for key in request.POST if key.startswith(f'customization_option_name[{category_index}]')])

                    if option_count > 0:
                        dish.customization_categories.add(customization_category)
                        updated_categories.append(customization_category)

                    for option_index in range(option_count):
                        option_name = request.POST.get(f'customization_option_name[{category_index}][{option_index}]')
                        option_price = request.POST.get(f'customization_option_price[{category_index}][{option_index}]')

                        full_option_name = f"{dish.name}_{option_name}"

                        customization_option, option_created = CustomizationOption.objects.get_or_create(
                            name=full_option_name,
                            category=customization_category,
                            defaults={'price': option_price}
                        )

                        if not option_created:
                            customization_option.price = option_price
                            customization_option.save()

                        updated_options.append(customization_option)
                        dish.customization_options.add(customization_option)
                
                for option in current_options:
                    if option not in updated_options:
                        dish.customization_options.remove(option)
                        if not option.dish_set.exists():
                            option.delete()

                for category in current_categories:
                    if category not in updated_categories:
                        dish.customization_categories.remove(category)
                        if not category.dish_set.exists():
                            category.delete()

            else:
                current_categories = list(dish.customization_categories.all())
                current_options = list(dish.customization_options.all())

                dish.customization_categories.clear()
                dish.customization_options.clear()

                for option in current_options:
                    if not option.dish_set.exists():
                        option.delete()

                for category in current_categories:
                    if not category.dish_set.exists():
                        category.delete()

            dish.save()

            return redirect('edit_dish', dish_id=dish_id)
        else:
            return JsonResponse({'success': False, 'message': 'Dish ID not found in cookie.'})
        
    return redirect('edit_dish', dish_id=dish_id)

@login_required(login_url='login')
@allowed_user(allowed_roles=['Restaurant Owner'])
def add_dish_page_view(request):
    client_profile = ClientProfile.objects.get(user=request.user)
    restaurant = client_profile.restaurant
    menu_categories = MenuCategory.objects.filter(restaurant=restaurant)

    context = {
        'menu_categories': menu_categories,
    }

    return render(request, 'app_owner_admin_panel/dish_add.html', context)

import json

@login_required(login_url='login')
@allowed_user(allowed_roles=['Restaurant Owner'])
def add_dish_view(request):
    if request.method == 'POST':
            required_fields = ['name', 'price', 'category']
            errors = {}

            for field in required_fields:
                if not request.POST.get(field):
                    errors[field] = f"{field.capitalize()} is required"

            if errors:
                return JsonResponse({'success': False, 'errors': errors}, status=400)
            
            try:
                category = get_object_or_404(MenuCategory, pk=request.POST.get('category'))

                dish_name = request.POST.get('name')

                customization_available = bool(request.POST.get('customizable', False))

                dish = Dish.objects.create(
                    restaurant=request.user.clientprofile.restaurant,
                    name=dish_name,
                    price=request.POST.get('price'),
                    description=request.POST.get('description', ''),
                    category=category,
                    customization_available=customization_available
                )

                if customization_available:
                    index = 0
                    while True:
                        group_key = f'customization_groups[{index}][category_name]'
                        exists = group_key in request.POST
                        if not exists:
                            break
                        
                        category_name = request.POST[group_key].strip()
                        max_options = request.POST.get(f'customization_groups[{index}][max_options]', 1)

                        category_name_prefixed = f"{dish.name}_{category_name}"
                  

                        # Create customization category
                        customization_category, category_created = CustomizationCategory.objects.get_or_create(
                            name=category_name_prefixed,
                            max_selection=max_options
                        )

                        if not category_created:
                            customization_category.max_selection = max_options
                            customization_category.save()

                        dish.customization_categories.add(customization_category)

                        # Process options
                        option_index = 0
                        while True:
                            option_name_key = f'customization_groups[{index}][options][{option_index}][name]'
                            if option_name_key not in request.POST:
                                break
                            
                            option_name = request.POST[option_name_key].strip()
                            option_price = request.POST.get(
                                f'customization_groups[{index}][options][{option_index}][price]', 0
                            )

                            option_name_prefixed = f"{dish.name}_{option_name}"
                            customization_option, option_created = CustomizationOption.objects.get_or_create(
                                name=option_name_prefixed,
                                category=customization_category,
                                defaults={'price': option_price}
                            )

                            if not option_created:
                                customization_option.price = option_price
                                customization_option.save()

                            dish.customization_options.add(customization_option)
                            option_index += 1
                        
                        index += 1
            
                for image_field in ['image_1x1', 'image_16x9']:
                    if image_field in request.FILES:
                        setattr(dish, image_field, request.FILES[image_field])

                dish.save()

                return JsonResponse({'success': True})
            except Exception as e:
                print("Error adding category:", str(e))
                return JsonResponse({'success': False, 'error': str(e)}, status=500)

# menu item end

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
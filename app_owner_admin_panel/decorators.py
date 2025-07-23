from django.http import HttpResponse
from django.shortcuts import redirect, render
from .models import ClientProfile
from django.contrib import messages
from functools import wraps

def unauthenticated_user(view_func):
    @wraps(view_func)
    def wrapper_func(request, *args, **kwargs):
        if request.user.is_authenticated:
            if request.user.groups.filter(name='Restaurant Owner').exists():
                # print("Going to admin panel", request)  # Debug statement
                return redirect('admin_panel')
            elif request.user.groups.filter(name='Staff').exists():
                # print("Redirecting to orders dashboard", request)  # Debug statement
                return redirect('orders_dashboard')
            else:
                print("Authenticated but not in a recognized group", request.user.groups)  # Debug statement
                return
        else:
            return view_func(request, *args, **kwargs)

    return wrapper_func

def allowed_user(allowed_roles=[]):
    def decorator(view_func):
        @wraps(view_func)
        def wrapper_func(request, *args, **kwargs):
            if request.user.groups.filter(name__in=allowed_roles).exists():
                # print("request user", request.user)
                return view_func(request, *args, **kwargs)
            else:
                return render(request, 'app_owner_admin_panel/access_denied.html', {'access_denied': True})
        return wrapper_func
    return decorator
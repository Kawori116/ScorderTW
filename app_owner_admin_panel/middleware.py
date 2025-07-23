# middleware.py
from datetime import datetime, timedelta
from .models import SystemConfiguration
from django.contrib.auth import logout
from django.contrib import messages
from django.core.cache import cache
from django.http import HttpResponseForbidden

class SystemStatusMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        system_config = SystemConfiguration.objects.first()

        if system_config.automatic_management:
            now = datetime.now().time()
            if system_config.opening_time <= now < system_config.closing_time:
                print("Middleware Open")
                system_config.system_open = True
            else:
                print("Middleware Closed")
                system_config.system_open = False
            system_config.save()

        # Cache the system status
        cache.set('system_status', system_config.system_open)

        return self.get_response(request)


class AutoLogoutMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.user.is_authenticated:
            # Check if the user has a last activity timestamp in the session
            last_activity_str = request.session.get('last_activity')
            if last_activity_str:
                # Convert the last_activity string back to a datetime object
                last_activity = datetime.fromisoformat(last_activity_str)
                # Calculate the time elapsed since the last activity
                elapsed_time = datetime.now() - last_activity

                # Define the inactivity timeout (30 minutes in this case) or 120 min for 2 hour
                inactivity_timeout = timedelta(minutes=120)

                # If the user has been inactive for more than the timeout, log them out
                if elapsed_time > inactivity_timeout:
                    logout(request)
                    messages.info(request, 'You have been logged out due to inactivity.')

            # Update the last activity timestamp in the session
            request.session['last_activity'] = datetime.now().isoformat()

        response = self.get_response(request)
        return response


class WhitelistMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response
        
    def __call__(self, request):
        # Define the allowed IP addresses for each app
        allowed_ips_whitelist = {
            'app_owner': ['127.0.0.1'],
            'app_staff': ['127.0.0.1'],
            'login': ['127.0.0.1'],
        }

        # Get the current app name based on the URL path
        app_name = None
        if request.path.startswith('/app_owner/'):
            app_name = 'app_owner'
        elif request.path.startswith('/app_staff/'):
            app_name = 'app_staff'
        elif request.path.startswith('/login/'):
            app_name = 'login'

        # Check if the request is from an allowed IP for the current app
        if app_name and request.META.get('REMOTE_ADDR') not in allowed_ips_whitelist[app_name]:
            return HttpResponseForbidden("Access denied. Your IP is not allowed to access this app.")
        elif request.path.startswith('/app_customer/'):
            return self.get_response(request)
        
        response = self.get_response(request)
        return response
    
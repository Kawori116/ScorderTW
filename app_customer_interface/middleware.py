# app_customer_interface/middleware.py
from django.http import HttpResponseForbidden, Http404
from cryptography.fernet import Fernet

from django.utils import timezone
import pytz

class TimezoneMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        tz_offset = request.headers.get('X-Timezone-Offset')
        if tz_offset:
            try:
                offset_minutes = int(float(tz_offset) * 60)
                timezone.activate(pytz.FixedOffset(offset_minutes))
            except (ValueError, TypeError):
                timezone.activate(pytz.UTC)
        else:
            timezone.activate(pytz.UTC)
        response = self.get_response(request)
        timezone.deactivate()
        return response
    
class DecryptTableNumberMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response
        self.key = self.load_key()

    def load_key(self):
        secret_key = '0iseESfRYHk-4PQuAhXDCp64iUnN-bFIPZlYLDUHJNg='
        return secret_key
    
    def __call__(self, request):
        response = self.get_response(request)
        return response
    
    def decrypt_data(self, encrypted_data):
        key = self.load_key()
        f = Fernet(key)
        try:
            decrypted_key = f.decrypt(encrypted_data.encode()).decode()
            return decrypted_key
        except:
            raise Http404("Invalid or expired link")

    def process_view(self, request, view_func, view_args, view_kwargs):
        if request.path.startswith('/app_customer/'):
            encrypted_table_number = view_kwargs.pop('encrypted_table_number')
            if encrypted_table_number:
                try:
                    decrypted_table_number = self.decrypt_data(encrypted_table_number)
                    request.encrypted_table_number = encrypted_table_number
                    request.decrypted_table_number = decrypted_table_number 
                except Exception as e:
                    return HttpResponseForbidden(str(e))

        return None

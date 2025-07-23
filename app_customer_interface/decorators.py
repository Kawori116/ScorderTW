import jwt
from functools import wraps
from django.http import HttpResponseForbidden, HttpResponseRedirect
from cryptography.fernet import Fernet


def jwt_required(view_func):
    secret_key = '0iseESfRYHk-4PQuAhXDCp64iUnN-bFIPZlYLDUHJNg='
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        token = request.COOKIES.get('auth_token')
        if not token:
            return HttpResponseForbidden("Invalid Page") #Authorization token is required

        try:
            payload = jwt.decode(token, secret_key, algorithms=['HS256'])
            request.table_number = payload['table_number']
        except jwt.ExpiredSignatureError:
            return HttpResponseForbidden("Invalid Page") #Token has expired
        except jwt.InvalidTokenError:
            return HttpResponseForbidden("Invalid Page") #Invalid token

        return view_func(request, *args, **kwargs)
    return _wrapped_view
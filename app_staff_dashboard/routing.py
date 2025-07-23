# app_staff_dashboard/routing.py
from django.urls import re_path
from . import consumers

websocket_urlpatterns = [
    re_path(r'app_staff/ws/orders/$', consumers.OrderNotificationConsumer.as_asgi()),
    re_path(r'app_staff/ws/kitchen/$', consumers.KitchenConsumer.as_asgi()),
]

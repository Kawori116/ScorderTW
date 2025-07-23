# app_customer_interface/urls.py

from django.urls import path
from . import views

urlpatterns = [
    path('handle_qr/', views.handle_qr_scan_view, name='handle_qr_scan'),
    path('welcome/', views.welcome_splash_view, name='welcome_splash'),
    path('', views.index_view, name='index'),
    path('item/<int:dish_id>/', views.item_details_view, name='item_details'),
    path('cart/', views.cart_page_view, name='cart_page'),
    path('update_cart/', views.update_cart_view, name='update_cart'),
    path('remove_item_from_cart/', views.remove_item_from_cart_view, name='remove_item_from_cart'),
    path('place_order/<int:table_number>/', views.place_order_view, name='place_order'),
    path('order_confirmation/<str:order_number>-<int:order_id>/', views.order_confirmation_view, name='order_confirmation'),
    path('clear_cart/', views.clear_cart_view, name='clear_cart'),
    path('check_cart_for_sold_out_items/', views.check_cart_for_sold_out_items_view, name='check_cart_for_sold_out_items'),
]

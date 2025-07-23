# app_staff_dashboard/urls.py

from django.urls import path
from . import views

urlpatterns = [
    # path('', views.staff_login_view, name='login'),
    path('', views.orders_dashboard_view, name='orders_dashboard'),
    path('order/<int:order_id>/', views.order_details_view, name='order_details'),
    path('update_order_item/', views.update_order_item_view, name='update_order_item'),
    path('delete_order_item/', views.delete_order_item_view, name='delete_order_item'),
    path('cancel_order/', views.cancel_order_view, name='cancel_order'),
    path('confirm_order/', views.confirm_order_view, name='confirm_order'),
    path('kitchen/', views.kitchen_interface_view, name='kitchen_interface'),
    path('accept_order/', views.accept_order_view, name='accept_order'),
    path('mark_order_completed/', views.mark_order_completed, name='mark_order_completed'),
    # path('lookup_order/', views.lookup_order_view, name='lookup_order'),
    path('open_system/', views.open_system_view, name='open_system'),
    path('close_system/', views.close_system_view, name='close_system'),
    path('update_management_mode/', views.update_management_mode_view, name='update_management_mode'),
    path('dish_management/', views.dish_management_view, name='dish_management'),
    path('mark_dish_sold_out/', views.mark_dish_sold_out, name='mark_dish_sold_out'),
    path('get_total_amount/', views.get_total_amount, name='get_total_amount'),
]

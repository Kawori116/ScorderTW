# app_owner_admin_panel/urls.py

from django.urls import path
from . import views

login_view = views.login_view

urlpatterns = [
    # path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('welcome/', views.welcome_splash_view, name='welcome_splash'),
    path('', views.admin_panel_view, name='admin_panel'),
    path('edit_profile/', views.edit_profile_view, name='edit_profile'),
    path('edit_settings/', views.edit_settings_view, name='edit_settings'),

    # category 
    path('category/', views.category_view, name='category'),
    path('edit_category/<int:category_id>/', views.edit_category_view, name='edit_category'),
    path('add_category_page', views.add_category_page_view, name='add_category_page'),
    path('add_category', views.add_category_view, name='add_category'),
    path('update_category', views.update_category_view, name='update_category'),
    path('delete_category/<int:category_id>/', views.delete_category_view, name='delete_category'),

    # menu items
    path('menu_items/', views.menu_items_view, name='menu_items'),
    path('edit_dish/<int:dish_id>/', views.edit_dish_view, name='edit_dish'),
    path('delete_dish/<int:dish_id>/', views.delete_dish_view, name='delete_dish'),
    path('update_dish', views.update_dish_view, name='update_dish'),
    path('add_dish_page', views.add_dish_page_view, name='add_dish_page'),
    path('add_dish', views.add_dish_view, name='add_dish'),
    
    path('get_total_amount/', views.get_total_amount, name='get_total_amount'),
]

from django.contrib import admin
from django.urls import path, include
from app_owner_admin_panel.views import login_view
from django.conf import settings
from django.conf.urls.static import static
# from app_customer_interface.views import index_view

urlpatterns = [
    path('admin/', admin.site.urls),
    path('login/', login_view, name='login'),
    path('app_owner/', include('app_owner_admin_panel.urls')),
    path('app_staff/', include('app_staff_dashboard.urls')),
    # path('app_customer/', include('app_customer_interface.urls')),
    path('app_customer/<str:encrypted_table_number>/', include('app_customer_interface.urls')),
]

# Serve media files during development
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
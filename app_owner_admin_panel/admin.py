# app_owner_admin_panel/admin.py
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.contrib.auth.models import User
from .models import Restaurant, MenuCategory, Dish, ClientProfile, CustomizationCategory, CustomizationOption, SystemConfiguration
from .forms import CustomUserCreationForm
from django import forms

class RestaurantAdmin(admin.ModelAdmin):
    list_display = ('name', 'address', 'contact')
    search_fields = ('name', 'address', 'contact')

class SystemConfigurationAdmin(admin.ModelAdmin):
    list_display = ('system_open', 'opening_time', 'closing_time', 'automatic_management')

class MenuCategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'description', 'restaurant') 
    list_filter = ('restaurant__name',)
    search_fields = ('name', 'description')

class DishAdminForm(forms.ModelForm):
    customization_categories = forms.ModelMultipleChoiceField(
        queryset=CustomizationCategory.objects.all(),
        required=False,
        widget=forms.CheckboxSelectMultiple,  # You can use a different widget if preferred
    )
    
    customization_options = forms.ModelMultipleChoiceField(
        queryset=CustomizationOption.objects.all(),
        required=False,
        widget=forms.CheckboxSelectMultiple,  # You can use a different widget if preferred
    )

    class Meta:
        model = Dish
        fields = '__all__'
        
class DishAdmin(admin.ModelAdmin):
    list_display = ('name', 'price', 'customization_available', 'category', 'restaurant', 'is_sold_out') 
    list_filter = ('restaurant__name', 'category__name')
    search_fields = ('name', 'description')
    form = DishAdminForm

class ClientProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'restaurant') 
    list_filter = ('restaurant__name',)
    search_fields = ('user__username', 'restaurant__name')

class ClientProfileInline(admin.StackedInline):
    model = ClientProfile
    can_delete = False
    verbose_name_plural = 'Client Profile'

class CustomUserAdmin(UserAdmin):
    add_form = CustomUserCreationForm
    inlines = (ClientProfileInline,)

    list_display = ('username', 'email', 'first_name', 'last_name', 'is_staff', 'is_superuser', 'get_restaurant')
    list_filter = ('is_staff', 'is_superuser', 'clientprofile__restaurant__name')
    search_fields = ('username', 'email', 'first_name', 'last_name', 'clientprofile__restaurant__name')

    def get_restaurant(self, obj):
        return obj.clientprofile.restaurant.name 

    get_restaurant.short_description = 'Restaurant'

class CustomizationCategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'max_selection')
    
class CustomizationOptionAdmin(admin.ModelAdmin):
    list_display = ('name', 'category', 'price')
    list_filter = ('category',)

admin.site.unregister(User)
admin.site.register(User, CustomUserAdmin)
admin.site.register(Restaurant, RestaurantAdmin)
admin.site.register(MenuCategory, MenuCategoryAdmin)
admin.site.register(Dish, DishAdmin)
admin.site.register(ClientProfile, ClientProfileAdmin)
admin.site.register(CustomizationCategory, CustomizationCategoryAdmin)
admin.site.register(CustomizationOption, CustomizationOptionAdmin)
admin.site.register(SystemConfiguration, SystemConfigurationAdmin)
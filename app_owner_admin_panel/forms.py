# app_owner_admin_panel/forms.py
from django import forms
from django.contrib.auth.forms import UserCreationForm
from .models import Restaurant, MenuCategory, Dish
from django.contrib.auth.models import User

class CustomUserCreationForm(UserCreationForm):
    restaurant = forms.ModelChoiceField(queryset=Restaurant.objects.all())

    class Meta(UserCreationForm.Meta):
        model = User
        fields = UserCreationForm.Meta.fields + ('restaurant',)

class LoginForm(forms.Form):
    username = forms.CharField(label='Username', max_length=100, required=True)
    password = forms.CharField(label='Password', widget=forms.PasswordInput, required=True)

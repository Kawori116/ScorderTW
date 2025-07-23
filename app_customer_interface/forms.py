# app_customer_interface/forms.py
from django import forms

class AddToCartForm(forms.Form):
    quantity = forms.IntegerField(min_value=1, max_value=15)

class UpdateCartForm(forms.Form):
    quantity = forms.IntegerField(min_value=1, max_value=15)
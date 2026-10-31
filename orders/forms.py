from django import forms
from orders.models import Order


class CheckoutForm(forms.ModelForm):
    payment_method = forms.ChoiceField(label='Способ оплаты', choices=[
        ('cash', 'Наличными при получении'), ('card', 'Картой при получении')])

    class Meta:
        model = Order
        fields = ['shipping_address', 'payment_method']
        labels = {'shipping_address': 'Адрес доставки'}
        widgets = {'shipping_address': forms.Textarea(attrs={'rows': 3})}

from django import forms

from products.models import Category


class ProductFilterForm(forms.Form):
    search = forms.CharField(required=False, max_length=100)
    categories = forms.ModelChoiceField(
        queryset=Category.objects.all(), to_field_name='slug', required=False,
        empty_label='Все категории')
    min_price = forms.DecimalField(required=False, min_value=0, max_digits=10, decimal_places=2)
    max_price = forms.DecimalField(required=False, min_value=0, max_digits=10, decimal_places=2)
    sorting = forms.ChoiceField(required=False, choices=[
        ('-created_at', 'Сначала новые'),
        ('price', 'Цена по возрастанию'),
        ('-price', 'Цена по убыванию'),
        ('popularity', 'По популярности'),
    ])

    def clean(self):
        data = super().clean()
        minimum = data.get('min_price')
        maximum = data.get('max_price')
        if minimum is not None and maximum is not None and minimum > maximum:
            self.add_error('max_price', 'Максимальная цена меньше минимальной.')
        return data

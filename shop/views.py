from decimal import Decimal

from django import forms
from django.contrib import messages
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.mixins import LoginRequiredMixin
from django.urls import reverse_lazy
from django.views.generic import CreateView, ListView
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from orders.models import Order
from products.models import Product


class CartQuantityForm(forms.Form):
    quantity = forms.IntegerField(min_value=1, max_value=2147483647)


def cart_detail(request):
    cart = request.session.get('cart', {})
    items = []
    total = Decimal('0.00')
    products = Product.objects.filter(is_active=True).in_bulk(cart)
    # Prices and availability always come from the database.
    for product_id, quantity in list(cart.items()):
        product = products.get(int(product_id))
        if product is None or product.stock == 0:
            del cart[product_id]
            messages.warning(request, 'Недоступный товар удалён из корзины.')
            continue
        if quantity > product.stock:
            quantity = product.stock
            cart[product_id] = quantity
            messages.warning(request, f'Количество «{product.name}» уменьшено до доступного остатка.')
        subtotal = product.price * quantity
        items.append({'product': product, 'quantity': quantity, 'subtotal': subtotal})
        total += subtotal
    request.session['cart'] = cart
    return render(request, 'shop/cart.html', {'items': items, 'total': total})


@require_POST
def cart_add(request, product_id):
    product = get_object_or_404(Product, pk=product_id, is_active=True)
    form = CartQuantityForm(request.POST)
    cart = request.session.get('cart', {})
    if not form.is_valid():
        messages.error(request, 'Введите целое положительное количество.')
    else:
        quantity = cart.get(str(product.pk), 0) + form.cleaned_data['quantity']
        if quantity > product.stock:
            messages.error(request, 'Недостаточно товара на складе.')
        else:
            cart[str(product.pk)] = quantity
            request.session['cart'] = cart
            messages.success(request, 'Товар добавлен в корзину.')
    return redirect('product_detail', slug=product.slug)


@require_POST
def cart_update(request, product_id):
    cart = request.session.get('cart', {})
    product = Product.objects.filter(pk=product_id, is_active=True).first()
    form = CartQuantityForm(request.POST)
    if str(product_id) not in cart:
        messages.error(request, 'Товара нет в корзине.')
    elif product is None or product.stock == 0:
        del cart[str(product_id)]
        request.session['cart'] = cart
        messages.warning(request, 'Недоступный товар удалён из корзины.')
    elif not form.is_valid():
        messages.error(request, 'Введите целое положительное количество.')
    elif form.cleaned_data['quantity'] > product.stock:
        messages.error(request, 'Недостаточно товара на складе.')
    else:
        cart[str(product_id)] = form.cleaned_data['quantity']
        request.session['cart'] = cart
        messages.success(request, 'Количество обновлено.')
    return redirect('shop:cart')


@require_POST
def cart_remove(request, product_id):
    cart = request.session.get('cart', {})
    cart.pop(str(product_id), None)
    request.session['cart'] = cart
    messages.success(request, 'Товар удалён из корзины.')
    return redirect('shop:cart')


class RegisterView(CreateView):
    form_class = UserCreationForm
    template_name = 'shop/register.html'
    success_url = reverse_lazy('login')

    def form_valid(self, form):
        messages.success(self.request, 'Регистрация завершена. Теперь вы можете войти.')
        return super().form_valid(form)


class AccountView(LoginRequiredMixin, ListView):
    template_name = 'shop/account.html'
    context_object_name = 'orders'

    def get_queryset(self):
        return Order.objects.filter(owner=self.request.user)

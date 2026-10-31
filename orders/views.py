from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import ValidationError
from django.shortcuts import get_object_or_404, redirect
from django.views.decorators.http import require_POST
from django.views.generic import DetailView, FormView

from orders.forms import CheckoutForm
from orders.models import Order, OrderStatus


class OrderDetailView(LoginRequiredMixin, DetailView):
    template_name = 'orders/order_detail.html'
    context_object_name = 'order'

    def get_queryset(self):
        return Order.objects.filter(owner=self.request.user).prefetch_related('items__product')


class CheckoutView(LoginRequiredMixin, FormView):
    template_name = 'orders/checkout.html'
    form_class = CheckoutForm

    def form_valid(self, form):
        try:
            order = Order.create_from_cart(
                self.request.user, self.request.session.get('cart', {}),
                form.cleaned_data['shipping_address'], form.cleaned_data['payment_method'])
        except ValidationError as error:
            form.add_error(None, ' '.join(error.messages))
            messages.error(self.request, 'Заказ не оформлен. Проверьте корзину и данные доставки.')
            return self.form_invalid(form)
        self.request.session['cart'] = {}
        messages.success(self.request, f'Заказ №{order.pk} успешно оформлен.')
        return redirect('orders:detail', pk=order.pk)


@login_required
@require_POST
def cancel_order(request, pk):
    order = get_object_or_404(Order, pk=pk, owner=request.user)
    try:
        if order.status != OrderStatus.PENDING:
            raise ValidationError('Можно отменить только заказ, ожидающий оплаты.')
        order.change_status(OrderStatus.CANCELLED, request.user, customer=True)
    except ValidationError as error:
        messages.error(request, ' '.join(error.messages))
    else:
        messages.success(request, 'Заказ отменён.')
    return redirect('orders:detail', pk=order.pk)

from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import DetailView

from orders.models import Order


class OrderDetailView(LoginRequiredMixin, DetailView):
    template_name = 'orders/order_detail.html'
    context_object_name = 'order'

    def get_queryset(self):
        return Order.objects.filter(owner=self.request.user).prefetch_related('items__product')

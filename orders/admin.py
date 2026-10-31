from django import forms
from django.contrib import admin
from django.db import transaction

from orders.models import Order, OrderItem


class OrderAdminForm(forms.ModelForm):
    class Meta:
        model = Order
        fields = '__all__'

    def clean_status(self):
        status = self.cleaned_data['status']
        previous = Order.objects.get(pk=self.instance.pk)
        if previous.status != status:
            previous.validate_transition(status)
        return status


class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0
    readonly_fields = ('product', 'quantity', 'price', 'created_at')
    can_delete = False

    def has_add_permission(self, request, obj=None):
        return False


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    form = OrderAdminForm
    list_display = ('owner', 'status', 'payment_method', 'shipping_address', 'total_price', 'created_at')
    list_filter = ('status', 'payment_method')
    search_fields = ('owner__username', 'owner__email')
    inlines = (OrderItemInline,)
    readonly_fields = ('owner', 'payment_method', 'shipping_address', 'total_price', 'created_at', 'updated_at')

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

    def changeform_view(self, request, object_id=None, form_url='', extra_context=None):
        # Keep the status locked during form validation and saving.
        if request.method == 'POST' and object_id and object_id.isdigit():
            with transaction.atomic():
                Order.objects.select_for_update().filter(pk=object_id).first()
                return super().changeform_view(request, object_id, form_url, extra_context)
        return super().changeform_view(request, object_id, form_url, extra_context)

    def save_model(self, request, obj, form, change):
        if 'status' in form.changed_data:
            obj.change_status(obj.status, request.user)

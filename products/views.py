from django.db.models import Avg, Q, Sum
from django.shortcuts import render
from django.views.generic import ListView, TemplateView, DetailView

from products.models import Product
from products.forms import ProductFilterForm


# Create your views here.
class ProductList(ListView):
    model = Product
    context_object_name = 'products'
    template_name = 'products/product_list.html'
    paginate_by = 6

    queryset = (Product.objects.filter(is_active=True)
                .select_related('category')
                .prefetch_related('reviews__owner'))

    def get_queryset(self):
        products = super().get_queryset()
        self.filter_form = ProductFilterForm(self.request.GET)
        if not self.filter_form.is_valid():
            return products.none()

        filters = self.filter_form.cleaned_data
        if filters['categories']:
            products = products.filter(category=filters['categories'])
        if filters['search']:
            products = products.filter(
                Q(name__icontains=filters['search']) |
                Q(description__icontains=filters['search']))
        if filters['min_price'] is not None:
            products = products.filter(price__gte=filters['min_price'])
        if filters['max_price'] is not None:
            products = products.filter(price__lte=filters['max_price'])

        sorting = filters['sorting'] or '-created_at'
        if sorting == 'popularity':
            products = products.annotate(popularity=Sum(
                'orderitem__quantity',
                filter=Q(orderitem__order__status__in=['paid', 'shipped', 'delivered']),
                default=0))
            sorting = '-popularity'
        return products.order_by(sorting, '-pk')

    def paginate_queryset(self, queryset, page_size):
        paginator = self.get_paginator(queryset, page_size)
        page = paginator.get_page(self.request.GET.get('page'))
        return paginator, page, page.object_list, page.has_other_pages()

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['filter_form'] = self.filter_form
        return context




class GuidesReceiptView(TemplateView):
    template_name = 'products/guides-recipes.html'


class ProductDetailsView(DetailView):
    template_name = 'products/product_detail.html'
    model = Product
    queryset = (Product.objects.filter(is_active=True)
                .select_related('category')
                .prefetch_related('reviews__owner'))




    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        product = self.object
        rating = product.reviews.aggregate(average=Avg('rating'))['average']
        context['average_rating'] = rating
        full_stars = int(rating or 0)
        has_half_star = rating is not None and rating - full_stars >= 0.5
        empty_stars = 5 - full_stars - int(has_half_star)
        context['full_stars'] = range(full_stars)
        context['has_half_star'] = has_half_star
        context['empty_stars'] = range(empty_stars)
        context['reviews_count'] = product.reviews.count()
        for review in product.reviews.all():
            review.stars = range(review.rating)
            review.empty_stars = range(5-review.rating)

        return context

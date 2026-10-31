from django.db.models import Avg, Q, Sum
from django.shortcuts import render
from django.shortcuts import redirect
from django.contrib import messages
from django.contrib.auth.views import redirect_to_login
from django.db import IntegrityError, transaction
from django.views.generic import ListView, TemplateView, DetailView

from products.models import Product
from products.forms import ProductFilterForm
from reviews.forms import ReviewForm
from reviews.models import Review


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




    def post(self, request, *args, **kwargs):
        self.object = self.get_object()
        if not request.user.is_authenticated:
            messages.error(request, 'Войдите, чтобы оставить отзыв.')
            return redirect_to_login(request.path)
        form = ReviewForm(request.POST, instance=Review(owner=request.user, product=self.object))
        if form.is_valid():
            try:
                with transaction.atomic():
                    form.save()
            except IntegrityError:
                form.add_error(None, 'Отзыв не сохранён. Возможно, вы уже отправили отзыв на этот товар.')
            else:
                messages.success(request, 'Спасибо! Ваш отзыв опубликован.')
                return redirect('product_detail', slug=self.object.slug)
        messages.error(request, 'Отзыв не опубликован. Исправьте ошибки формы.')
        return self.render_to_response(self.get_context_data(review_form=form))

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
        if self.request.user.is_authenticated and 'review_form' not in context:
            context['review_form'] = ReviewForm(instance=Review(owner=self.request.user, product=product))
        for review in product.reviews.all():
            review.stars = range(review.rating)
            review.empty_stars = range(5-review.rating)

        return context

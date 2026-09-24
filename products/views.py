

from django.shortcuts import render
from django.views.generic import ListView, TemplateView, DetailView

from products.models import Product


# Create your views here.
class ProductList(ListView):
    model = Product
    context_object_name = 'products'
    template_name = 'products/product_list.html'
    paginate_by = 6

class GuidesReceiptView(TemplateView):
    template_name = 'products/guides-recipes.html'


class ProductDetailsView(DetailView):
    template_name = 'products/product_detail.html'
    model = Product
    queryset = (Product.objects
                .select_related('category')
                .prefetch_related('reviews__owner'))




    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        product = self.object
        context['average_rating'] = product.get_rating()
        full_stars, has_half_star, empty_stars = product.get_stars()
        context['full_stars'] = range(full_stars)
        context['has_half_star'] = has_half_star
        context['empty_stars'] = range(empty_stars)
        context['reviews_count'] = product.reviews.count()
        for review in product.reviews.all():
            review.stars = range(review.rating)
            review.empty_stars = range(5-review.rating)

        return context
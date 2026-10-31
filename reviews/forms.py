from django import forms

from orders.models import OrderItem, OrderStatus
from reviews.models import Review


class ReviewForm(forms.ModelForm):
    class Meta:
        model = Review
        fields = ['rating', 'heading', 'comment']
        labels = {'rating': 'Оценка от 1 до 5', 'heading': 'Заголовок', 'comment': 'Отзыв'}
        widgets = {'comment': forms.Textarea(attrs={'rows': 4})}

    def clean(self):
        data = super().clean()
        review = self.instance
        if not OrderItem.objects.filter(
                order__owner=review.owner, order__status=OrderStatus.DELIVERED,
                product=review.product).exists():
            raise forms.ValidationError('Оставить отзыв можно только после получения купленного товара.')
        if Review.objects.filter(owner=review.owner, product=review.product).exists():
            raise forms.ValidationError('Вы уже оставили отзыв на этот товар.')
        return data

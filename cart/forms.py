from django import forms
from .models import Cart, CartItem
from products.models import Product


class AddToCartForm(forms.Form):
    """Форма для добавления товара в корзину"""

    product_id = forms.IntegerField(widget=forms.HiddenInput())
    quantity = forms.IntegerField(
        min_value=1,
        initial=1,
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'min': 1,
            'max': 99
        })
    )

    def clean(self):
        cleaned_data = super().clean()
        product_id = cleaned_data.get('product_id')
        quantity = cleaned_data.get('quantity')

        if product_id and quantity:
            try:
                product = Product.objects.get(id=product_id, is_active=True)
                if product.stock_quantity < quantity:
                    raise forms.ValidationError(
                        f'Недостаточно товара на складе. Доступно: {product.stock_quantity}'
                    )
                cleaned_data['product'] = product
            except Product.DoesNotExist:
                raise forms.ValidationError('Товар не найден')

        return cleaned_data


class UpdateCartItemForm(forms.Form):
    """Форма для изменения количества товара в корзине"""

    cart_item_id = forms.IntegerField(widget=forms.HiddenInput())
    quantity = forms.IntegerField(
        min_value=1,
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'min': 1
        })
    )

    def clean(self):
        cleaned_data = super().clean()
        cart_item_id = cleaned_data.get('cart_item_id')
        quantity = cleaned_data.get('quantity')

        if cart_item_id and quantity:
            try:
                cart_item = CartItem.objects.get(id=cart_item_id)
                if cart_item.product.stock_quantity < quantity:
                    raise forms.ValidationError(
                        f'Недостаточно товара на складе. Доступно: {cart_item.product.stock_quantity}'
                    )
            except CartItem.DoesNotExist:
                raise forms.ValidationError('Позиция корзины не найдена')

        return cleaned_data
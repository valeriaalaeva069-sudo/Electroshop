from django import forms
from .models import Order, OrderStatus
from cart.models import Cart


class OrderCreateForm(forms.Form):
    """Форма для оформления заказа"""

    city = forms.CharField(
        max_length=100,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Город'
        })
    )

    address = forms.CharField(
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 3,
            'placeholder': 'Улица, дом, квартира'
        })
    )

    postal_code = forms.CharField(
        max_length=20,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Почтовый индекс'
        })
    )

    delivery_method = forms.ChoiceField(
        choices=Order.DELIVERY_CHOICES,
        widget=forms.Select(attrs={
            'class': 'form-control'
        })
    )

    payment_method = forms.ChoiceField(
        choices=Order.PAYMENT_CHOICES,
        widget=forms.Select(attrs={
            'class': 'form-control'
        })
    )

    comment = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 2,
            'placeholder': 'Комментарий к заказу'
        })
    )

    items = forms.ModelMultipleChoiceField(
        queryset=None,
        required=False,
        widget=forms.CheckboxSelectMultiple,
        label='Выберите товары для оформления'
    )

    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)

        if user:
            try:
                cart = Cart.objects.get(user=user)
                self.fields['items'].queryset = cart.items.all()
            except Cart.DoesNotExist:
                self.fields['items'].queryset = Cart.objects.none()

    def clean_items(self):
        items = self.cleaned_data.get('items')
        if not items:
            raise forms.ValidationError('Выберите хотя бы один товар')
        return items


class OrderStatusForm(forms.ModelForm):
    """Форма для изменения статуса заказа (админ)"""

    class Meta:
        model = Order
        fields = ['status', 'tracking_number', 'comment']
        widgets = {
            'status': forms.Select(attrs={
                'class': 'form-control'
            }),
            'tracking_number': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Трек-номер доставки'
            }),
            'comment': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 2,
                'placeholder': 'Комментарий к изменению статуса'
            }),
        }


class OrderStatusCreateForm(forms.ModelForm):
    """Форма для создания статуса заказа"""

    class Meta:
        model = OrderStatus
        fields = ['name', 'color', 'icon', 'order', 'is_active']
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Название статуса'
            }),
            'color': forms.TextInput(attrs={
                'class': 'form-control',
                'type': 'color'
            }),
            'icon': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Иконка (например, 📦)'
            }),
            'order': forms.NumberInput(attrs={
                'class': 'form-control',
                'placeholder': 'Порядок отображения'
            }),
            'is_active': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            }),
        }
from django import forms
from .models import Product, Category, Brand


class ProductForm(forms.ModelForm):
    """Форма для создания и редактирования товара"""

    class Meta:
        model = Product
        fields = [
            'name', 'slug', 'category', 'brand',
            'price', 'stock_quantity',
            'description', 'specifications',
            'main_image', 'is_active', 'is_featured'
        ]
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Название товара'
            }),
            'slug': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'URL-имя (латиницей)'
            }),
            'category': forms.Select(attrs={
                'class': 'form-control'
            }),
            'brand': forms.Select(attrs={
                'class': 'form-control'
            }),
            'price': forms.NumberInput(attrs={
                'class': 'form-control',
                'placeholder': 'Цена в рублях',
                'step': '0.01'
            }),
            'stock_quantity': forms.NumberInput(attrs={
                'class': 'form-control',
                'placeholder': 'Количество на складе'
            }),
            'description': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 5,
                'placeholder': 'Подробное описание товара'
            }),
            'specifications': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'JSON с характеристиками: {"color": "black", "weight": "100g"}'
            }),
            'main_image': forms.FileInput(attrs={
                'class': 'form-control'
            }),
            'is_active': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            }),
            'is_featured': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            }),
        }


class CategoryForm(forms.ModelForm):
    """Форма для создания и редактирования категории"""

    class Meta:
        model = Category
        fields = ['name', 'slug', 'parent', 'image', 'description', 'is_active']
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Название категории'
            }),
            'slug': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'URL-имя (латиницей)'
            }),
            'parent': forms.Select(attrs={
                'class': 'form-control'
            }),
            'image': forms.FileInput(attrs={
                'class': 'form-control'
            }),
            'description': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Описание категории'
            }),
            'is_active': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            }),
        }


class BrandForm(forms.ModelForm):
    """Форма для создания и редактирования бренда"""

    class Meta:
        model = Brand
        fields = ['name', 'slug', 'logo', 'is_active']
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Название бренда'
            }),
            'slug': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'URL-имя (латиницей)'
            }),
            'logo': forms.FileInput(attrs={
                'class': 'form-control'
            }),
            'is_active': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            }),
        }
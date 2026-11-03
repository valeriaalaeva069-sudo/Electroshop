from django.contrib import admin
from .models import Cart, CartItem


class CartItemInline(admin.TabularInline):
    model = CartItem
    extra = 0
    readonly_fields = ['added_at']
    autocomplete_fields = ['product']


@admin.register(Cart)
class CartAdmin(admin.ModelAdmin):
    list_display = ['user', 'total_items', 'updated_at']
    search_fields = ['user__email']
    readonly_fields = ['created_at', 'updated_at']
    inlines = [CartItemInline]

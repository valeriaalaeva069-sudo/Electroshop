from rest_framework import generics, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from .models import Cart, CartItem
from .serializers import (
    CartSerializer,
    CartItemSerializer,
    AddToCartSerializer,
    UpdateCartItemSerializer,
)


class CartDetailView(generics.RetrieveAPIView):
    """Получение корзины текущего пользователя"""
    permission_classes = [IsAuthenticated]
    serializer_class = CartSerializer

    def get_object(self):
        cart, created = Cart.objects.get_or_create(user=self.request.user)
        # одним запросом подтягиваем товары, категории и бренды
        return Cart.objects.prefetch_related(
            'items__product__category', 'items__product__brand'
        ).get(pk=cart.pk)


class CartAddItemView(generics.CreateAPIView):
    """Добавление товара в корзину"""
    permission_classes = [IsAuthenticated]
    serializer_class = AddToCartSerializer

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        product = serializer.validated_data['product']
        quantity = serializer.validated_data['quantity']

        cart, created = Cart.objects.get_or_create(user=request.user)
        cart_item, created = CartItem.objects.get_or_create(
            cart=cart,
            product=product,
            defaults={'quantity': quantity}
        )

        if not created:
            cart_item.quantity += quantity
            if cart_item.quantity > product.stock_quantity:
                return Response(
                    {'error': f'Недостаточно товара. Доступно: {product.stock_quantity}'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            cart_item.save()

        return Response(
            CartItemSerializer(cart_item).data,
            status=status.HTTP_201_CREATED
        )


class CartUpdateItemView(generics.UpdateAPIView):
    """Изменение количества товара в корзине"""
    permission_classes = [IsAuthenticated]
    serializer_class = UpdateCartItemSerializer

    def get_queryset(self):
        return CartItem.objects.filter(cart__user=self.request.user)

    def update(self, request, *args, **kwargs):
        cart_item = self.get_object()
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        quantity = serializer.validated_data['quantity']

        if quantity <= 0:
            cart_item.delete()
            return Response(
                {'message': 'Товар удалён из корзины'},
                status=status.HTTP_200_OK
            )

        if quantity > cart_item.product.stock_quantity:
            return Response(
                {'error': f'Недостаточно товара. Доступно: {cart_item.product.stock_quantity}'},
                status=status.HTTP_400_BAD_REQUEST
            )

        cart_item.quantity = quantity
        cart_item.save()

        return Response(CartItemSerializer(cart_item).data)


class CartRemoveItemView(generics.DestroyAPIView):
    """Удаление товара из корзины"""
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return CartItem.objects.filter(cart__user=self.request.user)

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        self.perform_destroy(instance)
        return Response(
            {'message': 'Товар удалён из корзины'},
            status=status.HTTP_200_OK
        )


class CartClearView(generics.GenericAPIView):
    """Полная очистка корзины"""
    permission_classes = [IsAuthenticated]

    def post(self, request):
        cart, _ = Cart.objects.get_or_create(user=request.user)
        cart.clear()
        return Response(
            {'message': 'Корзина очищена'},
            status=status.HTTP_200_OK
        )

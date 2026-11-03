from django.http import HttpResponse
from django.shortcuts import render


def index(request):
    return render(request, 'index.html')


def login_page(request):
    return render(request, 'login.html')


def register_page(request):
    return render(request, 'register.html')


def cart_page(request):
    return render(request, 'cart.html')


def checkout_page(request):
    return render(request, 'checkout.html')


def orders_page(request):
    return render(request, 'orders.html')


def profile_page(request):
    return render(request, 'profile.html')


def product_detail_page(request, slug):
    return render(request, 'product_detail.html', {'slug': slug})


def payment_page(request, order_id):
    return render(request, 'payment.html', {'order_id': order_id})


def order_success_page(request, order_id):
    return render(request, 'order_success.html', {'order_id': order_id})


def password_reset_page(request):
    return render(request, 'password_reset.html')


def password_reset_confirm_page(request):
    return render(request, 'password_reset_confirm.html')


def admin_panel(request):
    return render(request, 'admin_panel.html')

def contacts_page(request):
    return render(request, 'contacts.html')


def page_not_found(request, exception=None):
    """Страница 404 (работает при DEBUG=False) с контактами для связи."""
    return render(request, 'error.html', {
        'code': 404, 'heading': 'Страница не найдена',
        'text': 'Такой страницы нет, или она была удалена.',
    }, status=404)


def server_error(request):
    """Страница 500 с контактами; если не получилось отрисовать шаблон — простой текст."""
    try:
        return render(request, 'error.html', {
            'code': 500, 'heading': 'Ошибка на сервере',
            'text': 'Мы уже знаем о проблеме. Попробуйте обновить страницу через несколько минут.',
        }, status=500)
    except Exception:
        return HttpResponse('Ошибка на сервере. Попробуйте позже.', status=500, content_type='text/plain; charset=utf-8')

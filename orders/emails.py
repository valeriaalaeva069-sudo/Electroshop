import logging

from django.core.mail import EmailMultiAlternatives
from django.conf import settings
from django.utils.html import escape

from core.models import SiteSettings

logger = logging.getLogger(__name__)


def send_order_confirmation_email(order):
    """Отправляет письмо-подтверждение заказа на email покупателя.

    Никогда не роняет вызывающий код: если SMTP не настроен или недоступен,
    просто пишет предупреждение в лог и работа сайта продолжается как обычно.
    """
    try:
        if not settings.EMAIL_HOST_USER or not settings.EMAIL_HOST_PASSWORD:
            logger.warning('EMAIL_HOST_USER/EMAIL_HOST_PASSWORD не заданы — письмо не отправлено')
            return

        items = order.items.all()
        site_name = SiteSettings.load().site_name

        text_lines = '\n'.join(
            f'  - {item.product_name} x {item.quantity} - {item.price * item.quantity:.2f} руб.'
            for item in items
        )

        subject = f'Заказ № {order.order_number} оформлен'

        text_body = (
            f'Здравствуйте, {order.user.full_name}!\n\n'
            f'Спасибо за заказ в {site_name}.\n\n'
            f'Номер заказа: {order.order_number}\n'
            f'Товары:\n{text_lines}\n\n'
            f'Доставка: {order.get_delivery_method_display()} - {order.delivery_cost} руб.\n'
            f'Итого к оплате: {order.total_amount} руб.\n\n'
            f'Адрес доставки: {order.city}, {order.address}\n\n'
            f'Следить за статусом заказа можно в личном кабинете на сайте.\n\n'
            f'Спасибо, что выбрали {site_name}!'
        )

        items_html = ''.join(
            f'<tr>'
            f'<td style="padding:6px 10px;border-bottom:1px solid #eee;">{escape(item.product_name)}</td>'
            f'<td style="padding:6px 10px;border-bottom:1px solid #eee;text-align:center;">× {item.quantity}</td>'
            f'<td style="padding:6px 10px;border-bottom:1px solid #eee;text-align:right;">{item.price * item.quantity:.2f} ₽</td>'
            f'</tr>'
            for item in items
        )

        html_body = f'''
        <div style="font-family:'Segoe UI', Arial, sans-serif; max-width:600px; margin:0 auto;">
            <div style="background:linear-gradient(135deg,#2c3e50,#3498db);color:white;padding:25px;border-radius:10px 10px 0 0;text-align:center;">
                <h1 style="margin:0;font-size:22px;">{escape(site_name)}</h1>
            </div>
            <div style="padding:25px;background:#f9fafb;border:1px solid #eee;border-top:none;border-radius:0 0 10px 10px;">
                <h2 style="color:#2c3e50;margin-top:0;">Спасибо за заказ, {escape(order.user.full_name)}!</h2>
                <p style="color:#555;">Номер заказа: <b>{order.order_number}</b></p>
                <table style="width:100%;border-collapse:collapse;background:white;border-radius:8px;overflow:hidden;">
                    {items_html}
                </table>
                <p style="margin-top:15px;color:#555;">Доставка: {order.get_delivery_method_display()} — {order.delivery_cost} ₽</p>
                <p style="font-size:18px;font-weight:bold;color:#e74c3c;">Итого: {order.total_amount} ₽</p>
                <p style="color:#555;">Адрес доставки: {escape(order.city)}, {escape(order.address)}</p>
                <p style="color:#95a5a6;font-size:13px;margin-top:25px;">Следить за статусом заказа можно в личном кабинете на сайте.</p>
            </div>
        </div>
        '''

        msg = EmailMultiAlternatives(
            subject=subject,
            body=text_body,
            from_email=settings.DEFAULT_FROM_EMAIL,
            to=[order.user.email],
        )
        msg.attach_alternative(html_body, 'text/html')
        msg.send(fail_silently=False)

        logger.info(f'Письмо с подтверждением заказа {order.order_number} отправлено на {order.user.email}')

    except Exception as e:
        logger.error(f'Не удалось отправить письмо с подтверждением заказа {order.order_number}: {type(e).__name__}: {e}')

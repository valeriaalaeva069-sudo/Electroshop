"""Генерация PDF-чека по заказу (reportlab)."""
from io import BytesIO

from django.conf import settings
from django.utils import timezone
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle
from xml.sax.saxutils import escape

from core.models import SiteSettings

FONT = 'ReceiptSans'
FONT_BOLD = 'ReceiptSans-Bold'
_fonts_ready = False


def _register_fonts():
    """Шрифт лежит в проекте (static/fonts), чтобы кириллица работала на любом компьютере."""
    global _fonts_ready
    if _fonts_ready:
        return
    fonts_dir = settings.BASE_DIR / 'static' / 'fonts'
    pdfmetrics.registerFont(TTFont(FONT, str(fonts_dir / 'DejaVuSans.ttf')))
    pdfmetrics.registerFont(TTFont(FONT_BOLD, str(fonts_dir / 'DejaVuSans-Bold.ttf')))
    pdfmetrics.registerFontFamily(FONT, normal=FONT, bold=FONT_BOLD)
    _fonts_ready = True


def _money(value):
    return f'{value:,.2f}'.replace(',', ' ').replace('.', ',') + ' ₽'


def build_receipt_pdf(order):
    """Возвращает bytes PDF-чека. Для оплаченного заказа — чек об оплате,
    для остальных — чек-подтверждение заказа с пометкой «оплата при получении»."""
    _register_fonts()
    site_name = SiteSettings.load().site_name
    payment = getattr(order, 'payment', None)
    paid = bool(order.payment_status)

    s = lambda **kw: ParagraphStyle('x', **{'fontName': FONT, **kw})
    title = s(fontSize=18, leading=22, fontName=FONT_BOLD, textColor=colors.HexColor('#2c3e50'))
    sub = s(fontSize=10, leading=14, textColor=colors.HexColor('#7f8c8d'))
    text = s(fontSize=10, leading=14)
    cell = s(fontSize=9.5, leading=12)

    buf = BytesIO()
    doc = SimpleDocTemplate(
        buf, pagesize=A4, leftMargin=20 * mm, rightMargin=20 * mm,
        topMargin=18 * mm, bottomMargin=18 * mm,
        title=f'Чек по заказу {order.order_number}', author=site_name,
    )

    story = [
        Paragraph(escape(site_name), title),
        Paragraph('Чек об оплате' if paid else 'Чек заказа', sub),
        Spacer(1, 6 * mm),
    ]

    created = timezone.localtime(order.created_at).strftime('%d.%m.%Y %H:%M')
    info = [
        ['Заказ №', order.order_number],
        ['Дата оформления', created],
        ['Покупатель', order.user.full_name],
        ['Адрес доставки', f'{order.city}, {order.address}'],
        ['Доставка', order.get_delivery_method_display()],
        ['Способ оплаты', order.get_payment_method_display()],
    ]
    if paid and payment is not None and payment.transaction_id:
        info.append(['Транзакция', payment.transaction_id])
    info_rows = [[Paragraph(f'<font color="#7f8c8d">{escape(k)}</font>', cell),
                  Paragraph(escape(str(v)), cell)] for k, v in info]
    t = Table(info_rows, colWidths=[40 * mm, 130 * mm])
    t.setStyle(TableStyle([('VALIGN', (0, 0), (-1, -1), 'TOP'),
                           ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
                           ('TOPPADDING', (0, 0), (-1, -1), 3)]))
    story += [t, Spacer(1, 6 * mm)]

    head = [Paragraph(f'<b>{h}</b>', cell) for h in ('Товар', 'Цена', 'Кол-во', 'Сумма')]
    rows = [head]
    for item in order.items.all():
        rows.append([
            Paragraph(escape(item.product_name), cell),
            Paragraph(_money(item.price), cell),
            Paragraph(str(item.quantity), cell),
            Paragraph(_money(item.price * item.quantity), cell),
        ])
    rows.append([Paragraph('Доставка', cell), '', '', Paragraph(_money(order.delivery_cost), cell)])
    items_table = Table(rows, colWidths=[85 * mm, 30 * mm, 20 * mm, 35 * mm], repeatRows=1)
    last = len(rows) - 1
    items_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#ecf0f1')),
        ('LINEBELOW', (0, 0), (-1, last - 1), 0.4, colors.HexColor('#dfe6e9')),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('TOPPADDING', (0, 0), (-1, -1), 5),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
    ]))
    story += [items_table, Spacer(1, 5 * mm)]

    total_style = s(fontSize=14, leading=18, fontName=FONT_BOLD, alignment=2)
    story.append(Paragraph(f'Итого: {_money(order.total_amount)}', total_style))
    story.append(Spacer(1, 2 * mm))
    if paid:
        note = s(fontSize=11, leading=14, fontName=FONT_BOLD, alignment=2, textColor=colors.HexColor('#27ae60'))
        story.append(Paragraph('ОПЛАЧЕНО', note))
    else:
        note = s(fontSize=10, leading=14, alignment=2, textColor=colors.HexColor('#e67e22'))
        story.append(Paragraph('Оплата при получении', note))
    story += [Spacer(1, 12 * mm),
              Paragraph(f'Спасибо, что выбрали {escape(site_name)}!', sub)]

    doc.build(story)
    return buf.getvalue()

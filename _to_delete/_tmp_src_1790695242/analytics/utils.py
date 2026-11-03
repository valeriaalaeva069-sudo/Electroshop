import io
import os
from datetime import datetime, timedelta
from decimal import Decimal

from django.db.models import Sum, Count, Q, F
from django.utils import timezone
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm, mm
from reportlab.platypus import (
    SimpleDocTemplate, Table, TableStyle, Paragraph,
    Spacer, PageBreak
)
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

from orders.models import Order, OrderItem, OrderStatus
from products.models import Product, Category
from users.models import CustomUser


# ============================================
# ШРИФТ С ПОДДЕРЖКОЙ КИРИЛЛИЦЫ ДЛЯ PDF
# ============================================
# Встроенные шрифты reportlab (Helvetica и т.д.) не содержат кириллицу,
# поэтому русский текст в PDF без регистрации TTF-шрифта будет пустым/битым.
# Пытаемся найти системный шрифт с кириллицей (на Windows почти всегда есть Arial).

CYRILLIC_FONT = 'Helvetica'
CYRILLIC_FONT_BOLD = 'Helvetica-Bold'

_FONT_CANDIDATES = [
    (r'C:\Windows\Fonts\arial.ttf', r'C:\Windows\Fonts\arialbd.ttf'),
    (r'C:\Windows\Fonts\calibri.ttf', r'C:\Windows\Fonts\calibrib.ttf'),
    ('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf', '/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf'),
    ('/System/Library/Fonts/Supplemental/Arial.ttf', '/System/Library/Fonts/Supplemental/Arial Bold.ttf'),
]

for _regular_path, _bold_path in _FONT_CANDIDATES:
    if os.path.exists(_regular_path):
        try:
            pdfmetrics.registerFont(TTFont('ReportCyrillic', _regular_path))
            CYRILLIC_FONT = 'ReportCyrillic'
            if os.path.exists(_bold_path):
                pdfmetrics.registerFont(TTFont('ReportCyrillic-Bold', _bold_path))
                CYRILLIC_FONT_BOLD = 'ReportCyrillic-Bold'
            else:
                CYRILLIC_FONT_BOLD = CYRILLIC_FONT
            break
        except Exception:
            continue


def get_date_range(period, start_date=None, end_date=None):
    """Возвращает диапазон дат по периоду"""
    today = timezone.now().date()

    if period == 'today':
        return today, today
    elif period == 'week':
        return today - timedelta(days=7), today
    elif period == 'month':
        return today - timedelta(days=30), today
    elif period == 'year':
        return today - timedelta(days=365), today
    elif period == 'custom' and start_date and end_date:
        return start_date, end_date
    else:
        return today - timedelta(days=30), today


def get_dashboard_stats(start_date=None, end_date=None):
    """Возвращает общую статистику для дашборда"""
    today = timezone.now().date()

    # Базовые метрики
    orders = Order.objects.all()
    if start_date and end_date:
        orders = orders.filter(created_at__date__gte=start_date, created_at__date__lte=end_date)

    total_revenue = orders.exclude(status__name='Отменён').aggregate(total=Sum('total_amount'))['total'] or Decimal('0')
    total_orders = orders.count()

    orders_today = Order.objects.filter(created_at__date=today).count()
    revenue_today = Order.objects.filter(
        created_at__date=today
    ).exclude(status__name='Отменён').aggregate(total=Sum('total_amount'))['total'] or Decimal('0')

    # Статусы
    try:
        pending_status = OrderStatus.objects.get(name='Оформлен')
        pending_orders = Order.objects.filter(status=pending_status).count()
    except OrderStatus.DoesNotExist:
        pending_orders = 0

    try:
        completed_status = OrderStatus.objects.get(name='Получен')
        completed_orders = Order.objects.filter(status=completed_status).count()
    except OrderStatus.DoesNotExist:
        completed_orders = 0

    return {
        'total_revenue': total_revenue,
        'total_orders': total_orders,
        'total_users': CustomUser.objects.filter(is_active=True).count(),
        'total_products': Product.objects.filter(is_active=True).count(),
        'orders_today': orders_today,
        'revenue_today': revenue_today,
        'pending_orders': pending_orders,
        'completed_orders': completed_orders,
    }


def get_revenue_by_period(period='month', start_date=None, end_date=None):
    """Возвращает выручку по дням/неделям/месяцам"""
    today = timezone.now().date()

    if period == 'week':
        start = today - timedelta(days=6)
        group_by = 'day'
    elif period == 'month':
        start = today - timedelta(days=29)
        group_by = 'day'
    elif period == 'year':
        start = today - timedelta(days=364)
        group_by = 'month'
    elif period == 'custom' and start_date and end_date:
        start = start_date
        end = end_date
        group_by = 'day'
    else:
        start = today - timedelta(days=29)
        group_by = 'day'

    end = end_date if (period == 'custom' and end_date) else today

    orders = Order.objects.filter(
        created_at__date__gte=start,
        created_at__date__lte=end
    )

    result = []

    if group_by == 'day':
        current = start
        while current <= end:
            day_orders = orders.filter(created_at__date=current)
            revenue = day_orders.exclude(status__name='Отменён').aggregate(total=Sum('total_amount'))['total'] or Decimal('0')
            result.append({
                'period': current.strftime('%d.%m.%Y'),
                'revenue': revenue,
                'orders_count': day_orders.count(),
            })
            current += timedelta(days=1)
    else:  # month
        from collections import OrderedDict
        months = OrderedDict()
        current = start
        while current <= end:
            key = current.strftime('%m.%Y')
            if key not in months:
                months[key] = {'revenue': Decimal('0'), 'orders_count': 0}
            current += timedelta(days=1)

        for order in orders.select_related('status'):
            key = order.created_at.strftime('%m.%Y')
            if key in months:
                if order.status.name != 'Отменён':
                    months[key]['revenue'] += order.total_amount
                months[key]['orders_count'] += 1

        for key, data in months.items():
            result.append({
                'period': key,
                'revenue': data['revenue'],
                'orders_count': data['orders_count'],
            })

    return result


def get_top_products(limit=10, start_date=None, end_date=None):
    """Возвращает топ-N популярных товаров"""
    order_items = OrderItem.objects.all()

    if start_date and end_date:
        order_items = order_items.filter(
            order__created_at__date__gte=start_date,
            order__created_at__date__lte=end_date
        )

    top = order_items.values(
        'product_id',
        'product_name',
    ).annotate(
        total_sold=Sum('quantity'),
        total_revenue=Sum(F('price') * F('quantity'))
    ).order_by('-total_sold')[:limit]

    result = []
    for item in top:
        product = None
        category_name = '—'
        try:
            product = Product.objects.get(id=item['product_id'])
            category_name = product.category.name
        except Product.DoesNotExist:
            pass

        result.append({
            'product_id': item['product_id'],
            'product_name': item['product_name'],
            'category_name': category_name,
            'total_sold': item['total_sold'],
            'total_revenue': item['total_revenue'],
        })

    return result


def get_order_status_stats():
    """Статистика по статусам заказов"""
    statuses = OrderStatus.objects.filter(is_active=True).order_by('order')
    total = Order.objects.count()

    result = []
    for status in statuses:
        count = Order.objects.filter(status=status).count()
        percentage = (count / total * 100) if total > 0 else 0
        result.append({
            'status_name': status.name,
            'status_color': status.color,
            'count': count,
            'percentage': round(percentage, 2),
        })

    return result


def get_category_stats():
    """Статистика по категориям"""
    categories = Category.objects.filter(is_active=True)
    result = []

    for category in categories:
        products = Product.objects.filter(category=category)
        order_items = OrderItem.objects.filter(product__category=category)

        total_sold = order_items.aggregate(total=Sum('quantity'))['total'] or 0
        total_revenue = order_items.aggregate(
            total=Sum(F('price') * F('quantity'))
        )['total'] or Decimal('0')

        result.append({
            'category_name': category.name,
            'products_count': products.count(),
            'total_sold': total_sold,
            'total_revenue': total_revenue,
        })

    return result


# ============================================
# ЭКСПОРТ В EXCEL
# ============================================

def generate_excel_report(start_date, end_date):
    """Генерирует Excel-отчёт по заказам за период"""
    wb = Workbook()

    # ===== Стили =====
    header_font = Font(bold=True, color='FFFFFF', size=12)
    header_fill = PatternFill(start_color='2C3E50', end_color='2C3E50', fill_type='solid')
    title_font = Font(bold=True, size=16, color='2C3E50')
    border = Border(
        left=Side(style='thin'),
        right=Side(style='thin'),
        top=Side(style='thin'),
        bottom=Side(style='thin')
    )
    center = Alignment(horizontal='center', vertical='center')

    # ===== Лист 1: Сводка =====
    ws = wb.active
    ws.title = 'Сводка'

    ws['A1'] = 'Отчёт по продажам'
    ws['A1'].font = title_font
    ws.merge_cells('A1:D1')

    ws['A2'] = f'Период: {start_date.strftime("%d.%m.%Y")} — {end_date.strftime("%d.%m.%Y")}'
    ws['A2'].font = Font(italic=True, size=11)
    ws.merge_cells('A2:D2')

    # Метрики
    stats = get_dashboard_stats(start_date, end_date)

    row = 4
    ws.cell(row=row, column=1, value='Показатель').font = header_font
    ws.cell(row=row, column=1).fill = header_fill
    ws.cell(row=row, column=2, value='Значение').font = header_font
    ws.cell(row=row, column=2).fill = header_fill

    metrics = [
        ('Общая выручка', f'{stats["total_revenue"]} ₽'),
        ('Всего заказов', stats['total_orders']),
        ('Пользователей', stats['total_users']),
        ('Товаров в каталоге', stats['total_products']),
        ('Заказов в обработке', stats['pending_orders']),
        ('Завершённых заказов', stats['completed_orders']),
    ]

    for i, (label, value) in enumerate(metrics, start=1):
        ws.cell(row=row + i, column=1, value=label).border = border
        ws.cell(row=row + i, column=2, value=value).border = border

    ws.column_dimensions['A'].width = 30
    ws.column_dimensions['B'].width = 20

    # ===== Лист 2: Заказы =====
    ws2 = wb.create_sheet('Заказы')

    headers = ['№ заказа', 'Дата', 'Покупатель', 'Email', 'Статус', 'Товаров', 'Сумма (₽)']
    for col, header in enumerate(headers, start=1):
        cell = ws2.cell(row=1, column=col, value=header)
        cell.font = header_font
        cell.fill = header_fill
        cell.alignment = center
        cell.border = border

    orders = Order.objects.filter(
        created_at__date__gte=start_date,
        created_at__date__lte=end_date
    ).select_related('user', 'status').order_by('-created_at')

    for row_idx, order in enumerate(orders, start=2):
        ws2.cell(row=row_idx, column=1, value=order.order_number).border = border
        ws2.cell(row=row_idx, column=2, value=order.created_at.strftime('%d.%m.%Y %H:%M')).border = border
        ws2.cell(row=row_idx, column=3, value=order.user.full_name).border = border
        ws2.cell(row=row_idx, column=4, value=order.user.email).border = border
        ws2.cell(row=row_idx, column=5, value=order.status.name).border = border
        ws2.cell(row=row_idx, column=6, value=order.items.count()).border = border
        ws2.cell(row=row_idx, column=7, value=float(order.total_amount)).border = border

    for col, width in zip(['A', 'B', 'C', 'D', 'E', 'F', 'G'], [18, 18, 25, 25, 15, 10, 15]):
        ws2.column_dimensions[col].width = width

    # ===== Лист 3: Топ товаров =====
    ws3 = wb.create_sheet('Топ товаров')

    headers = ['Место', 'Товар', 'Категория', 'Продано (шт)', 'Выручка (₽)']
    for col, header in enumerate(headers, start=1):
        cell = ws3.cell(row=1, column=col, value=header)
        cell.font = header_font
        cell.fill = header_fill
        cell.alignment = center
        cell.border = border

    top_products = get_top_products(limit=20, start_date=start_date, end_date=end_date)
    for row_idx, product in enumerate(top_products, start=2):
        ws3.cell(row=row_idx, column=1, value=row_idx - 1).border = border
        ws3.cell(row=row_idx, column=2, value=product['product_name']).border = border
        ws3.cell(row=row_idx, column=3, value=product['category_name']).border = border
        ws3.cell(row=row_idx, column=4, value=product['total_sold']).border = border
        ws3.cell(row=row_idx, column=5, value=float(product['total_revenue'])).border = border

    for col, width in zip(['A', 'B', 'C', 'D', 'E'], [8, 35, 25, 15, 18]):
        ws3.column_dimensions[col].width = width

    # ===== Лист 4: По категориям =====
    ws4 = wb.create_sheet('Категории')

    headers = ['Категория', 'Товаров', 'Продано', 'Выручка (₽)']
    for col, header in enumerate(headers, start=1):
        cell = ws4.cell(row=1, column=col, value=header)
        cell.font = header_font
        cell.fill = header_fill
        cell.alignment = center
        cell.border = border

    cat_stats = get_category_stats()
    for row_idx, cat in enumerate(cat_stats, start=2):
        ws4.cell(row=row_idx, column=1, value=cat['category_name']).border = border
        ws4.cell(row=row_idx, column=2, value=cat['products_count']).border = border
        ws4.cell(row=row_idx, column=3, value=cat['total_sold']).border = border
        ws4.cell(row=row_idx, column=4, value=float(cat['total_revenue'])).border = border

    for col, width in zip(['A', 'B', 'C', 'D'], [30, 15, 15, 20]):
        ws4.column_dimensions[col].width = width

    # Сохраняем в память
    output = io.BytesIO()
    wb.save(output)
    output.seek(0)
    return output


# ============================================
# ЭКСПОРТ В PDF
# ============================================

def generate_pdf_report(start_date, end_date):
    """Генерирует PDF-отчёт по продажам за период"""
    buffer = io.BytesIO()

    # Создаём документ
    doc = SimpleDocTemplate(
        buffer,
        pagesize=landscape(A4),
        rightMargin=1.5 * cm,
        leftMargin=1.5 * cm,
        topMargin=1.5 * cm,
        bottomMargin=1.5 * cm,
    )

    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontName=CYRILLIC_FONT_BOLD,
        fontSize=20,
        textColor=colors.HexColor('#2C3E50'),
        spaceAfter=20,
        alignment=1,  # центр
    )
    subtitle_style = ParagraphStyle(
        'Subtitle',
        parent=styles['Normal'],
        fontName=CYRILLIC_FONT,
        fontSize=12,
        textColor=colors.grey,
        spaceAfter=20,
        alignment=1,
    )
    h2_style = ParagraphStyle(
        'H2',
        parent=styles['Heading2'],
        fontName=CYRILLIC_FONT_BOLD,
        fontSize=14,
        textColor=colors.HexColor('#2C3E50'),
        spaceAfter=10,
        spaceBefore=15,
    )
    normal_style = ParagraphStyle(
        'CustomNormal',
        parent=styles['Normal'],
        fontName=CYRILLIC_FONT,
    )

    elements = []

    # ===== Заголовок =====
    elements.append(Paragraph('Отчёт по продажам', title_style))
    elements.append(Paragraph(
        f'Период: {start_date.strftime("%d.%m.%Y")} — {end_date.strftime("%d.%m.%Y")}',
        subtitle_style
    ))

    # ===== Сводка =====
    stats = get_dashboard_stats(start_date, end_date)
    elements.append(Paragraph('Общие показатели', h2_style))

    summary_data = [
        ['Показатель', 'Значение'],
        ['Общая выручка', f'{stats["total_revenue"]:,.2f} ₽'],
        ['Всего заказов', str(stats['total_orders'])],
        ['Пользователей', str(stats['total_users'])],
        ['Товаров в каталоге', str(stats['total_products'])],
        ['Заказов в обработке', str(stats['pending_orders'])],
        ['Завершённых заказов', str(stats['completed_orders'])],
    ]

    summary_table = Table(summary_data, colWidths=[8 * cm, 8 * cm])
    summary_table.setStyle(TableStyle([
        ('FONTNAME', (0, 0), (-1, 0), CYRILLIC_FONT_BOLD),
        ('FONTNAME', (0, 1), (-1, -1), CYRILLIC_FONT),
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#2C3E50')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('FONTSIZE', (0, 0), (-1, 0), 12),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
        ('GRID', (0, 0), (-1, -1), 1, colors.grey),
        ('FONTSIZE', (0, 1), (-1, -1), 11),
    ]))
    elements.append(summary_table)

    # ===== Топ товаров =====
    elements.append(Paragraph('Топ-10 популярных товаров', h2_style))

    top_products = get_top_products(limit=10, start_date=start_date, end_date=end_date)

    top_data = [['#', 'Товар', 'Категория', 'Продано', 'Выручка']]
    for i, product in enumerate(top_products, start=1):
        top_data.append([
            str(i),
            product['product_name'][:40],
            product['category_name'][:20],
            str(product['total_sold']),
            f'{product["total_revenue"]:,.2f} ₽',
        ])

    if len(top_data) > 1:
        top_table = Table(top_data, colWidths=[1 * cm, 8 * cm, 5 * cm, 3 * cm, 5 * cm])
        top_table.setStyle(TableStyle([
            ('FONTNAME', (0, 0), (-1, 0), CYRILLIC_FONT_BOLD),
            ('FONTNAME', (0, 1), (-1, -1), CYRILLIC_FONT),
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#2C3E50')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f5f5f5')]),
        ]))
        elements.append(top_table)
    else:
        elements.append(Paragraph('Нет данных за выбранный период', normal_style))

    # ===== Статистика по статусам =====
    elements.append(PageBreak())
    elements.append(Paragraph('Статистика по статусам заказов', h2_style))

    status_stats = get_order_status_stats()
    status_data = [['Статус', 'Количество', 'Процент']]
    for stat in status_stats:
        status_data.append([
            stat['status_name'],
            str(stat['count']),
            f'{stat["percentage"]}%',
        ])

    status_table = Table(status_data, colWidths=[8 * cm, 5 * cm, 5 * cm])
    status_table.setStyle(TableStyle([
        ('FONTNAME', (0, 0), (-1, 0), CYRILLIC_FONT_BOLD),
        ('FONTNAME', (0, 1), (-1, -1), CYRILLIC_FONT),
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#2C3E50')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
        ('ALIGN', (1, 0), (-1, -1), 'CENTER'),
    ]))
    elements.append(status_table)

    # ===== Статистика по категориям =====
    elements.append(Paragraph('Статистика по категориям', h2_style))

    cat_stats = get_category_stats()
    cat_data = [['Категория', 'Товаров', 'Продано', 'Выручка']]
    for cat in cat_stats:
        cat_data.append([
            cat['category_name'][:30],
            str(cat['products_count']),
            str(cat['total_sold']),
            f'{cat["total_revenue"]:,.2f} ₽',
        ])

    cat_table = Table(cat_data, colWidths=[8 * cm, 4 * cm, 4 * cm, 6 * cm])
    cat_table.setStyle(TableStyle([
        ('FONTNAME', (0, 0), (-1, 0), CYRILLIC_FONT_BOLD),
        ('FONTNAME', (0, 1), (-1, -1), CYRILLIC_FONT),
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#2C3E50')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f5f5f5')]),
    ]))
    elements.append(cat_table)

    # Генерируем PDF
    doc.build(elements)
    buffer.seek(0)
    return buffer

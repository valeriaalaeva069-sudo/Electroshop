from datetime import datetime

from django.http import FileResponse
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response
from rest_framework.views import APIView

from users.permissions import IsAdminRole
from . import utils


# ============================================
# РАЗБОР ПАРАМЕТРОВ: кривой ввод — 400 с понятным текстом, а не 500
# ============================================

def parse_date_param(request, name):
    """Дата из query-параметра в формате ГГГГ-ММ-ДД или None"""
    raw = request.query_params.get(name)
    if not raw:
        return None
    try:
        return datetime.strptime(raw, '%Y-%m-%d').date()
    except ValueError:
        raise ValidationError({name: 'Дата должна быть в формате ГГГГ-ММ-ДД'})


def parse_date_range(request):
    """(start_date, end_date) из параметров; проверяет, что начало не позже конца"""
    start_date = parse_date_param(request, 'start_date')
    end_date = parse_date_param(request, 'end_date')
    if start_date and end_date and start_date > end_date:
        raise ValidationError({'start_date': 'Начало периода позже конца'})
    return start_date, end_date


def report_range(request):
    """Период для отчётов: явные даты (обе) или готовый период (?period=month)"""
    start_date, end_date = parse_date_range(request)
    if start_date and end_date:
        return start_date, end_date
    return utils.get_date_range(request.query_params.get('period', 'month'))


class DashboardStatsView(APIView):
    """Общая статистика для дашборда"""
    permission_classes = [IsAdminRole]

    def get(self, request):
        period = request.query_params.get('period', 'month')
        start_date, end_date = parse_date_range(request)

        if period != 'custom':
            start_date, end_date = utils.get_date_range(period)

        stats = utils.get_dashboard_stats(start_date, end_date)
        return Response(stats)


class RevenueByPeriodView(APIView):
    """Выручка по дням/неделям/месяцам"""
    permission_classes = [IsAdminRole]

    def get(self, request):
        period = request.query_params.get('period', 'month')
        start_date, end_date = parse_date_range(request)

        data = utils.get_revenue_by_period(period, start_date, end_date)
        return Response(data)


class TopProductsView(APIView):
    """Топ популярных товаров"""
    permission_classes = [IsAdminRole]

    def get(self, request):
        try:
            limit = int(request.query_params.get('limit', 10))
        except ValueError:
            raise ValidationError({'limit': 'Укажите целое число'})
        limit = max(1, min(limit, 100))
        start_date, end_date = parse_date_range(request)

        data = utils.get_top_products(limit, start_date, end_date)
        return Response(data)


class OrderStatusStatsView(APIView):
    """Статистика по статусам заказов"""
    permission_classes = [IsAdminRole]

    def get(self, request):
        data = utils.get_order_status_stats()
        return Response(data)


class CategoryStatsView(APIView):
    """Статистика по категориям"""
    permission_classes = [IsAdminRole]

    def get(self, request):
        data = utils.get_category_stats()
        return Response(data)


class ExportExcelView(APIView):
    """Экспорт отчёта в Excel"""
    permission_classes = [IsAdminRole]

    def get(self, request):
        start_date, end_date = report_range(request)

        excel_file = utils.generate_excel_report(start_date, end_date)

        filename = f'report_{start_date.strftime("%Y%m%d")}_{end_date.strftime("%Y%m%d")}.xlsx'

        return FileResponse(
            excel_file,
            as_attachment=True,
            filename=filename,
            content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )


class ExportPdfView(APIView):
    """Экспорт отчёта в PDF"""
    permission_classes = [IsAdminRole]

    def get(self, request):
        start_date, end_date = report_range(request)

        pdf_file = utils.generate_pdf_report(start_date, end_date)

        filename = f'report_{start_date.strftime("%Y%m%d")}_{end_date.strftime("%Y%m%d")}.pdf'

        return FileResponse(
            pdf_file,
            as_attachment=True,
            filename=filename,
            content_type='application/pdf'
        )

from datetime import datetime
from django.http import FileResponse
from rest_framework import status

from rest_framework.response import Response
from rest_framework.views import APIView

from users.permissions import IsAdminRole
from .serializers import (
    DashboardStatsSerializer,
    RevenueByPeriodSerializer,
    TopProductSerializer,
    OrderStatusStatsSerializer,
    CategoryStatsSerializer,
)
from . import utils


class DashboardStatsView(APIView):
    """Общая статистика для дашборда"""
    permission_classes = [IsAdminRole]

    def get(self, request):
        period = request.query_params.get('period', 'month')
        start_date = request.query_params.get('start_date')
        end_date = request.query_params.get('end_date')

        if start_date:
            start_date = datetime.strptime(start_date, '%Y-%m-%d').date()
        if end_date:
            end_date = datetime.strptime(end_date, '%Y-%m-%d').date()

        if period != 'custom':
            start_date, end_date = utils.get_date_range(period)

        stats = utils.get_dashboard_stats(start_date, end_date)
        return Response(stats)


class RevenueByPeriodView(APIView):
    """Выручка по дням/неделям/месяцам"""
    permission_classes = [IsAdminRole]

    def get(self, request):
        period = request.query_params.get('period', 'month')
        start_date = request.query_params.get('start_date')
        end_date = request.query_params.get('end_date')

        if start_date:
            start_date = datetime.strptime(start_date, '%Y-%m-%d').date()
        if end_date:
            end_date = datetime.strptime(end_date, '%Y-%m-%d').date()

        data = utils.get_revenue_by_period(period, start_date, end_date)
        return Response(data)


class TopProductsView(APIView):
    """Топ популярных товаров"""
    permission_classes = [IsAdminRole]

    def get(self, request):
        limit = int(request.query_params.get('limit', 10))
        start_date = request.query_params.get('start_date')
        end_date = request.query_params.get('end_date')

        if start_date:
            start_date = datetime.strptime(start_date, '%Y-%m-%d').date()
        if end_date:
            end_date = datetime.strptime(end_date, '%Y-%m-%d').date()

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
        period = request.query_params.get('period', 'month')
        start_date_str = request.query_params.get('start_date')
        end_date_str = request.query_params.get('end_date')

        if start_date_str and end_date_str:
            start_date = datetime.strptime(start_date_str, '%Y-%m-%d').date()
            end_date = datetime.strptime(end_date_str, '%Y-%m-%d').date()
        else:
            start_date, end_date = utils.get_date_range(period)

        excel_file = utils.generate_excel_report(start_date, end_date)

        filename = f'report_{start_date.strftime("%Y%m%d")}_{end_date.strftime("%Y%m%d")}.xlsx'

        response = FileResponse(
            excel_file,
            as_attachment=True,
            filename=filename,
            content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )
        return response


class ExportPdfView(APIView):
    """Экспорт отчёта в PDF"""
    permission_classes = [IsAdminRole]

    def get(self, request):
        period = request.query_params.get('period', 'month')
        start_date_str = request.query_params.get('start_date')
        end_date_str = request.query_params.get('end_date')

        if start_date_str and end_date_str:
            start_date = datetime.strptime(start_date_str, '%Y-%m-%d').date()
            end_date = datetime.strptime(end_date_str, '%Y-%m-%d').date()
        else:
            start_date, end_date = utils.get_date_range(period)

        pdf_file = utils.generate_pdf_report(start_date, end_date)

        filename = f'report_{start_date.strftime("%Y%m%d")}_{end_date.strftime("%Y%m%d")}.pdf'

        response = FileResponse(
            pdf_file,
            as_attachment=True,
            filename=filename,
            content_type='application/pdf'
        )
        return response
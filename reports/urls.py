# reports/urls.py
from django.urls import path
from . import views

app_name = 'reports'

urlpatterns = [
    path('history/', views.report_history_view, name='report_history'),
    path('detail/<int:pk>/', views.report_detail_view, name='report_detail'),
    
    # --- NOVA ROTA DE API PARA POLLING ---
    # Esta URL será chamada pelo JavaScript para verificar o status
    path('api/check_status/<int:pk>/', views.check_report_status_api, name='api_check_report_status'),
]
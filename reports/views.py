# reports/views.py
from django.shortcuts import render, get_object_or_404
from django.contrib.auth.decorators import login_required
from .models import ValuationReport
from django.http import JsonResponse # <-- ADICIONADO
from django.urls import reverse # <-- ADICIONADO
import logging # <-- ADICIONADO

logger = logging.getLogger(__name__) # <-- ADICIONADO

@login_required
def report_history_view(request):
    """
    Exibe a lista de relatórios (histórico) do usuário.
    """
    reports = ValuationReport.objects.filter(user=request.user).order_by('-created_at')
    context = {
        'reports': reports
    }
    return render(request, 'reports/report_history.html', context)

@login_required
def report_detail_view(request, pk):
    """
    Exibe a página de detalhes de um relatório específico.
    Garante que o usuário só possa ver seus próprios relatórios.
    """
    report = get_object_or_404(ValuationReport, pk=pk, user=request.user)
    context = {
        'report': report
    }
    return render(request, 'reports/report_detail.html', context)


# --- NOVA VIEW DE API PARA POLLING ---

@login_required
def check_report_status_api(request, pk):
    """
    Uma API interna para o JavaScript verificar o status de um relatório,
    incluindo o status da geração Gamma.
    """
    try:
        report = ValuationReport.objects.get(pk=pk, user=request.user)
        
        main_status = report.status
        gamma_status = report.result_data.get('gamma_status')
        gamma_url = report.gamma_presentation_url
        
        # O status principal (IA) foi concluído
        if main_status == ValuationReport.StatusChoices.SUCCESS:
            return JsonResponse({
                "status": "SUCCESS",
                "detail_url": reverse('reports:report_detail', kwargs={'pk': report.pk}),
                # Informações do Gamma
                "gamma_status": gamma_status,
                "gamma_url": gamma_url
            })
        elif main_status == ValuationReport.StatusChoices.FAILED:
             return JsonResponse({"status": "FAILED", "gamma_status": gamma_status})
        else:
            # A tarefa principal ainda está PENDING ou PROCESSING
            return JsonResponse({"status": "PROCESSING", "gamma_status": "pending"})
            
    except ValuationReport.DoesNotExist:
        return JsonResponse({"status": "NOT_FOUND"}, status=404)
    except Exception as e:
        logger.error(f"Erro em check_report_status_api: {e}")
        return JsonResponse({"status": "ERROR"}, status=500)
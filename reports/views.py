# reports/views.py
from django.shortcuts import render, get_object_or_404
from django.contrib.auth.decorators import login_required
from .models import ValuationReport
from django.http import JsonResponse, Http404
from django.urls import reverse
import logging # Adicionado logging

# Configura o logger
logger = logging.getLogger(__name__)

@login_required
def report_list_view(request):
    """
    Exibe o histórico de relatórios do usuário logado.
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
    """
    report = get_object_or_404(ValuationReport, pk=pk, user=request.user)
    context = {
        'report': report
    }
    return render(request, 'reports/report_detail.html', context)


# --- API VIEW PARA POLLING ---

@login_required
def check_report_status_api(request, pk):
    """
    API endpoint (JSON) para o JavaScript (polling) verificar o status 
    de um relatório.
    """
    try:
        report = get_object_or_404(ValuationReport, pk=pk, user=request.user)

        # --- CORREÇÃO AQUI ---
        # Verifica se result_data não é None antes de tentar acessá-lo
        if report.result_data:
            gamma_status = report.result_data.get('gamma_status', 'pending')
        
        # Se report.result_data for None, trata como 'failed' ou 'pending'
        # para evitar o crash.
        else:
            # Se o status principal já for FAILED, o gamma_status também é.
            if report.status == ValuationReport.StatusChoices.FAILED:
                 gamma_status = 'failed'
            # Se não, ainda está pendente (ou processando o erro)
            else:
                 gamma_status = 'pending'
        # --- FIM DA CORREÇÃO ---

        data = {
            'status': report.status,
            'gamma_status': gamma_status,
            'gamma_url': report.gamma_presentation_url, # Isso é seguro, pois é None se não existir
            'detail_url': reverse('reports:report_detail', kwargs={'pk': report.pk})
        }
        
        return JsonResponse(data)

    except Http404:
         logger.warning(f"API check_status falhou: Report {pk} não encontrado para user {request.user.pk}")
         return JsonResponse({'status': 'error', 'message': 'Not Found'}, status=404)
    except Exception as e:
         # Captura qualquer outro erro inesperado
         logger.error(f"Erro em check_report_status_api (Report {pk}): {e}", exc_info=True)
         return JsonResponse({'status': 'error', 'message': str(e)}, status=500)
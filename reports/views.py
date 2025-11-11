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
        # Adiciona uma lógica "defensiva" para NUNCA quebrar
        # se report.result_data for None.
        gamma_status = 'pending' # Começa com um padrão seguro
        
        if report.result_data:
            # Só tenta ler .get() se 'result_data' NÃO for None
            gamma_status = report.result_data.get('gamma_status', 'pending')
        
        # Se o report.result_data for None, mas o status geral for FAILED,
        # então o gamma_status também falhou.
        elif report.status == ValuationReport.StatusChoices.FAILED:
             gamma_status = 'failed'
        # --- FIM DA CORREÇÃO ---

        data = {
            'status': report.status,
            'gamma_status': gamma_status, # Usa a variável segura
            'gamma_url': report.gamma_presentation_url,
            'detail_url': reverse('reports:report_detail', kwargs={'pk': report.pk})
        }
        
        return JsonResponse(data)

    except Http404:
         logger.warning(f"API check_status falhou: Report {pk} não encontrado para user {request.user.pk}")
         return JsonResponse({'status': 'error', 'message': 'Not Found'}, status=404)
    except Exception as e:
         # Captura qualquer outro erro inesperado (NUNCA DEIXA O GUNICORN MORRER)
         logger.error(f"Erro inesperado em check_report_status_api (Report {pk}): {e}", exc_info=True)
         # Retorna um erro JSON em vez de quebrar
         return JsonResponse({'status': 'error', 'message': str(e)}, status=500)
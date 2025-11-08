# chatbot/views.py
from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse, HttpRequest
from django.views.decorators.csrf import csrf_exempt
from django.db import transaction
import json
import logging

from reports.models import ValuationReport
from .tasks import process_valuation_request
# ESTA LINHA É ESSENCIAL
from .utils import validate_inputs_backend 

logger = logging.getLogger(__name__)

# O limite de usos (pode ajustar)
MAX_FREE_USES = 5 

@csrf_exempt
@login_required
def calculate_valuation_view(request: HttpRequest):
    if request.method == "POST":
        try:
            data = json.loads(request.body)
            
            # 1. VERIFICAR LIMITE DE USO
            if not request.user.is_superuser and request.user.usage_count >= MAX_FREE_USES:
                return JsonResponse({
                    "message": "Você atingiu o limite de simulações gratuitas."
                }, status=403) # 403 Forbidden

            # 2. VALIDAR OS INPUTS (AQUI ESTÁ O PONTO DE FALHA)
            # Esta função chama o utils.py
            validated_data, error = validate_inputs_backend(data)
            
            # Se o 'utils.py' novo estiver rodando, 'error' será None
            # Se o 'utils.py' antigo estiver rodando, ele vai gerar o erro que você viu.
            if error:
                return JsonResponse({"message": error}, status=400) # 400 Bad Request

            # 3. CRIAR O RELATÓRIO
            with transaction.atomic():
                report = ValuationReport.objects.create(
                    user=request.user,
                    status=ValuationReport.StatusChoices.PENDING,
                    inputs_data=validated_data # Salva os dados validados (24 campos)
                )
            
            # 4. DISPARAR A TAREFA CELERY
            process_valuation_request.delay(report_id=report.id)
            
            return JsonResponse({
                "message": "Sua solicitação foi recebida! Seu relatório está sendo processado. Você será notificado por e-mail e pode verificar o histórico em alguns minutos.",
                "report_id": report.id
            }, status=200)

        except json.JSONDecodeError:
            return JsonResponse({"message": "Corpo da requisição JSON inválido."}, status=400)
        except Exception as e:
            logger.error(f"Erro inesperado em calculate_valuation_view: {e}", exc_info=True)
            return JsonResponse({"message": "Erro interno no servidor."}, status=500)
    
    return JsonResponse({"message": "Método GET não permitido."}, status=405)


@login_required
def dashboard_view(request):
    """Renderiza a página principal do chatbot (dashboard.html)."""
    # Pega os 5 relatórios mais recentes para o "Histórico Recente"
    reports = ValuationReport.objects.filter(user=request.user).order_by('-created_at')[:5]
    context = {
        'reports': reports
    }
    return render(request, 'chatbot/dashboard.html', context)
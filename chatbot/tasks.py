# chatbot/tasks.py
from celery import shared_task
from reports.models import ValuationReport
from django.db.models import F
from .agents import run_analysis_agent
import requests
import time
import logging
from django.conf import settings
from django.apps import apps
import random
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.utils.html import strip_tags

logger = logging.getLogger(__name__)

# --- MAPAS DE CÁLCULO (Nova Lógica) ---
SCORE_MAP = {
    "BAIXO": -1,
    "NÃO CONSIGO AVALIAR": 0,
    "MÉDIO": 1,
    "ALTO": 2,
    "ELEVADO": 3
}

WEIGHTS_MAP = {
    # Peso 1
    "visao_pessoas": 1,
    "nivel_validacao": 1,
    "nivel_equipe": 1,
    "potencial_network": 1,
    # Peso 2
    "diferencial_modelo": 2,
    "possibilidade_escala": 2,
    "pmf": 2,
    "potencial_alcance": 2,
    "nivel_parcerias": 2,
    "estagio_modelo": 2,
    "estagio_prototipo": 2,
    "nivel_analise_financeira": 2,
    "estagio_comercializacao": 2,
    "nivel_faturamento": 2,
    "nivel_lucro": 2,
    # Peso -2
    "possibilidade_copia": -2,
    "potencial_mercado_barreiras": -2,
    "potencial_internacionalizacao": -2,
}

# --- TAREFA PRINCIPAL (MODIFICADA) ---
@shared_task
def process_valuation_request(report_id):
    """
    Tarefa Celery para processar o valuation usando a lógica de planilha
    e disparar a análise da IA e a geração Gamma.
    """
    user = None
    try:
        report = ValuationReport.objects.get(id=report_id)
        report.status = ValuationReport.StatusChoices.PROCESSING
        report.save(update_fields=['status'])

        user = report.user
        inputs = report.inputs_data

        logger.info(f"Iniciando cálculo de planilha para Report {report_id}")
        
        # 1. Obter dados financeiros
        faturamento_mensal = float(inputs.get('faturamento_mensal', 0))
        gastos_variaveis = float(inputs.get('gastos_variaveis', 0))
        gastos_fixos = float(inputs.get('gastos_fixos', 0))
        num_vendas = float(inputs.get('num_vendas', 1) or 1)
        num_prospeccoes = float(inputs.get('num_prospeccoes', 1) or 1)
        setor_atuacao = inputs.get('setor_atuacao', 'Não informado')

        # Etapa 1: Calcular Indicadores Financeiros
        faturamento_anual = faturamento_mensal * 12
        margem_contribuicao_valor = faturamento_mensal - gastos_variaveis
        margem_contribuicao_perc = (margem_contribuicao_valor / faturamento_mensal) if faturamento_mensal > 0 else 0
        ticket_medio = faturamento_mensal / num_vendas
        ponto_equilibrio = gastos_fixos / margem_contribuicao_perc if margem_contribuicao_perc > 0 else 0
        taxa_conversao = (num_vendas / num_prospeccoes) * 100

        indicadores_financeiros = {
            "faturamento_anual": faturamento_anual,
            "faturamento_mensal": faturamento_mensal,
            "margem_contribuicao_valor": margem_contribuicao_valor,
            "margem_contribuicao_perc": margem_contribuicao_perc,
            "ticket_medio": ticket_medio,
            "ponto_equilibrio": ponto_equilibrio,
            "taxa_conversao": taxa_conversao,
        }
        
        # Etapas 2 & 3: Calcular Valor Ponderado
        valores_criterios = []
        soma_valores_criterios = 0

        for crit_id, crit_peso in WEIGHTS_MAP.items():
            resposta_texto = inputs.get(crit_id, "NÃO CONSIGO AVALIAR")
            pontuacao = SCORE_MAP.get(resposta_texto, 0)
            valor_calculado = faturamento_anual * pontuacao * crit_peso
            
            valores_criterios.append({
                "criterio_id": crit_id,
                "resposta": resposta_texto,
                "pontuacao": pontuacao,
                "peso": crit_peso,
                "valor_calculado": valor_calculado
            })
            soma_valores_criterios += valor_calculado

        # Etapa 4: Calcular Valuation Base
        valuation_base = soma_valores_criterios / 18 if valores_criterios else 0

        logger.info(f"Cálculo de planilha concluído para Report {report_id}. Valuation Base: {valuation_base}")

        report.result_data = {
            "indicadores": indicadores_financeiros,
            "valores_criterios": valores_criterios,
            "valuation_base": valuation_base,
            "cenarios": {
                "realista": valuation_base,
                "otimista": None,
                "pessimista": None,
                "setor_crescimento_perc": None
            },
            "pontos_fortes": [],
            "pontos_atencao": [],
            "recomendacao_investidor": "",
            "prompt_gamma": None
        }

        # 5. Chama o Agente Gemini (Modificado)
        logger.info(f"Iniciando chamada ao Agente Gemini (Análise) para Report {report_id}")
        
        # --- MUDANÇA AQUI ---
        # Adicionamos user.razao_social à chamada
        agent_result = run_analysis_agent(
            user_razao_social=user.razao_social,
            setor_atuacao=setor_atuacao,
            indicadores=indicadores_financeiros,
            valores_criterios=valores_criterios,
            valuation_base=valuation_base
        )
        # --- FIM DA MUDANÇA ---
        
        logger.info(f"Agente Gemini (Análise) retornou para Report {report_id}")

        if agent_result and not agent_result.get("error"):
            report.result_data.update(agent_result)
        elif agent_result.get("error"):
            report.result_data["agent_error"] = agent_result.get("error")
            logger.error(f"Agente Gemini (Análise) falhou para Report {report_id}: {agent_result.get('error')}")
        
        report.status = ValuationReport.StatusChoices.SUCCESS
        gamma_generation_triggered = False

        # 7. Atualiza o contador de uso
        if user:
            User = apps.get_model(settings.AUTH_USER_MODEL)
            User.objects.filter(pk=user.pk).update(usage_count=F('usage_count') + 1)
            logger.info(f"Contador de uso incrementado para user {user.pk}")
        else:
            logger.warning(f"Objeto User não disponível para incrementar usage_count no Report {report_id}")

        # 8. Prepara para disparar Gamma
        if report.result_data and report.result_data.get('prompt_gamma'):
            report.result_data['gamma_status'] = 'pending'
            gamma_generation_triggered = True
            logger.info(f"Gamma status definido como 'pending' para Report {report_id}")
        else:
            logger.warning(f"Prompt Gamma não encontrado na resposta do Gemini para Report {report_id}. Geração Gamma não será disparada.")

        # 9. Salva o resultado final e status
        report.save(update_fields=['result_data', 'status'])
        logger.info(f"Resultado final e status salvos para Report {report_id}")

        # 10. Dispara a tarefa Gamma
        if gamma_generation_triggered:
            logger.info(f"Disparando tarefa generate_gamma_presentation para Report {report_id}")
            generate_gamma_presentation.delay(report_id)

    except ValuationReport.DoesNotExist:
        logger.error(f"Erro CRÍTICO: Relatório {report_id} não encontrado em process_valuation_request.")
    except Exception as e:
        logger.exception(f"Erro CRÍTICO inesperado em process_valuation_request para Report {report_id}: {e}")
        try:
            report_qs = ValuationReport.objects.filter(id=report_id)
            if report_qs.exists():
                report_qs.update(
                    status=ValuationReport.StatusChoices.FAILED,
                    result_data={"error": f"Erro inesperado na tarefa Celery: {str(e)}"}
                )
        except Exception as inner_e:
            logger.error(f"Erro ao tentar marcar Report {report_id} como falho após exceção principal: {inner_e}")


# --- TAREFA PARA GERAR APRESENTAÇÃO GAMMA (Sem mudanças) ---
@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def generate_gamma_presentation(self, report_id):
    """
    Tarefa Celery para pegar o prompt do report, chamar a API Gamma,
    fazer polling e salvar a URL da apresentação gerada.
    """
    logger.info(f"Iniciando geração Gamma para Report ID: {report_id} (Tentativa {self.request.retries + 1})")
    report = None
    generation_id = None
    try:
        report = ValuationReport.objects.get(id=report_id)

        prompt_gamma = report.result_data.get('prompt_gamma')
        current_gamma_status = report.result_data.get('gamma_status')

        if not prompt_gamma:
            logger.warning(f"Report {report_id} não possui prompt_gamma. Abortando tarefa Gamma.")
            return
        if current_gamma_status in ['completed', 'failed']:
             logger.warning(f"Report {report_id} já tem gamma_status '{current_gamma_status}'. Abortando tarefa Gamma.")
             return

        gamma_api_key = settings.GAMMA_API_KEY
        if not gamma_api_key:
            logger.error(f"GAMMA_API_KEY não configurada. Marcando falha para Report {report_id}.")
            if report.result_data:
                report.result_data['gamma_status'] = 'failed'
                report.save(update_fields=['result_data'])
            return

        headers = {"X-API-KEY": gamma_api_key, "Content-Type": "application/json"}
        gamma_payload = {"inputText": prompt_gamma, "format": "presentation", "textMode": "generate", "textOptions": {"language": "pt-br"}}
        gamma_endpoint = "https://public-api.gamma.app/v0.2/generations"

        logger.info(f"Enviando prompt para Gamma API para Report {report_id}")
        response_post = requests.post(gamma_endpoint, headers=headers, json=gamma_payload, timeout=30)
        response_post.raise_for_status()
        generation_id = response_post.json().get("generationId")
        if not generation_id:
            logger.error(f"Gamma API não retornou generationId para Report {report_id}. Resposta: {response_post.text}")
            raise ValueError("Gamma API não retornou ID de geração.")

        logger.info(f"Gamma iniciou geração (ID: {generation_id}) para Report {report_id}. Iniciando polling...")
        status_endpoint = f"{gamma_endpoint}/{generation_id}"
        start_time = time.time()
        timeout_seconds = 480

        while (time.time() - start_time) < timeout_seconds:
            time.sleep(30)
            try:
                response_get = requests.get(status_endpoint, headers=headers, timeout=15)
                response_get.raise_for_status()
                status_data = response_get.json()
                current_status = status_data.get('status')
                logger.info(f"Status Gamma para {generation_id} (Report {report_id}): {current_status}")

                if current_status == "completed":
                    gamma_url = status_data.get("gammaUrl")
                    if gamma_url:
                        report.gamma_presentation_url = gamma_url
                        if report.result_data:
                            report.result_data['gamma_status'] = 'completed'
                        report.save(update_fields=['gamma_presentation_url', 'result_data'])
                        logger.info(f"Apresentação Gamma concluída e URL salva para Report {report_id}: {gamma_url}")                        
                        try:
                            send_gamma_report_email.delay(report_id)
                            logger.info(f"Tarefa de envio de email disparada para Report {report_id}")
                        except Exception as e_email:
                            logger.error(f"Falha ao disparar tarefa send_gamma_report_email para Report {report_id}: {e_email}")                        
                        return
                    else:
                        logger.error(f"Status Gamma 'completed' mas sem gammaUrl para {generation_id}. Resposta: {status_data}")
                        raise ValueError("Resposta Gamma 'completed' sem URL.")

                elif current_status in ["failed", "error"]:
                     logger.error(f"Geração Gamma falhou explicitamente para {generation_id}. Status: {current_status}. Resposta: {status_data}")
                     raise ValueError(f"Geração Gamma falhou com status: {current_status}")

            except requests.exceptions.Timeout:
                logger.warning(f"Timeout durante polling do status Gamma para {generation_id}. Tentando novamente...")
            except requests.exceptions.RequestException as poll_error:
                if poll_error.response is not None and 400 <= poll_error.response.status_code < 500:
                     logger.error(f"Erro cliente ({poll_error.response.status_code}) durante polling Gamma para {generation_id}. Abortando retentativas. Erro: {poll_error}")
                     raise
                else:
                     logger.warning(f"Erro de rede/servidor durante polling Gamma para {generation_id}: {poll_error}. Tentando novamente...")
            
        logger.error(f"Timeout geral ({timeout_seconds}s) atingido ao esperar geração Gamma para Report {report_id} (ID: {generation_id}).")
        raise TimeoutError("Geração Gamma demorou demasiado.")

    except ValuationReport.DoesNotExist:
        logger.error(f"Erro CRÍTICO: Report {report_id} não encontrado em generate_gamma_presentation.")
    except (requests.exceptions.RequestException, ValueError, TimeoutError) as e:
        logger.warning(f"Erro tratável ({type(e).__name__}) na tarefa Gamma para Report {report_id}: {e}. Verificando retentativas...")
        try:
            retry_delay = int(random.uniform(2, 5) * (2 ** self.request.retries))
            logger.info(f"Agendando retentativa para Report {report_id} em {retry_delay}s.")
            raise self.retry(exc=e, countdown=retry_delay)
        except self.MaxRetriesExceededError:
             logger.error(f"Máximo de retentativas atingido para Report {report_id} na tarefa Gamma.")
             if report and report.result_data and report.result_data.get('gamma_status') == 'pending':
                 report.result_data['gamma_status'] = 'failed'
                 report.save(update_fields=['result_data'])
    except Exception as e:
        logger.exception(f"Erro INESPERADO na tarefa generate_gamma_presentation para Report {report_id}: {e}")
        if report and report.result_data and report.result_data.get('gamma_status') == 'pending':
            report.result_data['gamma_status'] = 'failed'
            report.save(update_fields=['result_data'])


# --- TAREFA PARA ENVIAR O EMAIL DO RELATÓRIO (Sem mudanças) ---
@shared_task(bind=True, max_retries=3, default_retry_delay=180)
def send_gamma_report_email(self, report_id):
    """
    Envia um email para o usuário com o link da apresentação Gamma concluída.
    """
    logger.info(f"Iniciando envio de email do relatório Gamma para Report ID: {report_id}")
    try:
        report = ValuationReport.objects.get(id=report_id)
        
        if not report.gamma_presentation_url:
            logger.warning(f"Report {report_id} não tem URL Gamma. Abortando envio de email.")
            return

        user = report.user
        subject = render_to_string('users/gamma_report_subject.txt', {'report': report, 'user': user}).strip()
        
        context = {
            'report': report,
            'user': user,
        }
        
        html_message = render_to_string('users/gamma_report_email.html', context)
        plain_message = strip_tags(html_message) 
        
        from_email = settings.DEFAULT_FROM_EMAIL
        to_email = user.email

        msg = EmailMultiAlternatives(subject, plain_message, from_email, [to_email])
        msg.attach_alternative(html_message, "text/html")
        msg.send()

        logger.info(f"Email do relatório Gamma enviado com sucesso para {to_email} (Report {report_id})")

    except ValuationReport.DoesNotExist:
         logger.error(f"Erro CRÍTICO: Report {report_id} não encontrado em send_gamma_report_email.")
    except Exception as e:
        logger.error(f"Erro ao enviar email do relatório Gamma para Report {report_id}: {e}", exc_info=True)
        try:
            raise self.retry(exc=e, countdown=int(random.uniform(2, 5) * (self.request.retries + 1)))
        except self.MaxRetriesExceededError:
             logger.error(f"Máximo de retentativas atingido para envio de email do Report {report_id}.")
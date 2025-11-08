# chatbot/agents.py
import google.generativeai as genai
from django.conf import settings
import json
import logging
import re # Para limpar o JSON

logger = logging.getLogger(__name__)

# --- NOVO AGENTE DE ANÁLISE ---
def run_analysis_agent(
    user_razao_social: str, # <-- ADICIONADO
    setor_atuacao: str, 
    indicadores: dict, 
    valores_criterios: list, 
    valuation_base: float
) -> dict:
    """
    Chama a API Gemini para analisar os dados JÁ CALCULADOS,
    estimar cenários, e gerar o prompt final do Gamma.
    """
    api_key = settings.GEMINI_API_KEY
    if not api_key:
        logger.error("GEMINI_API_KEY não configurada.")
        return {"error": "Configuração da API de IA ausente."}

    genai.configure(api_key=api_key)
    
    # Usando o seu modelo
    model = genai.GenerativeModel('gemini-2.5-flash') 

    # --- Construção do Prompt (Com formatação) ---
    def format_brl(value):
        try:
            return f"R$ {value:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
        except (ValueError, TypeError):
            return f"R$ {value}"

    indicadores_str = "\n".join([f"- {key.replace('_', ' ').title()}: {format_brl(value)}" for key, value in indicadores.items()])
    criterios_str = "\n".join([
        f"- {item['criterio_id'].replace('_', ' ').title()}: {format_brl(item['valor_calculado'])}" 
        for item in valores_criterios
    ])
    valuation_base_str = format_brl(valuation_base)

    # --- PROMPT ATUALIZADO (com nome e foto) ---
    prompt = f"""
    Você é um assistente de análise de dados para uma apresentação de negócios.
    Os cálculos de valuation da empresa '{user_razao_social}' já foram realizados.
    
    Setor da Empresa: {setor_atuacao}
    Valuation Base (Realista) Calculado: {valuation_base_str}
    
    Indicadores Financeiros (Calculados):
    {indicadores_str}
    
    Valores Ponderados por Critério (Calculados):
    {criterios_str}

    Sua tarefa é realizar 4 ações e retornar APENAS um JSON:

    1.  **Estimar Cenários:** Com base no setor '{setor_atuacao}', estime uma taxa de crescimento anual (em %) que você acha realista (ex: "8%"). Com base nessa taxa:
        - Calcule o 'valuation_otimista' = Valuation Base * (1 + taxa_em_decimal)
        - Calcule o 'valuation_pessimista' = Valuation Base * (1 - taxa_em_decimal)
        - Retorne a taxa usada em 'setor_crescimento_perc' (ex: 8.0).
    
    2.  **Analisar Critérios:** Analise a lista de 'Valores Ponderados por Critério':
        - Identifique os 3 a 5 critérios com o MAIOR 'valor_calculado' positivo. Liste-os como 'pontos_fortes'.
        - Identifique TODOS os critérios com 'valor_calculado' NEGATIVO. Liste-os como 'pontos_atencao'.

    3.  **Gerar Texto sobre Investidores:** Com base no faturamento e setor, escreva 1-2 frases para um slide sobre perfis de investidores (ex: Investidor-Anjo, Seed, etc.). Este texto é para fins ilustrativos.
    
    4.  **Gerar Prompt para Gamma:** Crie um prompt de texto otimizado para a API do Gamma (gamma.app) gerar uma apresentação de 7 slides. O prompt deve incluir todos os dados: os 3 cenários de valuation, os indicadores financeiros, os pontos fortes e os pontos de atenção.

    **Formato de Resposta JSON OBRIGATÓRIO (Use R$ e formato X.XXX,XX):**
    {{
        "cenarios": {{
            "realista": {valuation_base},
            "otimista": <valor_numerico_float_otimista>,
            "pessimista": <valor_numerico_float_pessimista>,
            "setor_crescimento_perc": <valor_numerico_float_taxa_usada>
        }},
        "pontos_fortes": [
            {{"criterio": "Nome do Criterio 1", "valor": "R$ XX.XXX,XX"}},
            {{"criterio": "Nome do Criterio 2", "valor": "R$ XX.XXX,XX"}}
        ],
        "pontos_atencao": [
            {{"criterio": "Nome do Criterio 3", "valor": "R$ -XX.XXX,XX"}}
        ],
        "recomendacao_investidor": "Para um negócio neste estágio e faturamento, perfis de investidores que tipicamente se interessam são [Perfil], que buscam [Justificativa].",
        "prompt_gamma": "Crie uma apresentação de 7 slides sobre a análise de valuation da empresa {user_razao_social}. Slide 1: Título 'Análise de Valuation - {user_razao_social}'. Adicione uma foto de capa profissional relacionada ao setor de '{setor_atuacao}'. Slide 2: Indicadores Chave (Faturamento Anual: {format_brl(indicadores.get('faturamento_anual'))}, Margem: {indicadores.get('margem_contribuicao_perc', 0):.1f}%, Ticket Médio: {format_brl(indicadores.get('ticket_medio'))}, Ponto de Equilíbrio: {format_brl(indicadores.get('ponto_equilibrio'))}). Slide 3: Valuation em 3 Cenários (Pessimista: [Valor Pessimista Formatado], Realista: {valuation_base_str}, Otimista: [Valor Otimista Formatado], baseado em {setor_atuacao}). Slide 4: Principais Forças (Liste os 'pontos_fortes'). Slide 5: Pontos de Atenção (Liste os 'pontos_atencao'). Slide 6: Perfil de Investidor (Texto da 'recomendacao_investidor'). Slide 7: Conclusão."
    }}

    **Instruções Adicionais:**
    - Formate TODOS os valores monetários no JSON final (pontos_fortes, pontos_atencao, prompt_gamma) como "R$ X.XXX.XXX,XX".
    - **NÃO inclua nenhuma explicação, comentário ou ```json``` fora do formato JSON.** Sua resposta deve ser *apenas* o JSON solicitado.
    """

    try:
        generation_config = genai.types.GenerationConfig(
            temperature=0.5,
            max_output_tokens=8192
        )
        
        safety_settings = [
            {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_NONE"},
            {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_NONE"},
            {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_NONE"},
            {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_NONE"},
        ]

        logger.debug(f"Enviando prompt de ANÁLISE para Gemini (Empresa: {user_razao_social})")
        response = model.generate_content(
            prompt,
            generation_config=generation_config,
            safety_settings=safety_settings
        )

        if not response.parts:
            block_reason = "Desconhecido"
            try:
                block_reason = response.prompt_feedback.block_reason
            except Exception:
                pass 
            
            logger.error(f"Resposta da IA bloqueada por segurança. Razão: {block_reason}. Finish Reason: {response.candidates[0].finish_reason}")
            return {"error": f"A IA bloqueou a resposta por motivos de segurança ({block_reason})."}

        cleaned_response = response.text.strip()
        
        match = re.search(r'\{.*\}', cleaned_response, re.DOTALL)
        if not match:
            logger.error(f"Resposta da IA não contém JSON. Resposta: {cleaned_response}")
            raise ValueError("Resposta da IA não é um JSON válido.")
        
        json_str = match.group(0)
        
        logger.debug(f"Resposta limpa da IA (JSON): {json_str}")
        result_json = json.loads(json_str)

        required_keys = ["cenarios", "pontos_fortes", "pontos_atencao", "recomendacao_investidor", "prompt_gamma"]
        if not all(key in result_json for key in required_keys):
            logger.error(f"Resposta da IA não contém todas as chaves esperadas. Resposta: {json_str}")
            raise ValueError("Resposta da IA não contém todas as chaves esperadas.")

        if result_json.get("error"):
             logger.error(f"IA retornou erro interno: {result_json.get('error')}")
             return result_json

        logger.info(f"Análise Gemini concluída com sucesso (Empresa: {user_razao_social})")
        return result_json

    except json.JSONDecodeError as e:
        logger.error(f"Erro ao decodificar JSON da resposta da IA: {e}\nResposta recebida: {cleaned_response}")
        return {"error": "Não foi possível processar a resposta da IA (formato inválido). Tente novamente."}
    except Exception as e:
        logger.error(f"Erro inesperado ao chamar a API Gemini: {e}", exc_info=True)
        return {"error": f"Erro inesperado na IA: {e}"}

# --- Agente Antigo (Não usado) ---
def run_valuation_agent(inputs_data: dict, user_razao_social: str) -> dict:
    logger.warning("run_valuation_agent (AGENTE ANTIGO) foi chamado. Isso não deveria acontecer no novo fluxo.")
    return {"error": "Agente antigo foi chamado. Verifique o chatbot/tasks.py."}
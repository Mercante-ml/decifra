# chatbot/utils.py
import logging

logger = logging.getLogger(__name__)

# --- NOVOS CONJUNTOS DE VALIDAÇÃO ---

# Lista de chaves esperadas para os dados financeiros e seus tipos
FINANCIAL_KEYS = {
    'faturamento_mensal': 'float_positive',
    'gastos_variaveis': 'float_non_negative',
    'gastos_fixos': 'float_non_negative',
    'num_vendas': 'int_positive',
    'num_prospeccoes': 'int_positive',
    'setor_atuacao': 'text',
}

# Lista de chaves esperadas para os 18 critérios de avaliação
QUALITATIVE_KEYS = [
    "visao_pessoas", "nivel_validacao", "nivel_equipe", "potencial_network",
    "diferencial_modelo", "possibilidade_escala", "pmf", "potencial_alcance",
    "nivel_parcerias", "estagio_modelo", "estagio_prototipo", 
    "nivel_analise_financeira", "estagio_comercializacao", "nivel_faturamento", 
    "nivel_lucro", "possibilidade_copia", "potencial_mercado_barreiras",
    "potencial_internacionalizacao",
]

# Respostas válidas permitidas para os critérios qualitativos
VALID_QUALITATIVE_ANSWERS = {
    "BAIXO", 
    "NÃO CONSIGO AVALIAR", 
    "MÉDIO", 
    "ALTO", 
    "ELEVADO"
}

def validate_inputs_backend(data: dict) -> tuple[dict | None, str | None]:
    """
    Valida os dados de input (6 financeiros + 18 qualitativos)
    recebidos pela API no backend.
    """
    if not isinstance(data, dict):
        return None, "Formato de dados inválido."

    inputs_raw = data.get('inputs')
    if not isinstance(inputs_raw, dict):
        return None, "Estrutura de 'inputs' ausente ou inválida."

    validated_data = {}
    
    # --- 1. Validar Chaves Financeiras ---
    for key, val_type in FINANCIAL_KEYS.items():
        value = inputs_raw.get(key)
        
        if value is None:
            return None, f"Dado obrigatório ausente: {key}"
        
        try:
            if val_type == 'float_positive':
                value = float(value)
                if value <= 0:
                    raise ValueError("Deve ser maior que zero")
            elif val_type == 'float_non_negative':
                value = float(value)
                if value < 0:
                    raise ValueError("Não pode ser negativo")
            elif val_type == 'int_positive':
                value = int(value)
                if value <= 0:
                    raise ValueError("Deve ser inteiro e maior que zero")
            elif val_type == 'text':
                value = str(value).strip()
                if not (1 <= len(value) <= 255): # Limite de tamanho razoável
                    raise ValueError("Texto inválido ou muito longo")
            
            validated_data[key] = value
            
        except (ValueError, TypeError):
            logger.warning(f"Erro de validação backend para '{key}': recebido '{value}', esperado '{val_type}'")
            return None, f"Valor inválido para o campo '{key}'. Esperado: {val_type}."

    # --- 2. Validar Chaves Qualitativas ---
    for key in QUALITATIVE_KEYS:
        value = inputs_raw.get(key)
        
        if not isinstance(value, str):
            return None, f"Valor inválido para o campo '{key}'. Esperado: texto."
        
        value_upper = value.upper().strip()
        
        if value_upper not in VALID_QUALITATIVE_ANSWERS:
            logger.warning(f"Erro de validação backend para '{key}': recebido '{value_upper}'")
            return None, f"Resposta inválida para o campo '{key}': {value}"
        
        validated_data[key] = value_upper 

    # --- 3. Verificar contagem ---
    total_keys = len(FINANCIAL_KEYS) + len(QUALITATIVE_KEYS)
    if len(validated_data) != total_keys:
         return None, f"Número incorreto de campos de input recebidos. Esperado: {total_keys}, Recebido: {len(validated_data)}"

    logger.info("Validação de backend concluída com sucesso.")
    return validated_data, None
# reports/admin.py
from django.contrib import admin
from django.utils.html import format_html, json_script
from django.utils.safestring import mark_safe
import json
from .models import ValuationReport

@admin.register(ValuationReport)
class ValuationReportAdmin(admin.ModelAdmin):
    list_display = (
        'id', 
        'user', 
        'status', 
        'get_valuation_realista', # <-- NOVO
        'get_gamma_status',       # <-- NOVO
        'gamma_presentation_link',
        'created_at'
    )
    list_filter = (
        'status', 
        'created_at'
        
    )
    search_fields = ('id', 'user__razao_social', 'user__cnpj')
    ordering = ('-created_at',)
    
    # Mantém os campos de dados JSON formatados na página de detalhes
    readonly_fields = (
        'inputs_data_formatted', 
        'result_data_formatted', 
        'gamma_presentation_link'
    )
    
    # Define os campos visíveis na página de edição/detalhe
    fields = (
        'id', 
        'user', 
        'status', 
        'gamma_presentation_url',
        'gamma_presentation_link',
        'created_at', 
        'updated_at',
        'inputs_data_formatted', 
        'result_data_formatted'
    )

    def get_readonly_fields(self, request, obj=None):
        # Torna campos-chave readonly se o objeto já existir
        if obj:
            return self.readonly_fields + ('id', 'user', 'created_at', 'updated_at')
        return self.readonly_fields

    # --- FUNÇÃO DE FORMATAÇÃO JSON (sem mudanças) ---
    def pretty_print_json(self, data):
        """Renderiza o JSON de forma legível no admin."""
        if not data or not isinstance(data, dict):
            return "N/A"
        
        # Converte para JSON string
        json_str = json.dumps(data, indent=4, ensure_ascii=False)
        
        # Usa <pre> para manter a formatação e adiciona um pouco de estilo
        html = f'<pre style="background: #f4f4f4; border: 1px solid #ddd; padding: 10px; border-radius: 5px; max-height: 400px; overflow-y: auto;">{json_str}</pre>'
        return mark_safe(html)

    @admin.display(description="Inputs Formatados")
    def inputs_data_formatted(self, obj):
        return self.pretty_print_json(obj.inputs_data)

    @admin.display(description="Resultados Formatados")
    def result_data_formatted(self, obj):
        return self.pretty_print_json(obj.result_data)

    # --- NOVAS COLUNAS PARA A LISTA ---

    @admin.display(description="Valuation (Realista)", ordering='result_data__valuation_base')
    def get_valuation_realista(self, obj):
        """Exibe o valuation realista na lista."""
        if obj.result_data and obj.result_data.get('valuation_base'):
            try:
                val = float(obj.result_data['valuation_base'])
                return f"R$ {val:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
            except (ValueError, TypeError):
                return "Erro de formato"
        return "N/A"

    @admin.display(description="Status Gamma", ordering='result_data__gamma_status')
    def get_gamma_status(self, obj):
        """Exibe o status do Gamma (pending, completed, failed) na lista."""
        if obj.result_data and obj.result_data.get('gamma_status'):
            status = obj.result_data['gamma_status']
            if status == 'completed':
                return format_html('<span style="color: green;">● Completed</span>')
            elif status == 'pending':
                return format_html('<span style="color: orange;">● Pending</span>')
            elif status == 'failed':
                return format_html('<span style="color: red;">● Failed</span>')
        return "N/A"
    
    # Mantém o link do Gamma (sem mudanças)
    @admin.display(description="Link Gamma")
    def gamma_presentation_link(self, obj):
        if obj.gamma_presentation_url:
            return format_html('<a href="{}" target="_blank">Abrir Apresentação</a>', obj.gamma_presentation_url)
        return "Nenhum link gerado"
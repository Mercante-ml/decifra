# users/admin.py
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .forms import CustomUserCreationForm # Importa o formulário de criação
from .models import CustomUser

class CustomUserAdmin(UserAdmin):
    # 1. ISTO ESTÁ CORRETO
    # Diz ao Admin para usar o seu formulário de criação personalizado
    add_form = CustomUserCreationForm

    model = CustomUser
    
    # --- O que mostrar na lista principal de utilizadores ---
    list_display = (
        'cnpj', 
        'email', 
        'razao_social', 
        'ddd', 
        'telefone', 
        'is_staff', 
        'is_active', 
        'usage_count', 
        'date_joined'
    )
    
    # --- O que pode ser pesquisado ---
    search_fields = ('cnpj', 'email', 'razao_social', 'telefone')
    
    # --- Filtros laterais ---
    list_filter = ('is_staff', 'is_active', 'date_joined')
    
    # --- Campo de ordenação ---
    ordering = ('cnpj',)

    # --- A CORREÇÃO ESTÁ AQUI ---

    # 1. Define os campos que são apenas para leitura na página de edição.
    readonly_fields = ('last_login', 'date_joined')

    # 2. O BLOCO 'add_fieldsets' FOI REMOVIDO
    # Este bloco estava a causar o conflito. Ao removê-lo,
    # o Django vai usar corretamente o 'add_form = CustomUserCreationForm'
    # que definimos no topo desta classe.
    
    # add_fieldsets = (
    #     (None, {
    #         'classes': ('wide',),
    #         'fields': ('cnpj', 'razao_social', 'email', 'ddd', 'telefone', 'password', 'password2'),
    #     }),
    # )

    # 3. ESTE BLOCO ESTÁ CORRETO E DEVE SER MANTIDO
    # Ele controla a página de *edição* (quando clica num usuário que já existe)
    fieldsets = (
        # Informação Principal (Login e Senha)
        (None, {'fields': ('cnpj', 'password')}),
        
        # Informações da Empresa (Nossos campos)
        ('Dados da Empresa', {'fields': ('razao_social', 'email', 'ddd', 'telefone')}),
        
        # Permissões
        ('Permissões', {'fields': ('is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions')}),
        
        # Contagem de Uso
        ('Uso', {'fields': ('usage_count',)}),
        
        # Datas Importantes (Como estão em 'readonly_fields', serão mostrados mas não editáveis)
        ('Datas Importantes', {'fields': ('last_login', 'date_joined')}),
    )
    # --- FIM DA CORREÇÃO ---

# Registra o modelo CustomUser com a configuração CustomUserAdmin
admin.site.register(CustomUser, CustomUserAdmin)
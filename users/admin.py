# users/admin.py

from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .forms import CustomUserCreationForm
from .models import CustomUser

class CustomUserAdmin(UserAdmin):
    # Usa o nosso formulário customizado para a página "Adicionar utilizador"
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
    
    # --- Campos somente leitura ---
    readonly_fields = ('last_login', 'date_joined')

    # --- FIELDSETS PARA ADIÇÃO (sem password/password2) ---
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('cnpj', 'razao_social', 'email', 'ddd', 'telefone', 'is_staff', 'is_active', 'password1', 'password2'),
        }),
    )

    # --- FIELDSETS PARA EDIÇÃO ---
    fieldsets = (
        (None, {'fields': ('cnpj', 'password')}),
        ('Dados da Empresa', {'fields': ('razao_social', 'email', 'ddd', 'telefone')}),
        ('Permissões', {'fields': ('is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions')}),
        ('Uso', {'fields': ('usage_count',)}),
        ('Datas Importantes', {'fields': ('last_login', 'date_joined')}),
    )

# Registra o modelo CustomUser com a configuração CustomUserAdmin
admin.site.register(CustomUser, CustomUserAdmin)

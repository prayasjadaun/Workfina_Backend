from django.contrib import admin
from .models import Wallet, WalletTransaction

@admin.register(Wallet)
class WalletAdmin(admin.ModelAdmin):
    list_display = ['hr_profile', 'balance', 'total_spent', 'created_at']
    search_fields = ['hr_profile__company_name', 'hr_profile__user__email']
    readonly_fields = ['total_spent', 'created_at', 'updated_at']

@admin.register(WalletTransaction)
class WalletTransactionAdmin(admin.ModelAdmin):
    list_display = ['wallet', 'transaction_type', 'credits_added', 'credits_used', 'created_at']
    list_filter = ['transaction_type', 'created_at']
    search_fields = ['wallet__hr_profile__company_name', 'reference_id']
    readonly_fields = ['created_at']
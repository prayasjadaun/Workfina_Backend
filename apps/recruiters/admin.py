from django.contrib import admin
from .models import HRProfile
from apps.wallet.models import Wallet

@admin.register(HRProfile)
class HRProfileAdmin(admin.ModelAdmin):
    list_display = ['user', 'company_name', 'designation', 'get_wallet_balance', 'get_total_spent', 'is_verified']
    list_filter = ['is_verified', 'company_size']
    search_fields = ['company_name', 'user__email']
    readonly_fields = ['get_wallet_balance', 'get_total_spent']
    
    fieldsets = (
        ('User Information', {
            'fields': ('user', 'full_name')
        }),
        ('Company Details', {
            'fields': ('company_name', 'designation', 'phone', 'company_website', 'company_size')
        }),
        ('Wallet Information', {
            'fields': ('get_wallet_balance', 'get_total_spent')
        }),
        ('Verification', {
            'fields': ('is_verified',)
        }),
    )
    
    def get_wallet_balance(self, obj):
        try:
            return obj.wallet.balance
        except Wallet.DoesNotExist:
            return 0
    get_wallet_balance.short_description = 'Balance'
    
    def get_total_spent(self, obj):
        try:
            return obj.wallet.total_spent
        except Wallet.DoesNotExist:
            return 0
    get_total_spent.short_description = 'Total Spent'
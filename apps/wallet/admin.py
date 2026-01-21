from django.contrib import admin
from .models import Wallet, WalletTransaction, CreditSettings

@admin.register(CreditSettings)
class CreditSettingsAdmin(admin.ModelAdmin):
    list_display = ['price_per_credit', 'unlock_credits_required', 'updated_at']
    fieldsets = (
        ('Credit Pricing', {
            'fields': ('price_per_credit',),
            'description': 'Set the price for 1 credit in rupees'
        }),
        ('Unlock Settings', {
            'fields': ('unlock_credits_required',),
            'description': 'Set how many credits are required to unlock a candidate'
        }),
    )

    def has_add_permission(self, request):
        # Only allow one instance
        return not CreditSettings.objects.exists()

    def has_delete_permission(self, request, obj=None):
        # Prevent deletion
        return False

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
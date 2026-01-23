from django.contrib import admin
from django import forms
from .models import HRProfile, Company, CompanyLocation
from apps.wallet.models import Wallet
from apps.candidates.models import FilterCategory, FilterOption


class CompanyLocationForm(forms.ModelForm):
    """Custom form to filter city/state/country dropdowns"""
    class Meta:
        model = CompanyLocation
        fields = '__all__'

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        try:
            # Filter dropdowns by category
            city_category = FilterCategory.objects.get(slug='city')
            state_category = FilterCategory.objects.get(slug='state')
            country_category = FilterCategory.objects.get(slug='country')

            self.fields['city'].queryset = FilterOption.objects.filter(category=city_category, is_active=True)
            self.fields['state'].queryset = FilterOption.objects.filter(category=state_category, is_active=True)
            self.fields['country'].queryset = FilterOption.objects.filter(category=country_category, is_active=True)
        except FilterCategory.DoesNotExist:
            pass


class CompanyLocationInline(admin.TabularInline):
    """Inline admin for company locations - allows adding infinite locations"""
    model = CompanyLocation
    form = CompanyLocationForm
    extra = 1
    fields = ['city', 'state', 'country', 'address', 'is_headquarters']
    verbose_name = "Location"
    verbose_name_plural = "Locations"


@admin.register(Company)
class CompanyAdmin(admin.ModelAdmin):
    list_display = ['name', 'size', 'is_verified', 'get_locations_count', 'created_at']
    list_filter = ['is_verified', 'size', 'created_at']
    search_fields = ['name', 'website']
    readonly_fields = ['id', 'created_at', 'updated_at']
    inlines = [CompanyLocationInline]

    fieldsets = (
        ('Company Information', {
            'fields': ('name', 'logo', 'website', 'size')
        }),
        ('Verification', {
            'fields': ('is_verified',)
        }),
        ('System Information', {
            'fields': ('id', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

    def get_locations_count(self, obj):
        return obj.locations.count()
    get_locations_count.short_description = 'Locations'


@admin.register(HRProfile)
class HRProfileAdmin(admin.ModelAdmin):
    list_display = ['user', 'get_company_name', 'designation', 'is_verified', 'get_company_verified', 'get_wallet_balance', 'get_total_spent']
    list_filter = ['is_verified', 'company__is_verified', 'company__size']
    search_fields = ['company__name', 'user__email', 'full_name']
    readonly_fields = ['get_wallet_balance', 'get_total_spent', 'created_at', 'updated_at']
    autocomplete_fields = ['company']
    actions = ['verify_hr_profiles', 'unverify_hr_profiles']

    fieldsets = (
        ('User Information', {
            'fields': ('user', 'full_name')
        }),
        ('Company & Role Details', {
            'fields': ('company', 'designation', 'phone')
        }),
        ('Verification Status', {
            'fields': ('is_verified',),
            'description': 'HR verification is separate from company verification. Both must be verified for full access.'
        }),
        ('Wallet Information', {
            'fields': ('get_wallet_balance', 'get_total_spent')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

    def get_company_name(self, obj):
        return obj.company.name if obj.company else "No Company"
    get_company_name.short_description = 'Company'
    get_company_name.admin_order_field = 'company__name'

    def get_company_verified(self, obj):
        return obj.company.is_verified if obj.company else False
    get_company_verified.short_description = 'Verified'
    get_company_verified.boolean = True
    get_company_verified.admin_order_field = 'company__is_verified'

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

    def verify_hr_profiles(self, request, queryset):
        """Bulk action to verify HR profiles"""
        updated = queryset.update(is_verified=True)
        self.message_user(request, f'{updated} HR profile(s) verified successfully.')
    verify_hr_profiles.short_description = 'Verify selected HR profiles'

    def unverify_hr_profiles(self, request, queryset):
        """Bulk action to unverify HR profiles"""
        updated = queryset.update(is_verified=False)
        self.message_user(request, f'{updated} HR profile(s) unverified.')
    unverify_hr_profiles.short_description = 'Unverify selected HR profiles'


@admin.register(CompanyLocation)
class CompanyLocationAdmin(admin.ModelAdmin):
    list_display = ['company', 'city', 'state', 'country', 'is_headquarters']
    list_filter = ['is_headquarters', 'country', 'state']
    search_fields = ['company__name', 'city', 'state', 'country']
    autocomplete_fields = ['company']
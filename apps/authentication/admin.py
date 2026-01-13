from django.contrib import admin
from .models import User, EmailOTP

@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    list_display = ['email', 'get_full_name', 'role', 'is_email_verified', 'is_active']
    list_filter = ['role', 'is_email_verified', 'is_active', 'is_staff']
    search_fields = ['email', 'first_name', 'last_name', 'employee_id']
    readonly_fields = ['id']

@admin.register(EmailOTP)
class EmailOTPAdmin(admin.ModelAdmin):
    list_display = ['email', 'otp', 'created_at', 'is_used']
    list_filter = ['is_used', 'created_at']
    search_fields = ['email']
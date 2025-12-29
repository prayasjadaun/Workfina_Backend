from django.contrib import admin
from .models import User, EmailOTP

@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    list_display = ['email', 'username', 'role', 'is_email_verified', 'date_joined']
    list_filter = ['role', 'is_email_verified', 'is_active']
    search_fields = ['email', 'username']

@admin.register(EmailOTP)
class EmailOTPAdmin(admin.ModelAdmin):
    list_display = ['email', 'otp', 'created_at', 'is_used']
    list_filter = ['is_used', 'created_at']
    search_fields = ['email']
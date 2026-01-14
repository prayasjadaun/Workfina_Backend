from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.utils.translation import gettext_lazy as _
from .models import User, EmailOTP


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    """Custom admin for User model with email-based authentication."""

    # List display
    list_display = ['email', 'first_name', 'last_name', 'role', 'is_email_verified', 'is_active', 'is_staff']
    list_filter = ['role', 'is_email_verified', 'is_active', 'is_staff', 'is_superuser']
    search_fields = ['email', 'first_name', 'last_name']
    ordering = ['email']

    # Fieldsets for viewing/editing existing users
    fieldsets = (
        (None, {'fields': ('email', 'password')}),
        (_('Personal Info'), {'fields': ('first_name', 'last_name')}),
        (_('Role & Verification'), {'fields': ('role', 'is_email_verified', 'google_id', 'fcm_token')}),
        (_('Permissions'), {
            'fields': ('is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions'),
        }),
        (_('Important dates'), {'fields': ('last_login', 'date_joined')}),
    )

    # Fieldsets for adding new users
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('email', 'password1', 'password2', 'first_name', 'last_name', 'role'),
        }),
    )

    readonly_fields = ['date_joined', 'last_login']


@admin.register(EmailOTP)
class EmailOTPAdmin(admin.ModelAdmin):
    list_display = ['email', 'otp', 'created_at', 'is_used']
    list_filter = ['is_used', 'created_at']
    search_fields = ['email']
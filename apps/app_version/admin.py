from django.contrib import admin
from django.utils.html import format_html, mark_safe
from .models import AppVersion, VersionCheckLog


@admin.register(AppVersion)
class AppVersionAdmin(admin.ModelAdmin):
    list_display = [
        'version_number',
        'version_code',
        'platform',
        'status_badge',
        'mandatory_badge',
        'release_date',
        'created_at'
    ]

    list_filter = [
        'platform',
        'is_mandatory',
        'is_active',
        'release_date'
    ]

    search_fields = [
        'version_number',
        'release_notes'
    ]

    readonly_fields = [
        'id',
        'version_code',
        'minimum_version_code',
        'created_at',
        'updated_at'
    ]

    fieldsets = (
        ('Version Information', {
            'fields': (
                'id',
                'version_number',
                'version_code',
                'platform',
            )
        }),
        ('Update Settings', {
            'fields': (
                'is_active',
                'is_mandatory',
                'minimum_supported_version',
                'minimum_version_code',
            )
        }),
        ('Release Information', {
            'fields': (
                'release_notes',
                'release_date',
                'features',
                'bug_fixes',
            )
        }),
        ('Download Links', {
            'fields': (
                'download_url_android',
                'download_url_ios',
            )
        }),
        ('Metadata', {
            'fields': (
                'created_by',
                'created_at',
                'updated_at',
            ),
            'classes': ('collapse',)
        }),
    )

    def status_badge(self, obj):
        """Display active status as colored badge"""
        if obj.is_active:
            return mark_safe(
                '<span style="background-color: #28a745; color: white; padding: 3px 10px; border-radius: 3px; font-weight: bold;">ACTIVE</span>'
            )
        return mark_safe(
            '<span style="background-color: #6c757d; color: white; padding: 3px 10px; border-radius: 3px;">INACTIVE</span>'
        )
    status_badge.short_description = 'Status'

    def mandatory_badge(self, obj):
        """Display mandatory status as colored badge"""
        if obj.is_mandatory:
            return mark_safe(
                '<span style="background-color: #dc3545; color: white; padding: 3px 10px; border-radius: 3px; font-weight: bold;">MANDATORY</span>'
            )
        return mark_safe(
            '<span style="background-color: #17a2b8; color: white; padding: 3px 10px; border-radius: 3px;">OPTIONAL</span>'
        )
    mandatory_badge.short_description = 'Update Type'

    def save_model(self, request, obj, form, change):
        """Auto-set created_by on creation"""
        if not change:  # Only on creation
            obj.created_by = request.user.email
        super().save_model(request, obj, form, change)

    class Media:
        css = {
            'all': ('admin/css/custom_admin.css',)
        }


@admin.register(VersionCheckLog)
class VersionCheckLogAdmin(admin.ModelAdmin):
    list_display = [
        'user_display',
        'current_version',
        'platform',
        'update_status',
        'checked_at'
    ]

    list_filter = [
        'platform',
        'update_available',
        'is_mandatory',
        'force_update',
        'checked_at'
    ]

    search_fields = [
        'user__email',
        'user__phone_number',
        'current_version',
        'ip_address'
    ]

    readonly_fields = [
        'id',
        'user',
        'current_version',
        'current_version_code',
        'platform',
        'update_available',
        'is_mandatory',
        'force_update',
        'latest_version',
        'device_info',
        'ip_address',
        'user_agent',
        'checked_at'
    ]

    fieldsets = (
        ('User Information', {
            'fields': (
                'id',
                'user',
                'ip_address',
                'user_agent',
            )
        }),
        ('Version Information', {
            'fields': (
                'current_version',
                'current_version_code',
                'platform',
                'latest_version',
            )
        }),
        ('Update Status', {
            'fields': (
                'update_available',
                'is_mandatory',
                'force_update',
            )
        }),
        ('Device Information', {
            'fields': (
                'device_info',
            ),
            'classes': ('collapse',)
        }),
        ('Timestamp', {
            'fields': (
                'checked_at',
            )
        }),
    )

    def user_display(self, obj):
        """Display user email or Anonymous"""
        if obj.user:
            return obj.user.email
        return "Anonymous"
    user_display.short_description = 'User'

    def update_status(self, obj):
        """Display update status as colored badge"""
        if obj.force_update:
            return mark_safe(
                '<span style="background-color: #dc3545; color: white; padding: 3px 10px; border-radius: 3px; font-weight: bold;">FORCE UPDATE</span>'
            )
        elif obj.update_available and obj.is_mandatory:
            return mark_safe(
                '<span style="background-color: #fd7e14; color: white; padding: 3px 10px; border-radius: 3px; font-weight: bold;">MANDATORY UPDATE</span>'
            )
        elif obj.update_available:
            return mark_safe(
                '<span style="background-color: #17a2b8; color: white; padding: 3px 10px; border-radius: 3px;">UPDATE AVAILABLE</span>'
            )
        return mark_safe(
            '<span style="background-color: #28a745; color: white; padding: 3px 10px; border-radius: 3px;">UP TO DATE</span>'
        )
    update_status.short_description = 'Status'

    def has_add_permission(self, request):
        """Disable manual addition of logs"""
        return False

    def has_delete_permission(self, request, obj=None):
        """Allow deletion for cleanup"""
        return True

    def has_change_permission(self, request, obj=None):
        """Read-only logs"""
        return False

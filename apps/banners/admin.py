from django.contrib import admin
from .models import Banner, RecruiterBanner

@admin.register(Banner)
class BannerAdmin(admin.ModelAdmin):
    list_display = ('title', 'is_active', 'created_at')


@admin.register(RecruiterBanner)
class RecruiterBannerAdmin(admin.ModelAdmin):
    list_display = ('heading', 'height', 'is_active', 'created_at', 'updated_at')
    list_filter = ('is_active', 'created_at')
    search_fields = ('heading', 'subheading')
    readonly_fields = ('created_at', 'updated_at')
    fieldsets = (
        ('Banner Content', {
            'fields': ('heading', 'subheading', 'image')
        }),
        ('Display Settings', {
            'fields': ('height', 'is_active')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

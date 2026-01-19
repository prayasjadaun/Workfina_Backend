from django.contrib import admin
from .models import Banner, RecruiterBanner

@admin.register(Banner)
class BannerAdmin(admin.ModelAdmin):
    list_display = ('title', 'is_active', 'created_at')


@admin.register(RecruiterBanner)
class RecruiterBannerAdmin(admin.ModelAdmin):
    list_display = ('heading', 'height', 'is_active', 'created_at', 'updated_at')
    list_filter = ('is_active', 'created_at', 'text_align')
    search_fields = ('heading', 'subheading')
    readonly_fields = ('created_at', 'updated_at')
    fieldsets = (
        ('Banner Content', {
            'fields': ('heading', 'subheading', 'image')
        }),
        ('Display Settings', {
            'fields': ('height', 'is_active', 'text_align')
        }),
        ('Heading Styling', {
            'fields': ('heading_font_size', 'heading_color', 'heading_font_weight'),
            'classes': ('collapse',)
        }),
        ('Subheading Styling', {
            'fields': ('subheading_font_size', 'subheading_color', 'subheading_font_weight'),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

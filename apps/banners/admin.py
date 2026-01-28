from django.contrib import admin
from .models import Banner, RecruiterBanner

@admin.register(Banner)
class BannerAdmin(admin.ModelAdmin):
    list_display = ('title', 'height', 'is_active', 'created_at', 'updated_at')
    list_filter = ('is_active', 'created_at', 'content_alignment')
    search_fields = ('title', 'button_text')
    readonly_fields = ('created_at', 'updated_at')

    fieldsets = (
        ('Banner Content', {
            'fields': ('title', 'button_text', 'image'),
            'description': 'Title and button are optional. You can upload just an image.'
        }),
        ('Banner Dimensions', {
            'fields': ('height', 'border_radius', 'is_active')
        }),
        ('Title Styling', {
            'fields': ('title_font_size', 'title_color', 'title_font_weight'),
            'classes': ('collapse',),
            'description': 'Customize title appearance'
        }),
        ('Button Styling', {
            'fields': (
                'button_bg_color', 'button_text_color', 'button_font_size',
                'button_font_weight', 'button_border_radius',
                'button_padding_horizontal', 'button_padding_vertical'
            ),
            'classes': ('collapse',),
            'description': 'Customize button appearance'
        }),
        ('Gradient Overlay', {
            'fields': (
                'gradient_start_color', 'gradient_start_opacity',
                'gradient_end_color', 'gradient_end_opacity'
            ),
            'classes': ('collapse',),
            'description': 'Gradient overlay on the banner image'
        }),
        ('Content Layout', {
            'fields': ('content_alignment', 'content_padding'),
            'classes': ('collapse',),
            'description': 'Control content positioning'
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )


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

from django.contrib import admin
from .models import Candidate, UnlockHistory, FilterCategory, FilterOption, CandidateNote, CandidateFollowup

class FilterOptionInline(admin.TabularInline):
    model = FilterOption
    extra = 1
    fields = ['name', 'slug', 'parent', 'display_order', 'is_active']

@admin.register(FilterCategory)
class FilterCategoryAdmin(admin.ModelAdmin):
    list_display = ['name', 'slug', 'display_order', 'is_active', 'created_at']
    list_filter = ['is_active']
    search_fields = ['name']
    prepopulated_fields = {'slug': ('name',)}
    inlines = [FilterOptionInline]
    ordering = ['display_order', 'name']



@admin.register(Candidate)
class CandidateAdmin(admin.ModelAdmin):
    list_display = ['user', 'masked_name', 'role', 'experience_years', 'city', 'age', 'is_active']
    list_filter = ['role__category', 'religion', 'state', 'is_active', 'experience_years']
    search_fields = ['full_name', 'masked_name', 'user__email', 'skills']
    readonly_fields = ['masked_name', 'created_at', 'updated_at']
    raw_id_fields = ['user']  # Better performance for user selection
    
    fieldsets = (
        ('User Account', {
            'fields': ('user',)
        }),
        ('Basic Information', {
            'fields': ('full_name', 'masked_name', 'phone', 'age')
        }),
        ('Professional', {
            'fields': ('role', 'experience_years', 'current_ctc', 'expected_ctc', 'skills')
        }),
        ('Personal', {
            'fields': ('religion',)
        }),
        ('Location', {
            'fields': ('country', 'state', 'city')
        }),
        ('Education & Resume', {
            'fields': ('education', 'resume', 'video_intro', 'profile_image')
        }),
        ('Status', {
            'fields': ('is_active', 'created_at', 'updated_at')
        })
    )

@admin.register(UnlockHistory)
class UnlockHistoryAdmin(admin.ModelAdmin):
    list_display = ['hr_user', 'candidate', 'credits_used', 'unlocked_at']
    list_filter = ['unlocked_at', 'credits_used']
    search_fields = ['hr_user__user__email', 'candidate__masked_name']
    readonly_fields = ['unlocked_at']
    raw_id_fields = ['hr_user', 'candidate']  # Better performance

@admin.register(CandidateNote)
class CandidateNoteAdmin(admin.ModelAdmin):
    list_display = ['hr_user', 'candidate', 'note_text_preview', 'created_at']
    list_filter = ['created_at']
    search_fields = ['hr_user__user__email', 'candidate__masked_name', 'note_text']
    readonly_fields = ['created_at', 'updated_at']
    raw_id_fields = ['hr_user', 'candidate']
    
    def note_text_preview(self, obj):
        return obj.note_text[:50] + '...' if len(obj.note_text) > 50 else obj.note_text
    note_text_preview.short_description = 'Note Preview'

@admin.register(CandidateFollowup)
class CandidateFollowupAdmin(admin.ModelAdmin):
    list_display = ['hr_user', 'candidate', 'followup_date', 'is_completed', 'created_at']
    list_filter = ['is_completed', 'followup_date', 'created_at']
    search_fields = ['hr_user__user__email', 'candidate__masked_name', 'notes']
    readonly_fields = ['created_at', 'updated_at']
    raw_id_fields = ['hr_user', 'candidate']
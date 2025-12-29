from django.contrib import admin
from .models import Candidate, UnlockHistory

@admin.register(Candidate)
class CandidateAdmin(admin.ModelAdmin):
    list_display = ['user', 'masked_name', 'role', 'experience_years', 'city', 'age', 'is_active']
    list_filter = ['role', 'religion', 'state', 'is_active', 'experience_years']
    search_fields = ['full_name', 'masked_name', 'user__email', 'skills']
    readonly_fields = ['masked_name', 'created_at', 'updated_at']
    
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
            'fields': ('education', 'resume')
        }),
        ('Status', {
            'fields': ('is_active',)
        })
    )

@admin.register(UnlockHistory)
class UnlockHistoryAdmin(admin.ModelAdmin):
    list_display = ['hr_user', 'candidate', 'credits_used', 'unlocked_at']
    list_filter = ['unlocked_at', 'credits_used']
    search_fields = ['hr_user__email', 'candidate__masked_name']
    readonly_fields = ['unlocked_at']
from django.contrib import admin
from django import forms    
from .models import *

class WorkExperienceInline(admin.TabularInline):
    model = WorkExperience
    extra = 1
    fields = ['company_name', 'role_title', 'start_date', 'end_date', 'is_current', 'location', 'description']

class EducationInline(admin.TabularInline):
    model = Education
    extra = 1
    fields = ['institution_name', 'degree', 'field_of_study', 'start_year', 'end_year', 'is_ongoing', 'grade_percentage', 'location']

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

class CandidateAdminForm(forms.ModelForm):
    class Meta:
        model = Candidate
        fields = '__all__'
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        try:
            # Filter role options to only show department category
            dept_category = FilterCategory.objects.get(slug='department')
            self.fields['role'].queryset = FilterOption.objects.filter(category=dept_category)
        except FilterCategory.DoesNotExist:
            pass
            
        try:
            # Filter religion options to only show religion category  
            religion_category = FilterCategory.objects.get(slug='religion')
            self.fields['religion'].queryset = FilterOption.objects.filter(category=religion_category)
        except FilterCategory.DoesNotExist:
            pass
            
        try:
            # Filter location options by their respective categories
            country_category = FilterCategory.objects.get(slug='country')
            state_category = FilterCategory.objects.get(slug='state') 
            city_category = FilterCategory.objects.get(slug='city')
            
            self.fields['country'].queryset = FilterOption.objects.filter(category=country_category)
            self.fields['state'].queryset = FilterOption.objects.filter(category=state_category)
            self.fields['city'].queryset = FilterOption.objects.filter(category=city_category)
        except FilterCategory.DoesNotExist:
            pass


@admin.register(Candidate)
class CandidateAdmin(admin.ModelAdmin):
    form = CandidateAdminForm 
    list_display = ['user', 'masked_name','first_name', 'last_name', 'role', 'experience_years', 'city', 'age', 'is_active']
    list_filter = ['role__category', 'religion', 'state', 'is_active', 'experience_years','joining_availability']
    search_fields = ['first_name', 'last_name', 'masked_name', 'user__email', 'skills','notice_period_details']
    readonly_fields = ['masked_name', 'created_at', 'updated_at']
    raw_id_fields = ['user']
    inlines = [WorkExperienceInline, EducationInline]
    
    fieldsets = (
        ('User Account', {
            'fields': ('user',)
        }),
        ('Basic Information', {
            'fields': ('first_name', 'last_name', 'masked_name', 'phone', 'age')
        }),
        ('Professional', {
            'fields': ('role', 'experience_years', 'current_ctc', 'expected_ctc', 'skills')
        }),
        ('Availability', { 
            'fields': ('joining_availability', 'notice_period_details')
        }),
        ('Personal', {
            'fields': ('religion', 'languages', 'street_address', 'willing_to_relocate', 'career_objective')
        }),
        ('Location', {
            'fields': ('country', 'state', 'city')
        }),
        ('Resume & Media', {
            'fields': ('resume', 'video_intro', 'profile_image')
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
    raw_id_fields = ['hr_user', 'candidate']  

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

@admin.register(WorkExperience)
class WorkExperienceAdmin(admin.ModelAdmin):
    list_display = ['candidate', 'company_name', 'role_title', 'start_date', 'end_date', 'is_current']
    list_filter = ['is_current', 'start_date']
    search_fields = ['candidate__masked_name', 'company_name', 'role_title']
    raw_id_fields = ['candidate']

@admin.register(Education)
class EducationAdmin(admin.ModelAdmin):
    list_display = ['candidate', 'institution_name', 'degree', 'start_year', 'end_year', 'is_ongoing']
    list_filter = ['is_ongoing', 'start_year']
    search_fields = ['candidate__masked_name', 'institution_name', 'degree']
    raw_id_fields = ['candidate']
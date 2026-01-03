from django.db import models
from django.contrib.auth import get_user_model
from django.db.models.signals import pre_save
from django.dispatch import receiver
from django.core.exceptions import ValidationError
import uuid
from apps.recruiters.models import HRProfile

User = get_user_model()

def validate_icon_file(value):
    """Allow both image files and SVG files for icons"""
    if not value:
        return
    
    # Check file extension
    if value.name.lower().endswith('.svg'):
        return  # SVG is allowed
    
    # For non-SVG files, use default image validation
    from PIL import Image
    try:
        image = Image.open(value)
        image.verify()
    except Exception:
        raise ValidationError("Upload a valid image or SVG file.")

class FilterCategory(models.Model):
    """Main filter categories like Department, Religion, Location etc."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=100, unique=True)
    slug = models.SlugField(max_length=100, unique=True)
    icon = models.FileField(upload_to='filter_icons/', blank=True, null=True, validators=[validate_icon_file])
    display_order = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['display_order', 'name']
    
    def __str__(self):
        return self.name

class FilterOption(models.Model):
    """Individual options within each category"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    category = models.ForeignKey(FilterCategory, on_delete=models.CASCADE, related_name='options')
    name = models.CharField(max_length=255)
    slug = models.SlugField(max_length=255)
    parent = models.ForeignKey('self', on_delete=models.CASCADE, null=True, blank=True, related_name='children')
    display_order = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['display_order', 'name']
        unique_together = ['category', 'slug']
    
    def __str__(self):
        if self.parent:
            return f"{self.parent.name} > {self.name}"
        return f"{self.category.name}: {self.name}"

class Candidate(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='candidate_profile')

    # Basic Information
    full_name = models.CharField(max_length=255)
    masked_name = models.CharField(max_length=50)
    phone = models.CharField(max_length=20)
    age = models.PositiveIntegerField()
    
    # Professional Information - Using FilterOption
    role = models.ForeignKey(FilterOption, on_delete=models.SET_NULL, null=True, blank=True, related_name='role_candidates')
    experience_years = models.PositiveIntegerField()
    current_ctc = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    expected_ctc = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    
    # Personal Information - Using FilterOption
    religion = models.ForeignKey(FilterOption, on_delete=models.SET_NULL, null=True, blank=True, related_name='religion_candidates')
    
    # Location - Using FilterOption with hierarchy
    country = models.ForeignKey(FilterOption, on_delete=models.SET_NULL, null=True, blank=True, related_name='country_candidates')
    state = models.ForeignKey(FilterOption, on_delete=models.SET_NULL, null=True, blank=True, related_name='state_candidates')
    city = models.ForeignKey(FilterOption, on_delete=models.SET_NULL, null=True, blank=True, related_name='city_candidates')
    
    # Education & Skills - Using FilterOption
    education = models.ForeignKey(FilterOption, on_delete=models.SET_NULL, null=True, blank=True, related_name='education_candidates')
    skills = models.TextField()  # Comma-separated skills
    education_details = models.TextField(blank=True, null=True)

    
    # Resume & Documents
    resume = models.FileField(upload_to='resumes/', blank=True)
    video_intro = models.FileField(upload_to='video_intros/', blank=True, null=True)
    profile_image = models.ImageField(upload_to='profile_images/', blank=True, null=True)

    languages = models.TextField(blank=True, null=True)  # Comma-separated languages
    street_address = models.CharField(max_length=500, blank=True, null=True)
    willing_to_relocate = models.BooleanField(default=False)
    
    # Work Experience Details
    work_experience = models.TextField(blank=True, null=True)  # JSON or structured text
    
    # Career Objective
    career_objective = models.TextField(blank=True, null=True)


    # Meta Information
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-created_at']
        
    def __str__(self):
        return self.masked_name
        
    def get_skills_list(self):
        return [skill.strip() for skill in self.skills.split(',') if skill.strip()]

class UnlockHistory(models.Model):
    hr_user = models.ForeignKey(HRProfile, on_delete=models.CASCADE)
    candidate = models.ForeignKey(Candidate, on_delete=models.CASCADE)
    credits_used = models.PositiveIntegerField(default=10)
    unlocked_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        unique_together = ['hr_user', 'candidate']
        ordering = ['-unlocked_at']
        
    def __str__(self):
        return f"{self.hr_user.user.email} unlocked {self.candidate}"

class CandidateNote(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    hr_user = models.ForeignKey(HRProfile, on_delete=models.CASCADE, related_name='candidate_notes')
    candidate = models.ForeignKey(Candidate, on_delete=models.CASCADE, related_name='notes')
    note_text = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-created_at']
        
    def __str__(self):
        return f"Note by {self.hr_user.user.email} for {self.candidate.masked_name}"

class CandidateFollowup(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    hr_user = models.ForeignKey(HRProfile, on_delete=models.CASCADE, related_name='candidate_followups')
    candidate = models.ForeignKey(Candidate, on_delete=models.CASCADE, related_name='followups')
    followup_date = models.DateTimeField()
    notes = models.TextField(blank=True, null=True)
    is_completed = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['followup_date']
        
    def __str__(self):
        return f"Followup by {self.hr_user.user.email} for {self.candidate.masked_name} on {self.followup_date}"

# Signal to auto-generate masked_name
@receiver(pre_save, sender=Candidate)
def generate_masked_name(sender, instance, **kwargs):
    if instance.full_name and not instance.masked_name:
        names = instance.full_name.split()
        masked = []
        for name in names:
            if len(name) > 1:
                masked.append(name[0] + '*' * (len(name) - 1))
            else:
                masked.append('*')
        instance.masked_name = ' '.join(masked)
from django.db import models
from django.contrib.auth import get_user_model
from django.db.models.signals import pre_save
from django.dispatch import receiver
import uuid

User = get_user_model()

class Candidate(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    # Link to User account
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='candidate_profile')

    # Basic Information
    full_name = models.CharField(max_length=255)
    masked_name = models.CharField(max_length=50)  # e.g., "J*** D***"
    phone = models.CharField(max_length=20)
    age = models.PositiveIntegerField()
    
    # Professional Information
    ROLE_CHOICES = [
        ('IT', 'Information Technology'),
        ('HR', 'Human Resources'),
        ('SUPPORT', 'Customer Support'),
        ('SALES', 'Sales'),
        ('MARKETING', 'Marketing'),
        ('FINANCE', 'Finance'),
        ('DESIGN', 'Design'),
        ('OTHER', 'Other'),
    ]
    role = models.CharField(max_length=20, choices=ROLE_CHOICES)
    experience_years = models.PositiveIntegerField()
    current_ctc = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    expected_ctc = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    
    # Personal Information
    RELIGION_CHOICES = [
        ('HINDU', 'Hindu'),
        ('MUSLIM', 'Muslim'),
        ('CHRISTIAN', 'Christian'),
        ('SIKH', 'Sikh'),
        ('BUDDHIST', 'Buddhist'),
        ('JAIN', 'Jain'),
        ('OTHER', 'Other'),
        ('PREFER_NOT_TO_SAY', 'Prefer not to say'),
    ]
    religion = models.CharField(max_length=20, choices=RELIGION_CHOICES, blank=True)
    
    # Location
    country = models.CharField(max_length=100, default='India')
    state = models.CharField(max_length=100)
    city = models.CharField(max_length=100)
    
    # Education & Skills
    education = models.TextField()
    skills = models.TextField()  # Comma-separated skills
    
    # Resume & Documents
    resume = models.FileField(upload_to='resumes/', blank=True)
    video_intro = models.FileField(upload_to='video_intros/', blank=True,null=True)  # ✅ ADD THIS

    
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
    hr_user = models.ForeignKey(User, on_delete=models.CASCADE, limit_choices_to={'role': 'hr'})
    candidate = models.ForeignKey(Candidate, on_delete=models.CASCADE)
    credits_used = models.PositiveIntegerField(default=10)
    unlocked_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        unique_together = ['hr_user', 'candidate']
        ordering = ['-unlocked_at']
        
    def __str__(self):
        return f"{self.hr_user.email} unlocked {self.candidate}"

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
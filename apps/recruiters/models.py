from django.db import models
from django.contrib.auth import get_user_model
import uuid


User = get_user_model()

class HRProfile(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='hr_profile')
    full_name = models.CharField(max_length=255,blank=True, default='')
    company_name = models.CharField(max_length=255)
    designation = models.CharField(max_length=100)
    phone = models.CharField(max_length=20)
    company_website = models.URLField(blank=True)
    company_size = models.CharField(max_length=50, choices=[
        ('1-10', '1-10 employees'),
        ('11-50', '11-50 employees'), 
        ('51-200', '51-200 employees'),
        ('201-1000', '201-1000 employees'),
        ('1000+', '1000+ employees')
    ])
    is_verified = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    
    def __str__(self):
        return f"{self.company_name} - {self.user.email}"
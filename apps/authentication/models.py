from django.contrib.auth.models import AbstractUser
from django.db import models
import random
from datetime import timedelta
from django.utils import timezone

class User(AbstractUser):
    ROLE_CHOICES = [
        ('candidate', 'Candidate'),
        ('hr', 'HR/Recruiter'),
    ]
    
    email = models.EmailField(unique=True)
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='')
    is_email_verified = models.BooleanField(default=False)
    google_id = models.CharField(max_length=100, blank=True, null=True)
    fcm_token = models.TextField(blank=True, null=True)
    
    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['username']

class EmailOTP(models.Model):
    email = models.EmailField()
    otp = models.CharField(max_length=6)
    created_at = models.DateTimeField(auto_now_add=True)
    is_used = models.BooleanField(default=False)
    
    def is_expired(self):
        return timezone.now() > self.created_at + timedelta(minutes=10)
    
    @classmethod
    def generate_otp(cls, email):
        otp = str(random.randint(100000, 999999))
        cls.objects.filter(email=email, is_used=False).update(is_used=True)
        return cls.objects.create(email=email, otp=otp)
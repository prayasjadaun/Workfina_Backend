from django.db import models
from django.contrib.auth import get_user_model
from django.utils import timezone
from datetime import timedelta
import uuid

User = get_user_model()

class NotificationTemplate(models.Model):
    """Admin-configurable notification templates"""
    NOTIFICATION_TYPES = [
        ('COMPLETE_PROFILE', 'Complete Profile'),
        ('PROFILE_STEP_REMINDER', 'Profile Step Reminder'),
        ('CANDIDATE_HIRED', 'Candidate Hired'),
        ('PROFILE_UPGRADE', 'Profile Upgrade'),
        ('GENERAL', 'General Announcement'),
        ('WELCOME', 'Welcome Message'),
        ('CREDIT_UPDATE', 'Credit Update'),
    ]
    
    RECIPIENT_TYPES = [
        ('CANDIDATE', 'Candidates Only'),
        ('HR', 'HR/Recruiters Only'), 
        ('ALL', 'All Users'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=200, help_text="Admin reference name")
    notification_type = models.CharField(max_length=30, choices=NOTIFICATION_TYPES)
    recipient_type = models.CharField(max_length=10, choices=RECIPIENT_TYPES)
    
    title = models.CharField(max_length=100)
    body = models.TextField(max_length=500)
    
    # Trigger settings
    is_active = models.BooleanField(default=True)
    auto_trigger = models.BooleanField(default=False, help_text="Auto send based on user actions")
    delay_minutes = models.PositiveIntegerField(default=0, help_text="Delay before sending (in minutes)")
    
    # Sound and visual settings
    play_sound = models.BooleanField(default=True)
    icon = models.ImageField(upload_to='notification_icons/', blank=True, null=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['notification_type', 'name']
    
    def __str__(self):
        return f"{self.name} ({self.get_notification_type_display()})"


class UserNotification(models.Model):
    """Individual notifications sent to users"""
    STATUS_CHOICES = [
        ('PENDING', 'Pending'),
        ('SENT', 'Sent'),
        ('DELIVERED', 'Delivered'),
        ('FAILED', 'Failed'),
        ('READ', 'Read'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='notifications')
    template = models.ForeignKey(NotificationTemplate, on_delete=models.CASCADE, null=True, blank=True)
    
    title = models.CharField(max_length=100)
    body = models.TextField(max_length=500)
    
    # FCM data
    fcm_message_id = models.CharField(max_length=200, blank=True, null=True)
    data_payload = models.JSONField(default=dict, blank=True)
    
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='PENDING')
    scheduled_for = models.DateTimeField(default=timezone.now)
    sent_at = models.DateTimeField(null=True, blank=True)
    read_at = models.DateTimeField(null=True, blank=True)
    
    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    error_message = models.TextField(blank=True, null=True)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.title} → {self.user.email}"
    
    def mark_as_read(self):
        if not self.read_at:
            self.read_at = timezone.now()
            self.status = 'READ'
            self.save()


class ProfileStepReminder(models.Model):
    """Track profile completion reminders for candidates"""
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='step_reminder')
    current_step = models.PositiveIntegerField(default=1)
    last_step_completed_at = models.DateTimeField(auto_now_add=True)
    
    # Reminder schedule
    first_reminder_sent = models.BooleanField(default=False)
    first_reminder_at = models.DateTimeField(null=True, blank=True)
    
    second_reminder_sent = models.BooleanField(default=False)
    second_reminder_at = models.DateTimeField(null=True, blank=True)
    
    final_reminder_sent = models.BooleanField(default=False)
    final_reminder_at = models.DateTimeField(null=True, blank=True)
    
    is_profile_completed = models.BooleanField(default=False)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-updated_at']
    
    def __str__(self):
        return f"{self.user.email} - Step {self.current_step}"
    
    def update_step(self, new_step):
        """Update user's current step and reset reminders if progressed"""
        if new_step > self.current_step:
            self.current_step = new_step
            self.last_step_completed_at = timezone.now()
            
            # Reset reminders for new step
            self.first_reminder_sent = False
            self.first_reminder_at = None
            self.second_reminder_sent = False
            self.second_reminder_at = None
            self.final_reminder_sent = False
            self.final_reminder_at = None
            
            if new_step >= 4:  # Profile completed
                self.is_profile_completed = True
            
            self.save()
    
    def needs_reminder(self):
        """Check if user needs a reminder based on time elapsed"""
        if self.is_profile_completed:
            return False, None
        
        time_since_last_step = timezone.now() - self.last_step_completed_at
        
        # 24 hours - first reminder
        if not self.first_reminder_sent and time_since_last_step >= timedelta(hours=24):
            return True, "first"
        
        # 72 hours - second reminder  
        elif not self.second_reminder_sent and time_since_last_step >= timedelta(hours=72):
            return True, "second"
        
        # 7 days - final reminder
        elif not self.final_reminder_sent and time_since_last_step >= timedelta(days=7):
            return True, "final"
        
        return False, None


class CandidateStatus(models.Model):
    """Track candidate hiring status for HR notifications"""
    STATUS_CHOICES = [
        ('ACTIVE', 'Active - Looking for Job'),
        ('HIRED', 'Hired'),
        ('ON_HOLD', 'Application on Hold'),
        ('REJECTED', 'Rejected'),
        ('WITHDRAWN', 'Withdrawn Application'),
    ]
    
    candidate = models.OneToOneField('candidates.Candidate', on_delete=models.CASCADE, related_name='hiring_status')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='ACTIVE')
    
    # HR who hired/updated status
    updated_by = models.ForeignKey('recruiters.HRProfile', on_delete=models.SET_NULL, null=True, blank=True)
    company_name = models.CharField(max_length=200, blank=True, null=True)
    position_title = models.CharField(max_length=200, blank=True, null=True)
    
    notes = models.TextField(blank=True, null=True)
    
    status_updated_at = models.DateTimeField(auto_now=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-status_updated_at']
    
    def __str__(self):
        return f"{self.candidate.masked_name} - {self.get_status_display()}"


class NotificationLog(models.Model):
    """Log all notification activities for debugging"""
    LOG_TYPES = [
        ('FCM_SENT', 'FCM Message Sent'),
        ('FCM_ERROR', 'FCM Error'),
        ('TEMPLATE_TRIGGERED', 'Template Triggered'),
        ('REMINDER_SCHEDULED', 'Reminder Scheduled'),
        ('USER_ACTION', 'User Action Triggered'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    log_type = models.CharField(max_length=30, choices=LOG_TYPES)
    user = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True)
    notification = models.ForeignKey(UserNotification, on_delete=models.CASCADE, null=True, blank=True)
    
    message = models.TextField()
    metadata = models.JSONField(default=dict, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.get_log_type_display()} - {self.created_at}"
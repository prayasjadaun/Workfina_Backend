from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from django.http import HttpResponseRedirect
from django.contrib import messages
from django.utils import timezone
from django.contrib.auth import get_user_model
from .models import (
    NotificationTemplate, 
    UserNotification, 
    ProfileStepReminder,
    CandidateStatus,
    NotificationLog
)
from .services import WorkfinaFCMService
from django import forms

User = get_user_model()


@admin.register(NotificationTemplate)
class NotificationTemplateAdmin(admin.ModelAdmin):
    list_display = [
        'name', 'notification_type', 'recipient_type', 'title_preview', 
        'auto_trigger', 'is_active', 'play_sound', 'created_at'
    ]
    list_filter = ['notification_type', 'recipient_type', 'auto_trigger', 'is_active', 'play_sound']
    search_fields = ['name', 'title', 'body']
    readonly_fields = ['created_at', 'updated_at']
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('name', 'notification_type', 'recipient_type')
        }),
        ('Message Content', {
            'fields': ('title', 'body'),
            'description': 'You can use placeholders like {user_name}, {current_step}, {company_name} in title and body'
        }),
        ('Settings', {
            'fields': ('is_active', 'auto_trigger', 'delay_minutes')
        }),
        ('Appearance & Sound', {
            'fields': ('play_sound', 'icon'),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        })
    )
    
    actions = ['send_test_notification', 'duplicate_template', 'send_to_selected_users']

    def send_to_selected_users(self, request, queryset):
        """Send notification to selected template's recipient users"""
        if queryset.count() != 1:
            messages.error(request, 'Please select exactly one template.')
            return

        template = queryset.first()

        try:
            # Get users based on template's recipient type
            if template.recipient_type == 'CANDIDATE':
                users = User.objects.filter(role='candidate', is_active=True, fcm_token__isnull=False).exclude(fcm_token='')
            elif template.recipient_type == 'HR':
                users = User.objects.filter(role='hr', is_active=True, fcm_token__isnull=False).exclude(fcm_token='')
            else:  # ALL
                users = User.objects.filter(is_active=True, fcm_token__isnull=False).exclude(fcm_token='')

            if not users.exists():
                self.message_user(request, f'No active users with FCM tokens found for {template.recipient_type}', level=messages.WARNING)
                return

            # Send to first 5 users as test
            test_users = users[:5]
            success_count = 0
            failed_users = []

            for user in test_users:
                result = WorkfinaFCMService.send_to_user(
                    user=user,
                    title=template.title,
                    body=template.body,
                    notification_type=template.notification_type
                )

                if result.get('success'):
                    success_count += 1
                else:
                    failed_users.append(user.email)

            if success_count > 0:
                self.message_user(request, f'Notification sent to {success_count}/{len(test_users)} users successfully.')

            if failed_users:
                self.message_user(request, f'Failed for: {", ".join(failed_users)}', level=messages.WARNING)

        except Exception as e:
            self.message_user(request, f'Error: {str(e)}', level=messages.ERROR)

    send_to_selected_users.short_description = 'Send to recipient users (test)'
    
    def title_preview(self, obj):
        return obj.title[:50] + '...' if len(obj.title) > 50 else obj.title
    title_preview.short_description = 'Title Preview'
    
    def send_test_notification(self, request, queryset):
        """Send test notification to current admin user"""
        if queryset.count() != 1:
            messages.error(request, 'Please select exactly one template to test.')
            return
        
        template = queryset.first()
        
        if not hasattr(request.user, 'fcm_token') or not request.user.fcm_token:
            messages.error(request, 'Your account needs an FCM token. Login to the mobile app first.')
            return
        
        try:
            # Create test notification
            notification = UserNotification.objects.create(
                user=request.user,
                template=template,
                title=f"[TEST] {template.title}",
                body=template.body,
                data_payload={'test': True, 'template_id': str(template.id)}
            )
            
            # Send via FCM
            result = WorkfinaFCMService.send_notification(notification)
            
            if result.get('success'):
                messages.success(request, f'Test notification sent successfully to {request.user.email}')
            else:
                messages.error(request, f'Failed to send notification: {result.get("error", "Unknown error")}')
                
        except Exception as e:
            messages.error(request, f'Error sending test notification: {str(e)}')
    
    send_test_notification.short_description = 'Send test notification to me'
    
    def duplicate_template(self, request, queryset):
        """Duplicate selected templates"""
        count = 0
        for template in queryset:
            template.pk = None  # This will create a new instance
            template.name = f"{template.name} (Copy)"
            template.is_active = False  # Deactivate copies by default
            template.save()
            count += 1
        
        messages.success(request, f'Successfully duplicated {count} template(s).')
    
    duplicate_template.short_description = 'Duplicate selected templates'


@admin.register(UserNotification)
class UserNotificationAdmin(admin.ModelAdmin):
    list_display = [
        'title_preview', 'user_email', 'status', 'template_type',
        'scheduled_for', 'sent_at', 'read_at'
    ]
    list_filter = [
        'status', 'template__notification_type', 'scheduled_for', 
        'sent_at', 'read_at'
    ]
    search_fields = ['title', 'body', 'user__email', 'user__username']
    readonly_fields = [
        'fcm_message_id', 'sent_at', 'read_at', 'created_at', 'error_message'
    ]
    date_hierarchy = 'created_at'
    
    fieldsets = (
        ('Notification Details', {
            'fields': ('user', 'template', 'title', 'body')
        }),
        ('Scheduling', {
            'fields': ('status', 'scheduled_for', 'sent_at', 'read_at')
        }),
        ('FCM Details', {
            'fields': ('fcm_message_id', 'data_payload', 'error_message'),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('created_at',),
            'classes': ('collapse',)
        })
    )
    
    actions = ['resend_failed_notifications', 'mark_as_read']
    
    def title_preview(self, obj):
        return obj.title[:40] + '...' if len(obj.title) > 40 else obj.title
    title_preview.short_description = 'Title'
    
    def user_email(self, obj):
        return obj.user.email
    user_email.short_description = 'User Email'
    user_email.admin_order_field = 'user__email'
    
    def template_type(self, obj):
        return obj.template.get_notification_type_display() if obj.template else 'Custom'
    template_type.short_description = 'Type'
    
    def resend_failed_notifications(self, request, queryset):
        """Resend failed notifications"""
        failed_notifications = queryset.filter(status='FAILED')
        count = 0
        
        for notification in failed_notifications:
            try:
                result = WorkfinaFCMService.send_notification(notification)
                if result.get('success'):
                    count += 1
            except Exception:
                pass
        
        messages.success(request, f'Attempted to resend {failed_notifications.count()} notifications. {count} succeeded.')
    
    resend_failed_notifications.short_description = 'Resend failed notifications'
    
    def mark_as_read(self, request, queryset):
        """Mark notifications as read"""
        count = queryset.filter(read_at__isnull=True).update(
            read_at=timezone.now(),
            status='READ'
        )
        messages.success(request, f'Marked {count} notifications as read.')
    
    mark_as_read.short_description = 'Mark as read'


@admin.register(ProfileStepReminder)
class ProfileStepReminderAdmin(admin.ModelAdmin):
    list_display = [
        'user_email', 'current_step', 'is_profile_completed',
        'last_step_completed_at', 'reminders_sent', 'next_reminder'
    ]
    list_filter = [
        'current_step', 'is_profile_completed', 'first_reminder_sent',
        'second_reminder_sent', 'final_reminder_sent'
    ]
    search_fields = ['user__email', 'user__username']
    readonly_fields = [
        'user', 'first_reminder_at', 'second_reminder_at', 'final_reminder_at',
        'created_at', 'updated_at'
    ]
    
    fieldsets = (
        ('User Progress', {
            'fields': ('user', 'current_step', 'last_step_completed_at', 'is_profile_completed')
        }),
        ('Reminder Status', {
            'fields': (
                ('first_reminder_sent', 'first_reminder_at'),
                ('second_reminder_sent', 'second_reminder_at'), 
                ('final_reminder_sent', 'final_reminder_at')
            )
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        })
    )
    
    actions = ['send_manual_reminder', 'reset_reminders']
    
    def user_email(self, obj):
        return obj.user.email
    user_email.short_description = 'User Email'
    user_email.admin_order_field = 'user__email'
    
    def reminders_sent(self, obj):
        count = sum([obj.first_reminder_sent, obj.second_reminder_sent, obj.final_reminder_sent])
        return f"{count}/3"
    reminders_sent.short_description = 'Reminders Sent'
    
    def next_reminder(self, obj):
        needs_reminder, reminder_type = obj.needs_reminder()
        if needs_reminder:
            return f"Ready for {reminder_type} reminder"
        elif obj.is_profile_completed:
            return "Profile completed"
        else:
            return "No reminder needed yet"
    next_reminder.short_description = 'Next Reminder'
    
    def send_manual_reminder(self, request, queryset):
        """Manually send profile completion reminders"""
        count = 0
        for reminder in queryset.filter(is_profile_completed=False):
            try:
                WorkfinaFCMService.send_profile_step_reminder(reminder.user, reminder.current_step)
                count += 1
            except Exception as e:
                messages.error(request, f'Error sending reminder to {reminder.user.email}: {str(e)}')
        
        messages.success(request, f'Sent manual reminders to {count} users.')
    
    send_manual_reminder.short_description = 'Send manual reminder'
    
    def reset_reminders(self, request, queryset):
        """Reset reminder status for selected users"""
        queryset.update(
            first_reminder_sent=False,
            first_reminder_at=None,
            second_reminder_sent=False, 
            second_reminder_at=None,
            final_reminder_sent=False,
            final_reminder_at=None
        )
        messages.success(request, f'Reset reminder status for {queryset.count()} users.')
    
    reset_reminders.short_description = 'Reset reminder status'


@admin.register(CandidateStatus)
class CandidateStatusAdmin(admin.ModelAdmin):
    list_display = [
        'candidate_name', 'status', 'company_name', 'position_title',
        'updated_by_email', 'status_updated_at'
    ]
    list_filter = ['status', 'status_updated_at', 'company_name']
    search_fields = [
        'candidate__masked_name', 'candidate__user__email',
        'company_name', 'position_title', 'updated_by__user__email'
    ]
    readonly_fields = ['candidate', 'status_updated_at', 'created_at']
    
    fieldsets = (
        ('Candidate Information', {
            'fields': ('candidate', 'status')
        }),
        ('Job Details', {
            'fields': ('company_name', 'position_title', 'updated_by')
        }),
        ('Additional Information', {
            'fields': ('notes',)
        }),
        ('Timestamps', {
            'fields': ('status_updated_at', 'created_at'),
            'classes': ('collapse',)
        })
    )
    
    def candidate_name(self, obj):
        return obj.candidate.masked_name
    candidate_name.short_description = 'Candidate'
    candidate_name.admin_order_field = 'candidate__masked_name'
    
    def updated_by_email(self, obj):
        return obj.updated_by.user.email if obj.updated_by else 'System'
    updated_by_email.short_description = 'Updated By'
    
    def save_model(self, request, obj, form, change):
        if not obj.updated_by and hasattr(request.user, 'hr_profile'):
            obj.updated_by = request.user.hr_profile
        super().save_model(request, obj, form, change)
        
        # Send notification to HR users who have unlocked this candidate
        if obj.status == 'HIRED':
            WorkfinaFCMService.notify_hrs_about_hired_candidate(obj.candidate)


@admin.register(NotificationLog)
class NotificationLogAdmin(admin.ModelAdmin):
    list_display = [
        'log_type', 'user_email', 'notification_title', 'message_preview', 'created_at'
    ]
    list_filter = ['log_type', 'created_at']
    search_fields = ['message', 'user__email', 'notification__title']
    readonly_fields = ['created_at']
    date_hierarchy = 'created_at'
    
    fieldsets = (
        ('Log Details', {
            'fields': ('log_type', 'user', 'notification', 'message')
        }),
        ('Metadata', {
            'fields': ('metadata',),
            'classes': ('collapse',)
        }),
        ('Timestamp', {
            'fields': ('created_at',)
        })
    )
    
    def user_email(self, obj):
        return obj.user.email if obj.user else 'System'
    user_email.short_description = 'User'
    
    def notification_title(self, obj):
        return obj.notification.title if obj.notification else '-'
    notification_title.short_description = 'Notification'
    
    def message_preview(self, obj):
        return obj.message[:60] + '...' if len(obj.message) > 60 else obj.message
    message_preview.short_description = 'Message Preview'
    
    def has_add_permission(self, request):
        return False  # Don't allow manual creation
    
    def has_change_permission(self, request, obj=None):
        return False  # Read-only logs


# Custom admin actions for bulk notification sending
class SendBulkNotificationForm(forms.Form):
    title = forms.CharField(max_length=100)
    body = forms.CharField(widget=forms.Textarea)
    recipient_type = forms.ChoiceField(
        choices=[('ALL', 'All Users'), ('CANDIDATE', 'Candidates Only'), ('HR', 'HR Only')]
    )
    play_sound = forms.BooleanField(required=False, initial=True)


def send_bulk_notification(modeladmin, request, queryset):
    """Custom admin action to send bulk notifications"""
    if request.POST.get('apply'):
        form = SendBulkNotificationForm(request.POST)
        if form.is_valid():
            title = form.cleaned_data['title']
            body = form.cleaned_data['body']
            recipient_type = form.cleaned_data['recipient_type']
            play_sound = form.cleaned_data['play_sound']
            
            result = WorkfinaFCMService.send_bulk_notification(
                title=title,
                body=body,
                recipient_type=recipient_type,
                play_sound=play_sound
            )
            
            messages.success(
                request, 
                f'Bulk notification sent! Success: {result.get("success_count", 0)}, '
                f'Failed: {result.get("failure_count", 0)}'
            )
            return
    
    form = SendBulkNotificationForm()
    return admin.helpers.render_to_response(
        'admin/send_bulk_notification.html',
        {'form': form, 'queryset': queryset}
    )

send_bulk_notification.short_description = 'Send bulk notification'
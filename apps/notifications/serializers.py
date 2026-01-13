from rest_framework import serializers
from .models import UserNotification, NotificationTemplate, ProfileStepReminder, CandidateStatus


class NotificationTemplateSerializer(serializers.ModelSerializer):
    notification_type_display = serializers.CharField(source='get_notification_type_display', read_only=True)
    recipient_type_display = serializers.CharField(source='get_recipient_type_display', read_only=True)
    
    class Meta:
        model = NotificationTemplate
        fields = [
            'id', 'name', 'notification_type', 'notification_type_display',
            'recipient_type', 'recipient_type_display', 'title', 'body',
            'is_active', 'auto_trigger', 'delay_minutes', 'play_sound',
            'icon_url', 'created_at', 'updated_at'
        ]


class UserNotificationSerializer(serializers.ModelSerializer):
    template_name = serializers.CharField(source='template.name', read_only=True)
    notification_type = serializers.CharField(source='template.notification_type', read_only=True)
    time_ago = serializers.SerializerMethodField()
    is_read = serializers.SerializerMethodField()
    
    class Meta:
        model = UserNotification
        fields = [
            'id', 'title', 'body', 'status', 'template_name', 'notification_type',
            'data_payload', 'scheduled_for', 'sent_at', 'read_at', 'created_at',
            'time_ago', 'is_read'
        ]
        read_only_fields = [
            'fcm_message_id', 'sent_at', 'read_at', 'created_at', 'error_message'
        ]
    
    def get_time_ago(self, obj):
        """Get human readable time ago"""
        from django.utils.timesince import timesince
        from django.utils import timezone
        
        if obj.read_at:
            return f"Read {timesince(obj.read_at)} ago"
        elif obj.sent_at:
            return f"Sent {timesince(obj.sent_at)} ago"
        else:
            return f"Created {timesince(obj.created_at)} ago"
    
    def get_is_read(self, obj):
        return obj.read_at is not None


class ProfileStepReminderSerializer(serializers.ModelSerializer):
    user_email = serializers.CharField(source='user.email', read_only=True)
    user_name = serializers.CharField(source='user.username', read_only=True)
    needs_reminder = serializers.SerializerMethodField()
    next_reminder_type = serializers.SerializerMethodField()
    
    class Meta:
        model = ProfileStepReminder
        fields = [
            'user_email', 'user_name', 'current_step', 'last_step_completed_at',
            'first_reminder_sent', 'first_reminder_at', 'second_reminder_sent',
            'second_reminder_at', 'final_reminder_sent', 'final_reminder_at',
            'is_profile_completed', 'needs_reminder', 'next_reminder_type',
            'created_at', 'updated_at'
        ]
        read_only_fields = [
            'first_reminder_at', 'second_reminder_at', 'final_reminder_at',
            'created_at', 'updated_at'
        ]
    
    def get_needs_reminder(self, obj):
        needs_reminder, _ = obj.needs_reminder()
        return needs_reminder
    
    def get_next_reminder_type(self, obj):
        _, reminder_type = obj.needs_reminder()
        return reminder_type


class CandidateStatusSerializer(serializers.ModelSerializer):
    candidate_name = serializers.CharField(source='candidate.masked_name', read_only=True)
    candidate_email = serializers.CharField(source='candidate.user.email', read_only=True)
    updated_by_name = serializers.CharField(source='updated_by.user.username', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    
    class Meta:
        model = CandidateStatus
        fields = [
            'id', 'candidate_name', 'candidate_email', 'status', 'status_display',
            'updated_by_name', 'company_name', 'position_title', 'notes',
            'status_updated_at', 'created_at'
        ]
        read_only_fields = ['status_updated_at', 'created_at']


class BulkNotificationSerializer(serializers.Serializer):
    title = serializers.CharField(max_length=100)
    body = serializers.CharField(max_length=500)
    recipient_type = serializers.ChoiceField(
        choices=[('ALL', 'All Users'), ('CANDIDATE', 'Candidates'), ('HR', 'HR Users')],
        default='ALL'
    )
    play_sound = serializers.BooleanField(default=True)
    schedule_for = serializers.DateTimeField(required=False)
    
    def validate(self, data):
        if len(data['title'].strip()) == 0:
            raise serializers.ValidationError("Title cannot be empty")
        if len(data['body'].strip()) == 0:
            raise serializers.ValidationError("Body cannot be empty")
        return data


class NotificationStatsSerializer(serializers.Serializer):
    total_notifications = serializers.IntegerField()
    notifications_last_30_days = serializers.IntegerField()
    sent_notifications = serializers.IntegerField()
    delivered_notifications = serializers.IntegerField()
    read_notifications = serializers.IntegerField()
    failed_notifications = serializers.IntegerField()
    active_templates = serializers.IntegerField()
    users_with_fcm_tokens = serializers.IntegerField()
    notification_types = serializers.DictField()
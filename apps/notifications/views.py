from rest_framework import status, generics
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django.contrib.admin.views.decorators import staff_member_required
from django.http import JsonResponse
from django.utils import timezone
from django.db.models import Q
from datetime import timedelta

from .models import UserNotification, NotificationTemplate, ProfileStepReminder
from .services import WorkfinaFCMService
from .serializers import UserNotificationSerializer, NotificationTemplateSerializer


class UserNotificationListView(generics.ListAPIView):
    """Get user's notifications"""
    serializer_class = UserNotificationSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        return UserNotification.objects.filter(
            user=self.request.user
        ).order_by('-created_at')
    
    def list(self, request, *args, **kwargs):
        queryset = self.get_queryset()
        
        # Mark notifications as delivered when user opens the list
        queryset.filter(status='SENT').update(status='DELIVERED')
        
        # Pagination
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def mark_notification_read(request, notification_id):
    """Mark notification as read"""
    try:
        notification = UserNotification.objects.get(
            id=notification_id,
            user=request.user
        )
        notification.mark_as_read()
        
        return Response({
            'success': True,
            'message': 'Notification marked as read'
        })
    except UserNotification.DoesNotExist:
        return Response({
            'error': 'Notification not found'
        }, status=404)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def mark_all_notifications_read(request):
    """Mark all user notifications as read"""
    count = UserNotification.objects.filter(
        user=request.user,
        read_at__isnull=True
    ).update(
        read_at=timezone.now(),
        status='READ'
    )
    
    return Response({
        'success': True,
        'message': f'Marked {count} notifications as read'
    })


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_notification_count(request):
    """Get unread notification count"""
    unread_count = UserNotification.objects.filter(
        user=request.user,
        read_at__isnull=True
    ).count()
    
    return Response({
        'unread_count': unread_count,
        'total_count': UserNotification.objects.filter(user=request.user).count()
    })


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def send_test_notification(request):
    """Send test notification to current user (for development)"""
    if not request.user.is_staff:
        return Response({
            'error': 'Only staff users can send test notifications'
        }, status=403)
    
    title = request.data.get('title', 'Test Notification')
    body = request.data.get('body', 'This is a test notification from Workfina')
    
    result = WorkfinaFCMService.send_to_user(
        user=request.user,
        title=title,
        body=body,
        notification_type='GENERAL',
        data={'test': True}
    )
    
    return Response(result)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def trigger_profile_reminder(request):
    """Manually trigger profile completion reminder (for testing)"""
    if request.user.role != 'candidate':
        return Response({
            'error': 'Only candidates can trigger profile reminders'
        }, status=400)
    
    try:
        from apps.candidates.models import Candidate
        candidate = Candidate.objects.get(user=request.user)
        
        result = WorkfinaFCMService.send_profile_step_reminder(
            user=request.user,
            current_step=candidate.profile_step or 1,
            reminder_type='manual'
        )
        
        return Response(result)
    except Candidate.DoesNotExist:
        return Response({
            'error': 'Candidate profile not found'
        }, status=404)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_notification_settings(request):
    """Get user's notification preferences"""
    # You can expand this to include user-specific notification settings
    return Response({
        'email_notifications': True,
        'push_notifications': True,
        'profile_reminders': request.user.role == 'candidate',
        'hiring_updates': request.user.role == 'hr',
        'general_announcements': True
    })


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def update_notification_settings(request):
    """Update user's notification preferences"""
    # Implement user notification preferences here
    # For now, just return success
    return Response({
        'success': True,
        'message': 'Notification settings updated'
    })


# Admin/Staff views for sending bulk notifications
@api_view(['POST'])
@permission_classes([IsAuthenticated])
def send_bulk_notification_api(request):
    """API for admins to send bulk notifications"""
    if not request.user.is_staff:
        return Response({
            'error': 'Only staff users can send bulk notifications'
        }, status=403)
    
    title = request.data.get('title')
    body = request.data.get('body')
    recipient_type = request.data.get('recipient_type', 'ALL')
    
    if not title or not body:
        return Response({
            'error': 'Title and body are required'
        }, status=400)
    
    result = WorkfinaFCMService.send_bulk_notification(
        title=title,
        body=body,
        recipient_type=recipient_type
    )
    
    return Response(result)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_notification_templates(request):
    """Get available notification templates"""
    if not request.user.is_staff:
        return Response({
            'error': 'Only staff users can access templates'
        }, status=403)
    
    templates = NotificationTemplate.objects.filter(is_active=True)
    serializer = NotificationTemplateSerializer(templates, many=True)
    return Response(serializer.data)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def send_from_template(request, template_id):
    """Send notification using template"""
    if not request.user.is_staff:
        return Response({
            'error': 'Only staff users can send from templates'
        }, status=403)
    
    try:
        template = NotificationTemplate.objects.get(id=template_id, is_active=True)
        recipient_emails = request.data.get('recipients', [])
        
        if not recipient_emails:
            return Response({
                'error': 'Recipients list is required'
            }, status=400)
        
        from django.contrib.auth import get_user_model
        User = get_user_model()
        
        success_count = 0
        failure_count = 0
        
        for email in recipient_emails:
            try:
                user = User.objects.get(email=email, is_active=True)
                result = WorkfinaFCMService.send_to_user(
                    user=user,
                    title=template.title,
                    body=template.body,
                    notification_type=template.notification_type
                )
                
                if result.get('success'):
                    success_count += 1
                else:
                    failure_count += 1
            except User.DoesNotExist:
                failure_count += 1
        
        return Response({
            'success_count': success_count,
            'failure_count': failure_count,
            'template_used': template.name
        })
        
    except NotificationTemplate.DoesNotExist:
        return Response({
            'error': 'Template not found'
        }, status=404)


@api_view(['GET'])
def notification_stats(request):
    """Get notification statistics (for admin dashboard)"""
    if not request.user.is_staff:
        return Response({
            'error': 'Only staff users can access stats'
        }, status=403)
    
    # Last 30 days stats
    thirty_days_ago = timezone.now() - timedelta(days=30)
    
    stats = {
        'total_notifications': UserNotification.objects.count(),
        'notifications_last_30_days': UserNotification.objects.filter(
            created_at__gte=thirty_days_ago
        ).count(),
        'sent_notifications': UserNotification.objects.filter(status='SENT').count(),
        'delivered_notifications': UserNotification.objects.filter(status='DELIVERED').count(),
        'read_notifications': UserNotification.objects.filter(status='READ').count(),
        'failed_notifications': UserNotification.objects.filter(status='FAILED').count(),
        'active_templates': NotificationTemplate.objects.filter(is_active=True).count(),
        'users_with_fcm_tokens': User.objects.filter(fcm_token__isnull=False).exclude(fcm_token='').count()
    }
    
    # Notification types breakdown
    type_stats = {}
    for choice in NotificationTemplate.NOTIFICATION_TYPES:
        type_stats[choice[0]] = UserNotification.objects.filter(
            template__notification_type=choice[0]
        ).count()
    
    stats['notification_types'] = type_stats
    
    return Response(stats)


# Webhook endpoints for external services (if needed)
@api_view(['POST'])
def fcm_delivery_callback(request):
    """Handle FCM delivery status callbacks"""
    # Implement FCM delivery receipt handling if needed
    message_id = request.data.get('message_id')
    status = request.data.get('status')
    
    if message_id:
        UserNotification.objects.filter(
            fcm_message_id=message_id
        ).update(
            status='DELIVERED' if status == 'delivered' else 'FAILED'
        )
    
    return Response({'success': True})


# Scheduled tasks endpoint (for cron jobs or external schedulers)
@api_view(['POST'])
def run_scheduled_notifications(request):
    """Run scheduled notification checks (call this from cron or celery)"""
    # This endpoint should be protected with API key or internal access only
    from django.conf import settings

    api_key = request.headers.get('X-API-Key')
    expected_key = getattr(settings, 'NOTIFICATION_API_KEY', None)

    if not expected_key:
        return Response({'error': 'Notification API key not configured'}, status=500)

    if api_key != expected_key:
        return Response({'error': 'Unauthorized'}, status=401)
    
    # Run profile reminder checks
    reminder_result = WorkfinaFCMService.check_and_send_profile_reminders()
    
    # Send any pending scheduled notifications
    pending_notifications = UserNotification.objects.filter(
        status='PENDING',
        scheduled_for__lte=timezone.now()
    )
    
    sent_count = 0
    for notification in pending_notifications:
        result = WorkfinaFCMService.send_notification(notification)
        if result.get('success'):
            sent_count += 1
    
    return Response({
        'profile_reminders_sent': reminder_result.get('sent_count', 0),
        'scheduled_notifications_sent': sent_count,
        'total_pending': pending_notifications.count()
    })
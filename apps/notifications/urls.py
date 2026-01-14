from django.urls import path
from .views import (
    UserNotificationListView,
    mark_notification_read,
    mark_all_notifications_read,
    get_notification_count,
    send_test_notification,
    trigger_profile_reminder,
    get_notification_settings,
    update_notification_settings,
    send_bulk_notification_api,
    get_notification_templates,
    send_from_template,
    notification_stats,
    fcm_delivery_callback,
    run_scheduled_notifications,
)

urlpatterns = [
    # User notification endpoints
    path('', UserNotificationListView.as_view(), name='user-notifications'),
    path('count/', get_notification_count, name='notification-count'),
    path('<uuid:notification_id>/read/', mark_notification_read, name='mark-notification-read'),
    path('mark-all-read/', mark_all_notifications_read, name='mark-all-read'),
    
    # User settings
    path('settings/', get_notification_settings, name='notification-settings'),
    path('settings/update/', update_notification_settings, name='update-notification-settings'),
    
    # Testing endpoints (staff only)
    path('test/', send_test_notification, name='send-test-notification'),
    path('trigger-reminder/', trigger_profile_reminder, name='trigger-profile-reminder'),
    
    # Admin/Staff endpoints
    path('bulk/', send_bulk_notification_api, name='send-bulk-notification'),
    path('templates/', get_notification_templates, name='notification-templates'),
    path('templates/<uuid:template_id>/send/', send_from_template, name='send-from-template'),
    path('stats/', notification_stats, name='notification-stats'),
    
    # External/System endpoints
    path('callback/fcm/', fcm_delivery_callback, name='fcm-delivery-callback'),
    path('scheduled/run/', run_scheduled_notifications, name='run-scheduled-notifications'),
]
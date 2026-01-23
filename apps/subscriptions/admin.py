from django.contrib import admin
from django.utils.html import format_html
from django.utils.safestring import mark_safe
from django.utils import timezone
from django.urls import reverse
from django.db.models import Q
from .models import (
    SubscriptionPlan,
    CompanySubscription,
    SubscriptionHistory
)


@admin.register(SubscriptionPlan)
class SubscriptionPlanAdmin(admin.ModelAdmin):
    list_display = [
        'name',
        'plan_type',
        'price_display',
        'credits_info',
        'is_active_badge',
        'active_subscriptions_count',
        'created_at'
    ]
    list_filter = ['is_active', 'plan_type', 'is_unlimited']
    search_fields = ['name', 'description']
    readonly_fields = ['id', 'created_at', 'updated_at']

    fieldsets = (
        ('Basic Information', {
            'fields': ('name', 'description', 'plan_type', 'price')
        }),
        ('Credits Configuration', {
            'fields': ('is_unlimited', 'credits_limit'),
            'description': 'Configure credit limits. For unlimited plans, check "Is unlimited" and leave credits limit empty.'
        }),
        ('Status', {
            'fields': ('is_active',)
        }),
        ('Metadata', {
            'fields': ('id', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

    def price_display(self, obj):
        return f"₹{obj.price:,.2f}"
    price_display.short_description = 'Price'

    def credits_info(self, obj):
        if obj.is_unlimited:
            return mark_safe('<span style="color: green; font-weight: bold;">♾️ Unlimited</span>')
        elif obj.credits_limit:
            return f"{obj.credits_limit:,} credits/month"
        return "Not configured"
    credits_info.short_description = 'Credits'

    def is_active_badge(self, obj):
        if obj.is_active:
            return mark_safe('<span style="color: white; background-color: green; padding: 3px 10px; border-radius: 3px;">Active</span>')
        return mark_safe('<span style="color: white; background-color: red; padding: 3px 10px; border-radius: 3px;">Inactive</span>')
    is_active_badge.short_description = 'Status'

    def active_subscriptions_count(self, obj):
        count = obj.subscriptions.filter(status='ACTIVE').count()
        if count > 0:
            return format_html('<span style="font-weight: bold;">{} companies</span>', count)
        return count
    active_subscriptions_count.short_description = 'Active Subscriptions'


class SubscriptionHistoryInline(admin.TabularInline):
    model = SubscriptionHistory
    extra = 0
    readonly_fields = ['action', 'performed_by', 'details', 'notes', 'created_at']
    can_delete = False

    def has_add_permission(self, request, obj=None):
        return False


@admin.register(CompanySubscription)
class CompanySubscriptionAdmin(admin.ModelAdmin):
    list_display = [
        'company_info',
        'plan_info',
        'status_badge',
        'timeline_info',
        'days_remaining',
        'credits_usage',
        'approved_by'
    ]
    list_filter = [
        'status',
        'plan__plan_type',
        'plan__is_unlimited',
        ('start_date', admin.DateFieldListFilter),
        ('end_date', admin.DateFieldListFilter),
    ]
    search_fields = [
        'hr_profile__company_name',
        'hr_profile__user__email',
        'plan__name',
        'payment_reference'
    ]
    readonly_fields = [
        'id',
        'credits_used',
        'approved_at',
        'cancelled_at',
        'created_at',
        'updated_at'
    ]
    autocomplete_fields = ['hr_profile']
    inlines = [SubscriptionHistoryInline]

    fieldsets = (
        ('Subscription Details', {
            'fields': ('hr_profile', 'plan', 'status')
        }),
        ('Credits Tracking', {
            'fields': ('credits_used',),
            'description': 'Tracks credits used for non-unlimited plans'
        }),
        ('Payment Information', {
            'fields': ('payment_reference',)
        }),
        ('Approval Information', {
            'fields': ('approved_by', 'approved_at'),
            'classes': ('collapse',)
        }),
        ('Cancellation Information', {
            'fields': ('cancelled_by', 'cancelled_at', 'cancellation_reason'),
            'classes': ('collapse',)
        }),
        ('Admin Notes', {
            'fields': ('admin_notes',)
        }),
        ('Timeline', {
            'fields': ('start_date', 'end_date'),
            'description': 'Set dates manually or use bulk action to auto-calculate'
        }),
        ('Metadata', {
            'fields': ('id', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

    actions = [
        'activate_subscriptions',
        'cancel_subscriptions',
        'send_expiry_notifications'
    ]

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        """Filter approved_by and cancelled_by to show only admin/staff users"""
        if db_field.name in ['approved_by', 'cancelled_by']:
            kwargs['queryset'] = db_field.related_model.objects.filter(is_staff=True)
        return super().formfield_for_foreignkey(db_field, request, **kwargs)

    def company_info(self, obj):
        company_name = obj.hr_profile.company.name if obj.hr_profile.company else "No Company"
        return format_html(
            '<strong>{}</strong><br><small style="color: #666;">{}</small>',
            company_name,
            obj.hr_profile.user.email
        )
    company_info.short_description = 'Company'

    def plan_info(self, obj):
        price_color = '#27ae60' if obj.plan.is_unlimited else '#2980b9'
        price_formatted = f"₹{obj.plan.price:,.2f}"
        return format_html(
            '<strong>{}</strong><br><span style="color: {};">{}</span>',
            obj.plan.name,
            price_color,
            price_formatted
        )
    plan_info.short_description = 'Plan'

    def status_badge(self, obj):
        colors = {
            'PENDING': '#f39c12',
            'ACTIVE': '#27ae60',
            'EXPIRED': '#e74c3c',
            'CANCELLED': '#95a5a6',
        }
        color = colors.get(obj.status, '#95a5a6')
        return format_html(
            '<span style="color: white; background-color: {}; padding: 5px 12px; border-radius: 3px; font-weight: bold;">{}</span>',
            color,
            obj.get_status_display()
        )
    status_badge.short_description = 'Status'

    def timeline_info(self, obj):
        if obj.start_date and obj.end_date:
            return format_html(
                '<small>{}<br>to<br>{}</small>',
                obj.start_date.strftime('%d %b %Y'),
                obj.end_date.strftime('%d %b %Y')
            )
        elif obj.created_at:
            return format_html('<small>Created: {}</small>', obj.created_at.strftime('%d %b %Y'))
        return '-'
    timeline_info.short_description = 'Timeline'

    def days_remaining(self, obj):
        if obj.status != 'ACTIVE' or not obj.end_date:
            return '-'

        days = obj.days_until_expiry()
        if days is None:
            return '-'

        warning_level = obj.get_expiry_warning_level()
        colors = {
            'CRITICAL': '#e74c3c',
            'HIGH': '#e67e22',
            'MEDIUM': '#f39c12',
            'LOW': '#27ae60'
        }
        color = colors.get(warning_level, '#27ae60')

        icon = '⚠️' if days <= 7 else '✓'
        return format_html(
            '<span style="color: {}; font-weight: bold;">{} {} days</span>',
            color,
            icon,
            days
        )
    days_remaining.short_description = 'Days Left'

    def credits_usage(self, obj):
        from django.utils.safestring import mark_safe
        if obj.plan.is_unlimited:
            return mark_safe('<span style="color: green;">♾️ Unlimited</span>')
        elif obj.plan.credits_limit:
            percentage = (obj.credits_used / obj.plan.credits_limit) * 100
            color = '#e74c3c' if percentage > 80 else '#27ae60'
            usage_text = f"{obj.credits_used:,} / {obj.plan.credits_limit:,}"
            return format_html(
                '<span style="color: {};">{}</span><br><small>{}%</small>',
                color,
                usage_text,
                int(percentage)
            )
        return f"{obj.credits_used:,} used"
    credits_usage.short_description = 'Credits'

    def activate_subscriptions(self, request, queryset):
        """Bulk activate pending subscriptions"""
        count = 0
        for subscription in queryset.filter(status='PENDING'):
            subscription.activate(admin_user=request.user)
            SubscriptionHistory.objects.create(
                subscription=subscription,
                action='ACTIVATED',
                performed_by=request.user,
                notes='Activated via admin bulk action'
            )
            count += 1

        self.message_user(request, f'{count} subscription(s) activated successfully.')
    activate_subscriptions.short_description = 'Activate selected subscriptions'

    def cancel_subscriptions(self, request, queryset):
        """Bulk cancel active subscriptions"""
        count = 0
        for subscription in queryset.filter(status='ACTIVE'):
            subscription.cancel(admin_user=request.user, reason='Cancelled via admin bulk action')
            SubscriptionHistory.objects.create(
                subscription=subscription,
                action='CANCELLED',
                performed_by=request.user,
                notes='Cancelled via admin bulk action'
            )
            count += 1

        self.message_user(request, f'{count} subscription(s) cancelled successfully.')
    cancel_subscriptions.short_description = 'Cancel selected subscriptions'

    def send_expiry_notifications(self, request, queryset):
        """Send expiry notifications for subscriptions expiring soon"""
        from apps.notifications.models import UserNotification
        count = 0
        for subscription in queryset.filter(status='ACTIVE'):
            days = subscription.days_until_expiry()
            if days is not None and days <= 7:
                UserNotification.objects.create(
                    user=subscription.hr_profile.user,
                    title='Subscription Expiring Soon',
                    body=f'Your {subscription.plan.name} subscription will expire in {days} days on {subscription.end_date.strftime("%d %b %Y")}. Please renew to continue using unlimited credits.',
                    data_payload={'type': 'subscription', 'action': 'expiring', 'subscription_id': str(subscription.id), 'days_remaining': days}
                )
                count += 1

        self.message_user(request, f'{count} expiry notification(s) sent.')
    send_expiry_notifications.short_description = 'Send expiry notifications'

    def save_model(self, request, obj, form, change):
        """Create history entry for new subscriptions"""
        is_new = obj.pk is None
        super().save_model(request, obj, form, change)

        if is_new:
            SubscriptionHistory.objects.create(
                subscription=obj,
                action='CREATED',
                performed_by=request.user,
                notes='Created via admin panel - use bulk action to activate'
            )


@admin.register(SubscriptionHistory)
class SubscriptionHistoryAdmin(admin.ModelAdmin):
    list_display = [
        'company_name',
        'action',
        'performed_by',
        'created_at'
    ]
    list_filter = ['action', 'created_at']
    search_fields = [
        'subscription__hr_profile__company_name',
        'notes'
    ]
    readonly_fields = ['subscription', 'action', 'performed_by', 'details', 'notes', 'created_at']

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        """Filter performed_by to show only admin/staff users"""
        if db_field.name == 'performed_by':
            kwargs['queryset'] = db_field.related_model.objects.filter(is_staff=True)
        return super().formfield_for_foreignkey(db_field, request, **kwargs)

    def company_name(self, obj):
        return obj.subscription.hr_profile.company.name if obj.subscription.hr_profile.company else "No Company"
    company_name.short_description = 'Company'

    def has_add_permission(self, request):
        return False

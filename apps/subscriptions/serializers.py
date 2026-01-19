from rest_framework import serializers
from .models import (
    SubscriptionPlan,
    CompanySubscription,
    SubscriptionHistory
)


class SubscriptionPlanSerializer(serializers.ModelSerializer):
    """Serializer for subscription plans"""

    duration_days = serializers.SerializerMethodField()
    plan_type_display = serializers.CharField(source='get_plan_type_display', read_only=True)

    class Meta:
        model = SubscriptionPlan
        fields = [
            'id',
            'name',
            'description',
            'plan_type',
            'plan_type_display',
            'duration_days',
            'price',
            'is_unlimited',
            'credits_limit',
            'is_active',
            'created_at',
        ]
        read_only_fields = ['id', 'created_at']

    def get_duration_days(self, obj):
        return obj.get_duration_days()


class SubscriptionHistorySerializer(serializers.ModelSerializer):
    """Serializer for subscription history"""

    performed_by_name = serializers.SerializerMethodField()

    class Meta:
        model = SubscriptionHistory
        fields = [
            'id',
            'action',
            'performed_by',
            'performed_by_name',
            'details',
            'notes',
            'created_at',
        ]

    def get_performed_by_name(self, obj):
        if obj.performed_by:
            return obj.performed_by.username
        return None


class CompanySubscriptionSerializer(serializers.ModelSerializer):
    """Serializer for company subscriptions"""

    plan = SubscriptionPlanSerializer(read_only=True)
    plan_id = serializers.UUIDField(write_only=True, required=False)

    company_name = serializers.CharField(source='hr_profile.company_name', read_only=True)
    company_email = serializers.CharField(source='hr_profile.user.email', read_only=True)

    status_display = serializers.CharField(source='get_status_display', read_only=True)
    days_remaining = serializers.SerializerMethodField()
    warning_level = serializers.SerializerMethodField()
    is_currently_active = serializers.SerializerMethodField()
    has_unlimited = serializers.SerializerMethodField()

    approved_by_name = serializers.SerializerMethodField()
    cancelled_by_name = serializers.SerializerMethodField()

    class Meta:
        model = CompanySubscription
        fields = [
            'id',
            'hr_profile',
            'company_name',
            'company_email',
            'plan',
            'plan_id',
            'status',
            'status_display',
            'start_date',
            'end_date',
            'days_remaining',
            'warning_level',
            'is_currently_active',
            'has_unlimited',
            'credits_used',
            'payment_reference',
            'approved_by',
            'approved_by_name',
            'approved_at',
            'cancelled_by',
            'cancelled_by_name',
            'cancelled_at',
            'cancellation_reason',
            'admin_notes',
            'created_at',
            'updated_at',
        ]
        read_only_fields = [
            'id',
            'credits_used',
            'approved_at',
            'cancelled_at',
            'created_at',
            'updated_at',
        ]

    def get_days_remaining(self, obj):
        return obj.days_until_expiry()

    def get_warning_level(self, obj):
        return obj.get_expiry_warning_level()

    def get_is_currently_active(self, obj):
        return obj.is_active()

    def get_has_unlimited(self, obj):
        return obj.has_unlimited_credits()

    def get_approved_by_name(self, obj):
        if obj.approved_by:
            return obj.approved_by.username
        return None

    def get_cancelled_by_name(self, obj):
        if obj.cancelled_by:
            return obj.cancelled_by.username
        return None


class CompanySubscriptionDetailSerializer(CompanySubscriptionSerializer):
    """Detailed serializer with history"""

    history = SubscriptionHistorySerializer(many=True, read_only=True)

    class Meta(CompanySubscriptionSerializer.Meta):
        fields = CompanySubscriptionSerializer.Meta.fields + ['history']


class SubscriptionStatusSerializer(serializers.Serializer):
    """Serializer for subscription status response"""

    has_subscription = serializers.BooleanField()
    status = serializers.CharField(allow_null=True)
    plan = serializers.CharField(allow_null=True)
    plan_type = serializers.CharField(allow_null=True)
    expires_at = serializers.DateTimeField(allow_null=True)
    days_remaining = serializers.IntegerField(allow_null=True)
    is_unlimited = serializers.BooleanField()
    credits_used = serializers.IntegerField()
    credits_limit = serializers.IntegerField(allow_null=True)
    warning_level = serializers.CharField(allow_null=True)

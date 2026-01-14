from rest_framework import serializers
from .models import AppVersion, VersionCheckLog


class AppVersionSerializer(serializers.ModelSerializer):
    """Serializer for AppVersion model"""

    class Meta:
        model = AppVersion
        fields = [
            'id',
            'version_number',
            'version_code',
            'platform',
            'is_mandatory',
            'is_active',
            'minimum_supported_version',
            'minimum_version_code',
            'release_notes',
            'release_date',
            'download_url_android',
            'download_url_ios',
            'features',
            'bug_fixes',
            'created_at',
            'updated_at'
        ]
        read_only_fields = [
            'id',
            'version_code',
            'minimum_version_code',
            'created_at',
            'updated_at'
        ]


class VersionCheckRequestSerializer(serializers.Serializer):
    """Serializer for version check request"""
    current_version = serializers.CharField(
        max_length=20,
        required=True,
        help_text="Current app version (e.g., 1.0.0)"
    )

    platform = serializers.ChoiceField(
        choices=['ANDROID', 'IOS', 'android', 'ios'],
        required=True,
        help_text="Platform: ANDROID or IOS"
    )

    device_info = serializers.JSONField(
        required=False,
        allow_null=True,
        help_text="Optional device information"
    )

    def validate_current_version(self, value):
        """Validate version format"""
        import re
        pattern = r'^\d+\.\d+\.\d+$'
        if not re.match(pattern, value):
            raise serializers.ValidationError(
                "Version must be in format X.Y.Z (e.g., 1.0.0)"
            )
        return value

    def validate_platform(self, value):
        """Normalize platform to uppercase"""
        return value.upper()


class VersionCheckResponseSerializer(serializers.Serializer):
    """Serializer for version check response"""
    update_available = serializers.BooleanField(
        help_text="Whether an update is available"
    )

    is_mandatory = serializers.BooleanField(
        help_text="Whether the update is mandatory"
    )

    force_update = serializers.BooleanField(
        help_text="Whether user is below minimum supported version and must update"
    )

    latest_version = serializers.CharField(
        max_length=20,
        allow_null=True,
        help_text="Latest available version"
    )

    latest_version_code = serializers.IntegerField(
        allow_null=True,
        help_text="Latest version code"
    )

    current_version_code = serializers.IntegerField(
        help_text="Current version code"
    )

    release_notes = serializers.CharField(
        allow_null=True,
        help_text="What's new in the latest version"
    )

    download_url = serializers.URLField(
        allow_null=True,
        help_text="Download URL for app store"
    )

    features = serializers.ListField(
        child=serializers.CharField(),
        allow_null=True,
        help_text="List of new features"
    )

    bug_fixes = serializers.ListField(
        child=serializers.CharField(),
        allow_null=True,
        help_text="List of bug fixes"
    )

    message = serializers.CharField(
        allow_null=True,
        help_text="User-friendly message"
    )


class VersionCheckLogSerializer(serializers.ModelSerializer):
    """Serializer for VersionCheckLog model"""
    user_email = serializers.EmailField(source='user.email', read_only=True, allow_null=True)

    class Meta:
        model = VersionCheckLog
        fields = [
            'id',
            'user',
            'user_email',
            'current_version',
            'current_version_code',
            'platform',
            'update_available',
            'is_mandatory',
            'force_update',
            'latest_version',
            'device_info',
            'ip_address',
            'checked_at'
        ]
        read_only_fields = fields

from django.db import models
from django.core.validators import RegexValidator
from django.utils import timezone
import uuid


class AppVersion(models.Model):
    """
    Manage app versions for update notifications and mandatory updates
    """
    PLATFORM_CHOICES = [
        ('ANDROID', 'Android'),
        ('IOS', 'iOS'),
        ('BOTH', 'Both Platforms'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    # Version information
    version_number = models.CharField(
        max_length=20,
        validators=[
            RegexValidator(
                regex=r'^\d+\.\d+\.\d+$',
                message='Version must be in format X.Y.Z (e.g., 1.0.0)',
            )
        ],
        help_text="Version in format X.Y.Z (e.g., 1.0.0, 1.1.0)"
    )

    version_code = models.PositiveIntegerField(
        help_text="Numeric version code for comparison (e.g., 100 for 1.0.0, 110 for 1.1.0)"
    )

    platform = models.CharField(
        max_length=10,
        choices=PLATFORM_CHOICES,
        default='BOTH'
    )

    # Update settings
    is_mandatory = models.BooleanField(
        default=False,
        help_text="If true, users must update to continue using the app"
    )

    is_active = models.BooleanField(
        default=True,
        help_text="Mark as active to make this the latest version"
    )

    # Minimum supported version
    minimum_supported_version = models.CharField(
        max_length=20,
        blank=True,
        null=True,
        validators=[
            RegexValidator(
                regex=r'^\d+\.\d+\.\d+$',
                message='Version must be in format X.Y.Z (e.g., 1.0.0)',
            )
        ],
        help_text="Users below this version will be forced to update"
    )

    minimum_version_code = models.PositiveIntegerField(
        blank=True,
        null=True,
        help_text="Numeric code for minimum supported version"
    )

    # Release information
    release_notes = models.TextField(
        max_length=1000,
        help_text="What's new in this version (shown to users)"
    )

    release_date = models.DateTimeField(
        default=timezone.now,
        help_text="When this version was released"
    )

    # Download links
    download_url_android = models.URLField(
        max_length=500,
        blank=True,
        null=True,
        help_text="Play Store URL for Android"
    )

    download_url_ios = models.URLField(
        max_length=500,
        blank=True,
        null=True,
        help_text="App Store URL for iOS"
    )

    # Additional features
    features = models.JSONField(
        default=list,
        blank=True,
        help_text="List of new features in this version"
    )

    bug_fixes = models.JSONField(
        default=list,
        blank=True,
        help_text="List of bugs fixed in this version"
    )

    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.CharField(max_length=100, blank=True, null=True)

    class Meta:
        ordering = ['-version_code', '-created_at']
        verbose_name = 'App Version'
        verbose_name_plural = 'App Versions'
        unique_together = ['version_number', 'platform']

    def __str__(self):
        mandatory_tag = " [MANDATORY]" if self.is_mandatory else ""
        active_tag = " [ACTIVE]" if self.is_active else ""
        return f"{self.version_number} ({self.get_platform_display()}){mandatory_tag}{active_tag}"

    def save(self, *args, **kwargs):
        # Auto-generate version_code from version_number if not provided
        if not self.version_code and self.version_number:
            self.version_code = self.calculate_version_code(self.version_number)

        # Auto-generate minimum_version_code if minimum_supported_version is provided
        if self.minimum_supported_version and not self.minimum_version_code:
            self.minimum_version_code = self.calculate_version_code(self.minimum_supported_version)

        super().save(*args, **kwargs)

    @staticmethod
    def calculate_version_code(version_string):
        """
        Convert version string (e.g., '1.2.3') to integer code (e.g., 10203)
        1.0.0 -> 10000
        1.1.0 -> 10100
        1.2.3 -> 10203
        """
        try:
            major, minor, patch = map(int, version_string.split('.'))
            return (major * 10000) + (minor * 100) + patch
        except:
            return 0

    @staticmethod
    def compare_versions(version1, version2):
        """
        Compare two version strings
        Returns: 1 if version1 > version2, -1 if version1 < version2, 0 if equal
        """
        code1 = AppVersion.calculate_version_code(version1)
        code2 = AppVersion.calculate_version_code(version2)

        if code1 > code2:
            return 1
        elif code1 < code2:
            return -1
        else:
            return 0

    def get_download_url(self, platform=None):
        """Get appropriate download URL based on platform"""
        if platform == 'ANDROID' or self.platform == 'ANDROID':
            return self.download_url_android
        elif platform == 'IOS' or self.platform == 'IOS':
            return self.download_url_ios
        else:
            return self.download_url_android or self.download_url_ios


class VersionCheckLog(models.Model):
    """
    Log version check requests for analytics
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    user = models.ForeignKey(
        'authentication.User',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='version_checks'
    )

    current_version = models.CharField(max_length=20)
    current_version_code = models.PositiveIntegerField()

    platform = models.CharField(max_length=10)

    update_available = models.BooleanField(default=False)
    is_mandatory = models.BooleanField(default=False)
    force_update = models.BooleanField(default=False)

    latest_version = models.CharField(max_length=20, blank=True, null=True)

    # Device information (optional)
    device_info = models.JSONField(default=dict, blank=True)

    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(blank=True, null=True)

    checked_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-checked_at']
        verbose_name = 'Version Check Log'
        verbose_name_plural = 'Version Check Logs'

    def __str__(self):
        user_info = self.user.email if self.user else "Anonymous"
        return f"{user_info} - {self.current_version} ({self.platform}) - {self.checked_at}"

from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.permissions import AllowAny
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi
from django.utils import timezone

from .models import AppVersion, VersionCheckLog
from .serializers import (
    VersionCheckRequestSerializer,
    VersionCheckResponseSerializer,
    AppVersionSerializer
)


def get_client_ip(request):
    """Get client IP address from request"""
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0]
    else:
        ip = request.META.get('REMOTE_ADDR')
    return ip


class CheckAppVersionView(APIView):
    """
    API endpoint to check if app update is available

    This endpoint compares the user's current app version with the latest available version
    and returns whether an update is available, if it's mandatory, and download information.
    """
    permission_classes = [AllowAny]

    @swagger_auto_schema(
        request_body=VersionCheckRequestSerializer,
        responses={
            200: openapi.Response(
                description="Version check successful",
                schema=VersionCheckResponseSerializer
            ),
            400: "Bad Request - Invalid version format or platform"
        },
        operation_description="""
        Check for app updates

        Request body should contain:
        - current_version: Current app version (e.g., "1.0.0")
        - platform: Platform type ("ANDROID" or "IOS")
        - device_info: Optional device information (JSON object)

        Returns:
        - update_available: Whether an update is available
        - is_mandatory: Whether the update is mandatory
        - force_update: Whether user must update (below minimum supported version)
        - latest_version: Latest available version
        - release_notes: What's new in the latest version
        - download_url: App store download URL
        - features: List of new features
        - bug_fixes: List of bug fixes
        """,
        tags=['App Version']
    )
    def post(self, request):
        # Validate request data
        serializer = VersionCheckRequestSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(
                {
                    'error': 'Invalid request data',
                    'details': serializer.errors
                },
                status=status.HTTP_400_BAD_REQUEST
            )

        current_version = serializer.validated_data['current_version']
        platform = serializer.validated_data['platform']
        device_info = serializer.validated_data.get('device_info', {})

        # Calculate current version code
        current_version_code = AppVersion.calculate_version_code(current_version)

        # Get latest active version for the platform
        latest_version_obj = AppVersion.objects.filter(
            platform__in=[platform, 'BOTH'],
            is_active=True
        ).order_by('-version_code').first()

        # Initialize response data
        response_data = {
            'update_available': False,
            'is_mandatory': False,
            'force_update': False,
            'latest_version': current_version,
            'latest_version_code': current_version_code,
            'current_version_code': current_version_code,
            'release_notes': None,
            'download_url': None,
            'features': [],
            'bug_fixes': [],
            'message': 'You are using the latest version'
        }

        # If no active version exists in database
        if not latest_version_obj:
            # Log the check
            self._log_version_check(
                request=request,
                current_version=current_version,
                current_version_code=current_version_code,
                platform=platform,
                device_info=device_info,
                **response_data
            )

            return Response(response_data, status=status.HTTP_200_OK)

        # Check if update is available
        update_available = latest_version_obj.version_code > current_version_code

        if update_available:
            # Check if force update is required (below minimum supported version)
            force_update = False
            if latest_version_obj.minimum_version_code:
                force_update = current_version_code < latest_version_obj.minimum_version_code

            # Prepare response data
            response_data = {
                'update_available': True,
                'is_mandatory': latest_version_obj.is_mandatory or force_update,
                'force_update': force_update,
                'latest_version': latest_version_obj.version_number,
                'latest_version_code': latest_version_obj.version_code,
                'current_version_code': current_version_code,
                'release_notes': latest_version_obj.release_notes,
                'download_url': latest_version_obj.get_download_url(platform),
                'features': latest_version_obj.features or [],
                'bug_fixes': latest_version_obj.bug_fixes or [],
                'message': self._get_update_message(
                    latest_version_obj.is_mandatory,
                    force_update
                )
            }

        # Log the version check
        self._log_version_check(
            request=request,
            current_version=current_version,
            current_version_code=current_version_code,
            platform=platform,
            device_info=device_info,
            update_available=response_data['update_available'],
            is_mandatory=response_data['is_mandatory'],
            force_update=response_data['force_update'],
            latest_version=response_data['latest_version'],
        )


        return Response(response_data, status=status.HTTP_200_OK)

    def _get_update_message(self, is_mandatory, force_update):
        """Generate user-friendly update message"""
        if force_update:
            return "Your app version is no longer supported. Please update to continue using the app."
        elif is_mandatory:
            return "A mandatory update is available. Please update to continue using the app."
        else:
            return "A new version is available with exciting features and improvements!"

    def _log_version_check(self, request, current_version, current_version_code,
                          platform, device_info, update_available, is_mandatory,
                          force_update, latest_version,):
        """Log version check for analytics"""
        try:
            # Get user if authenticated
            user = request.user if request.user.is_authenticated else None

            # Create log entry
            VersionCheckLog.objects.create(
                user=user,
                current_version=current_version,
                current_version_code=current_version_code,
                platform=platform,
                update_available=update_available,
                is_mandatory=is_mandatory,
                force_update=force_update,
                latest_version=latest_version,
                device_info=device_info,
                ip_address=get_client_ip(request),
                user_agent=request.META.get('HTTP_USER_AGENT', '')
            )
        except Exception as e:
            # Don't fail the request if logging fails
            print(f"Error logging version check: {str(e)}")


class LatestVersionView(APIView):
    """
    Get latest app version information without version comparison

    This endpoint returns the latest available version for a platform
    without requiring the current version.
    """
    permission_classes = [AllowAny]

    @swagger_auto_schema(
        manual_parameters=[
            openapi.Parameter(
                'platform',
                openapi.IN_QUERY,
                description="Platform (ANDROID or IOS)",
                type=openapi.TYPE_STRING,
                enum=['ANDROID', 'IOS', 'android', 'ios'],
                required=True
            )
        ],
        responses={
            200: AppVersionSerializer,
            404: "No active version found for this platform"
        },
        operation_description="Get latest app version information for a platform",
        tags=['App Version']
    )
    def get(self, request):
        platform = request.query_params.get('platform', '').upper()

        if platform not in ['ANDROID', 'IOS']:
            return Response(
                {'error': 'Invalid platform. Must be ANDROID or IOS'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Get latest active version
        latest_version = AppVersion.objects.filter(
            platform__in=[platform, 'BOTH'],
            is_active=True
        ).order_by('-version_code').first()

        if not latest_version:
            return Response(
                {'error': 'No active version found for this platform'},
                status=status.HTTP_404_NOT_FOUND
            )

        serializer = AppVersionSerializer(latest_version)
        return Response(serializer.data, status=status.HTTP_200_OK)


class VersionHistoryView(APIView):
    """
    Get version history for a platform

    Returns all versions (active and inactive) for analytics or display purposes.
    """
    permission_classes = [AllowAny]

    @swagger_auto_schema(
        manual_parameters=[
            openapi.Parameter(
                'platform',
                openapi.IN_QUERY,
                description="Platform (ANDROID, IOS, or BOTH)",
                type=openapi.TYPE_STRING,
                enum=['ANDROID', 'IOS', 'BOTH', 'android', 'ios', 'both'],
                required=False
            ),
            openapi.Parameter(
                'active_only',
                openapi.IN_QUERY,
                description="Show only active versions",
                type=openapi.TYPE_BOOLEAN,
                required=False,
                default=False
            )
        ],
        responses={
            200: AppVersionSerializer(many=True)
        },
        operation_description="Get version history for a platform",
        tags=['App Version']
    )
    def get(self, request):
        platform = request.query_params.get('platform', '').upper()
        active_only = request.query_params.get('active_only', 'false').lower() == 'true'

        # Build query
        queryset = AppVersion.objects.all()

        if platform and platform in ['ANDROID', 'IOS', 'BOTH']:
            queryset = queryset.filter(platform__in=[platform, 'BOTH'])

        if active_only:
            queryset = queryset.filter(is_active=True)

        queryset = queryset.order_by('-version_code')

        serializer = AppVersionSerializer(queryset, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

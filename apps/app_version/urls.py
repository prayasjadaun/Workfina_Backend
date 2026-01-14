from django.urls import path
from .views import (
    CheckAppVersionView,
    LatestVersionView,
    VersionHistoryView
)

app_name = 'app_version'

urlpatterns = [
    # Main version check endpoint
    path('check/', CheckAppVersionView.as_view(), name='check_version'),

    # Get latest version info
    path('latest/', LatestVersionView.as_view(), name='latest_version'),

    # Get version history
    path('history/', VersionHistoryView.as_view(), name='version_history'),
]

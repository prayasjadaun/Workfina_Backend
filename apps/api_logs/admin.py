from django.contrib import admin
from .models import APILog

@admin.register(APILog)
class APILogAdmin(admin.ModelAdmin):
    list_display = ['timestamp', 'method', 'endpoint', 'response_status', 'user', 'response_time', 'ip_address']
    list_filter = ['method', 'response_status', 'timestamp']
    search_fields = ['endpoint', 'user__email', 'ip_address']
    readonly_fields = ['timestamp', 'response_time']
    date_hierarchy = 'timestamp'
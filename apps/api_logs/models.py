from django.db import models
from django.contrib.auth import get_user_model

User = get_user_model()

class APILog(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True)
    method = models.CharField(max_length=10)
    endpoint = models.URLField()
    request_data = models.JSONField(null=True, blank=True)
    response_status = models.IntegerField()
    response_data = models.JSONField(null=True, blank=True)
    ip_address = models.GenericIPAddressField()
    user_agent = models.TextField(blank=True)
    timestamp = models.DateTimeField(auto_now_add=True)
    response_time = models.FloatField()
    
    class Meta:
        ordering = ['-timestamp']
        
    def __str__(self):
        return f"{self.method} {self.endpoint} - {self.response_status}"
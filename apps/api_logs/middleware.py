import json
import time
from django.utils.deprecation import MiddlewareMixin
from .models import APILog

class APILoggingMiddleware(MiddlewareMixin):
    def process_request(self, request):
        request.start_time = time.time()
        
        # Cache request body before it's consumed by the view
        if request.method in ['POST', 'PUT', 'PATCH']:
            try:
                content_type = request.META.get('CONTENT_TYPE', '')
                if 'application/json' in content_type and hasattr(request, 'body'):
                    request._cached_body = request.body
            except:
                pass
        
    def process_response(self, request, response):
        if request.path.startswith('/admin/') or request.path.startswith('/static/'):
            return response
            
        response_time = (time.time() - getattr(request, 'start_time', time.time())) * 1000
        
        request_data = None
        if request.method in ['POST', 'PUT', 'PATCH']:
            try:
                content_type = request.META.get('CONTENT_TYPE', '')
                
                # For JSON requests - use cached body
                if 'application/json' in content_type:
                    if hasattr(request, '_cached_body'):
                        request_data = json.loads(request._cached_body.decode('utf-8'))
                
                # For multipart/form-data
                elif 'multipart/form-data' in content_type:
                    request_data = {}
                    if hasattr(request, 'POST') and request.POST:
                        for key, value in request.POST.items():
                            request_data[key] = value
                    if hasattr(request, 'FILES') and request.FILES:
                        for key, file in request.FILES.items():
                            request_data[key] = f"<FILE: {file.name}>"
                    
            except Exception as e:
                request_data = {"_error": str(e)}
        
        # Capture response data
        response_data = None
        try:
            if hasattr(response, 'content') and response.get('Content-Type', '').startswith('application/json'):
                response_data = json.loads(response.content.decode('utf-8'))
        except:
            pass
        
        # Fix user detection
        user = None
        if hasattr(request, 'user') and request.user.is_authenticated:
            user = request.user
        
        # Debug prints
        print(f'[API DEBUG] {request.method} {request.get_full_path()}')
        print(f'[API DEBUG] Content-Type: {request.META.get("CONTENT_TYPE", "")}')
        print(f'[API DEBUG] Request Data: {request_data}')
        print(f'[API DEBUG] Response Status: {response.status_code}')
        print(f'[API DEBUG] Response Data: {response_data}')
        
        APILog.objects.create(
            user=user,
            method=request.method,
            endpoint=request.get_full_path(),
            request_data=request_data,
            response_status=response.status_code,
            response_data=response_data,
            ip_address=self.get_client_ip(request),
            user_agent=request.META.get('HTTP_USER_AGENT', ''),
            response_time=response_time
        )
        
        return response
    
    def get_client_ip(self, request):
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR', '127.0.0.1')
        return ip
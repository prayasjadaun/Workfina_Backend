from django.urls import path
from .views import SendOTPView, VerifyOTPView, LoginView, CreateAccountView, LogoutView, UpdateRoleView, RefreshTokenView, UpdateFCMTokenView

urlpatterns = [
    path('send-otp/', SendOTPView.as_view()),
    path('verify-otp/', VerifyOTPView.as_view()),
    path('create-account/', CreateAccountView.as_view()),
    path('login/', LoginView.as_view()),
    path('logout/', LogoutView.as_view()),
    path('update-role/', UpdateRoleView.as_view()),
    path('refresh/', RefreshTokenView.as_view()),
    path('update-fcm-token/', UpdateFCMTokenView.as_view()),
]
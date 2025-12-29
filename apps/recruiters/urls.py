from django.urls import path
from .views import HRRegistrationView, hr_profile, update_hr_profile

urlpatterns = [
    path('register/', HRRegistrationView.as_view(), name='hr-register'),
    path('profile/', hr_profile, name='hr-profile'),
        path('profile/update/', update_hr_profile, name='update-hr-profile'),  
]
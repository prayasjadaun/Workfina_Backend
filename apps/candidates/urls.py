from django.urls import path
from .views import CandidateRegistrationView, CandidateListView, unlock_candidate, get_unlocked_candidates, get_candidate_profile

urlpatterns = [
    path('register/', CandidateRegistrationView.as_view(), name='candidate-register'),
    path('profile/', get_candidate_profile, name='candidate-profile'),
    path('list/', CandidateListView.as_view(), name='candidate-list'),
    path('<uuid:candidate_id>/unlock/', unlock_candidate, name='unlock-candidate'),
    path('unlocked/', get_unlocked_candidates, name='unlocked-candidates'),
]
from django.urls import path
from .views import *

urlpatterns = [
    path('register/', CandidateRegistrationView.as_view(), name='candidate-register'),
    path('profile/', get_candidate_profile, name='candidate-profile'),
    path('profile/update/', update_candidate_profile, name='candidate-profile-update'),  
    path('list/', CandidateListView.as_view(), name='candidate-list'),
    path('<uuid:candidate_id>/unlock/', unlock_candidate, name='unlock-candidate'),
    path('unlocked/', get_unlocked_candidates, name='unlocked-candidates'),
    path('filter-options/', get_filter_options, name='candidate-filter-options'),
    path('<uuid:candidate_id>/note/', add_candidate_note, name='add-candidate-note'),
    path('<uuid:candidate_id>/followup/', add_candidate_followup, name='add-candidate-followup'),
    path('<uuid:candidate_id>/notes-followups/', get_candidate_notes_followups, name='get-candidate-notes-followups'),
    
]
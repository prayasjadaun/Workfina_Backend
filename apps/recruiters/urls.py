from django.urls import path
from .views import (
    HRRegistrationView, hr_profile, update_hr_profile,
    filter_candidates, get_all_recruiters,
    get_cities, get_states, get_countries, add_custom_location,
    search_companies, check_company_location,
    search_companies_by_website, 
)

urlpatterns = [
    path('register/', HRRegistrationView.as_view(), name='hr-register'),
    path('profile/', hr_profile, name='hr-profile'),
    path('profile/update/', update_hr_profile, name='update-hr-profile'),
    path('candidates/filter/', filter_candidates, name='filter-candidates'),
    path('all/', get_all_recruiters, name='get-all-recruiters'),

    # Company search/autocomplete endpoints
    path('companies/search/', search_companies, name='search-companies'),
    path('companies/search-by-website/', search_companies_by_website, name='search-companies-by-website'),
    path('companies/check-location/', check_company_location, name='check-company-location'),

    # Location dropdown endpoints
    path('locations/cities/', get_cities, name='get-cities'),
    path('locations/states/', get_states, name='get-states'),
    path('locations/countries/', get_countries, name='get-countries'),
    path('locations/custom/', add_custom_location, name='add-custom-location'),
]
from django.urls import path
from .views import (
    HRRegistrationView, hr_profile, update_hr_profile,
    filter_candidates, get_all_recruiters,
    add_custom_location,
    search_companies, check_company_location,
    search_companies_by_website,
    search_countries, search_states, search_cities,
)

urlpatterns = [
    path('register/', HRRegistrationView.as_view(), name='hr-register'),
    path('profile/', hr_profile, name='hr-profile'),
    path('profile/update/', update_hr_profile, name='update-hr-profile'),
    path('candidates/filter/', filter_candidates, name='filter-candidates'),
    path('all/', get_all_recruiters, name='get-all-recruiters'),

    # Company search/autocomplete endpoints
    path('companies/search/', search_companies, name='search-companies'),
    path('companies/check-location/', check_company_location, name='check-company-location'),
    path('companies/search-by-website/', search_companies_by_website, name='search-companies-by-website'),

    # Location search endpoints
    path('locations/search/countries/', search_countries, name='search-countries'),
    path('locations/search/states/', search_states, name='search-states'),
    path('locations/search/cities/', search_cities, name='search-cities'),
    path('locations/custom/', add_custom_location, name='add-custom-location'),
]
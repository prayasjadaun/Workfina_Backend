from rest_framework import status, generics
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django.db.models import Q
from .models import HRProfile
from .serializers import HRRegistrationSerializer, HRProfileSerializer
from apps.candidates.models import Candidate, UnlockHistory
from apps.candidates.serializers import MaskedCandidateSerializer, FullCandidateSerializer

class HRRegistrationView(generics.CreateAPIView):
    serializer_class = HRRegistrationSerializer
    permission_classes = [IsAuthenticated]

    def post(self, request, *args, **kwargs):
        if request.user.role != 'hr':
            return Response({
                'error': 'Only HR users can create HR profiles'
            }, status=status.HTTP_403_FORBIDDEN)

        # If profile already exists, update it instead of creating new
        if hasattr(request.user, 'hr_profile'):
            profile = request.user.hr_profile
            serializer = HRProfileSerializer(profile, data=request.data, partial=True)
            if serializer.is_valid():
                serializer.save()
                return Response(serializer.data, status=status.HTTP_200_OK)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        return super().post(request, *args, **kwargs)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def hr_profile(request):
    if request.user.role != 'hr':
        return Response({
            'error': 'Only HR users can access this'
        }, status=status.HTTP_403_FORBIDDEN)
    
    try:
        profile = request.user.hr_profile
        serializer = HRProfileSerializer(profile)
        return Response(serializer.data)
    except HRProfile.DoesNotExist:
        return Response({
            'error': 'HR profile not found'
        }, status=status.HTTP_404_NOT_FOUND)

@api_view(['PATCH'])
@permission_classes([IsAuthenticated])
def update_hr_profile(request):
    if request.user.role != 'hr':
        return Response({
            'error': 'Only HR users can access this'
        }, status=status.HTTP_403_FORBIDDEN)
    
    try:
        profile = request.user.hr_profile
        serializer = HRProfileSerializer(profile, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    except HRProfile.DoesNotExist:
        return Response({
            'error': 'HR profile not found'
        }, status=status.HTTP_404_NOT_FOUND)

from django.core.paginator import Paginator


@api_view(['GET'])
def get_all_recruiters(request):
    """Get all recruiters/HR profiles - Public endpoint"""

    # No authentication required - anyone can view recruiters list

    # Get pagination parameters
    page = int(request.query_params.get('page', 1))
    page_size = int(request.query_params.get('page_size', 20))

    # Get all HR profiles
    queryset = HRProfile.objects.select_related('user').all()

    # Optional: Filter by verification status
    is_verified = request.query_params.get('is_verified')
    if is_verified is not None:
        queryset = queryset.filter(is_verified=is_verified.lower() == 'true')

    # Apply pagination
    paginator = Paginator(queryset, page_size)
    recruiters_page = paginator.get_page(page)

    # Serialize recruiters
    serializer = HRProfileSerializer(recruiters_page, many=True, context={'request': request})

    return Response({
        'success': True,
        'recruiters': serializer.data,
        'pagination': {
            'current_page': page,
            'page_size': page_size,
            'total_pages': paginator.num_pages,
            'total_count': paginator.count,
            'has_next': recruiters_page.has_next(),
            'has_previous': recruiters_page.has_previous(),
        }
    })


def normalize_slug(value: str) -> str:
    """
    Converts slug to human readable text
    madhya-pradesh -> Madhya Pradesh
    uttar_pradesh  -> Uttar Pradesh
    """
    return (
        value
        .replace('-', ' ')
        .replace('_', ' ')
        .strip()
        .title()
    )


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def filter_candidates(request):
    """Filter candidates API for HR users"""
    
    if request.user.role != 'hr':
        return Response({
            'error': 'Only HR users can access this'
        }, status=status.HTTP_403_FORBIDDEN)
    
    try:
        hr_profile = request.user.hr_profile
        if not hr_profile.is_verified:
            return Response({
                'error': 'Company verification pending. Cannot view candidates.'
            }, status=status.HTTP_403_FORBIDDEN)
    except HRProfile.DoesNotExist:
        return Response({
            'error': 'HR profile not found'
        }, status=status.HTTP_404_NOT_FOUND)
    
    # Get filter parameters
    role = request.query_params.get('role')
    min_experience = request.query_params.get('min_experience')
    max_experience = request.query_params.get('max_experience')
    min_age = request.query_params.get('min_age')
    max_age = request.query_params.get('max_age')
    city = request.query_params.get('city')
    state = request.query_params.get('state')
    country = request.query_params.get('country')
    religion = request.query_params.get('religion')
    skills = request.query_params.get('skills')
    min_ctc = request.query_params.get('min_ctc')
    max_ctc = request.query_params.get('max_ctc')
    show_locked_only = request.query_params.get('show_locked_only', 'false').lower() == 'true'
    
    # Pagination
    page = int(request.query_params.get('page', 1))
    page_size = int(request.query_params.get('page_size', 20))
    
    # Base queryset - Only show actual candidates, not HR/Recruiter profiles
    queryset = Candidate.objects.filter(
        is_active=True,
        user__role='candidate'
    ).select_related(
        'role', 'religion', 'country', 'state', 'city'
    )
    
    # Apply dynamic filters
    if role and role != 'All':
        queryset = queryset.filter(role__name__iexact=role)
        
    if min_experience:
        try:
            queryset = queryset.filter(experience_years__gte=int(min_experience))
        except ValueError:
            pass
            
    if max_experience:
        try:
            queryset = queryset.filter(experience_years__lte=int(max_experience))
        except ValueError:
            pass
            
    if min_age:
        try:
            queryset = queryset.filter(age__gte=int(min_age))
        except ValueError:
            pass
            
    if max_age:
        try:
            queryset = queryset.filter(age__lte=int(max_age))
        except ValueError:
            pass
            
    if city:
        normalized_city = normalize_slug(city)
        queryset = queryset.filter(city__name__iexact=normalized_city)

    if state:
        normalized_state = normalize_slug(state)
        queryset = queryset.filter(state__name__iexact=normalized_state)

    if country:
        normalized_country = normalize_slug(country)
        queryset = queryset.filter(country__name__iexact=normalized_country)

            
    if religion and religion != 'All':
        queryset = queryset.filter(
        religion__name__iexact=normalize_slug(religion)
    )
        
    if skills:
        queryset = queryset.filter(skills__icontains=skills)
        
    if min_ctc:
        try:
            queryset = queryset.filter(expected_ctc__gte=float(min_ctc))
        except (ValueError, TypeError):
            pass
            
    if max_ctc:
        try:
            queryset = queryset.filter(expected_ctc__lte=float(max_ctc))
        except (ValueError, TypeError):
            pass
    
    # Get unlocked candidate IDs
    unlocked_ids = set(UnlockHistory.objects.filter(
        hr_user=request.user.hr_profile
    ).values_list('candidate_id', flat=True))
    
    # Filter to show only locked candidates if requested
    if show_locked_only:
        queryset = queryset.exclude(id__in=unlocked_ids)
    
    # Apply pagination
    paginator = Paginator(queryset, page_size)
    candidates_page = paginator.get_page(page)
    
    # Serialize candidates
    candidates_data = []
    for candidate in candidates_page:
        if candidate.id in unlocked_ids:
            serializer = FullCandidateSerializer(candidate, context={'request': request})
        else:
            serializer = MaskedCandidateSerializer(candidate, context={'request': request})
        candidates_data.append(serializer.data)
    
    return Response({
        'success': True,
        'candidates': candidates_data,
        'pagination': {
            'current_page': page,
            'page_size': page_size,
            'total_pages': paginator.num_pages,
            'total_count': paginator.count,
            'has_next': candidates_page.has_next(),
            'has_previous': candidates_page.has_previous(),
        },
        'filters_applied': {
            'role': role,
            'experience_range': f"{min_experience}-{max_experience}",
            'age_range': f"{min_age}-{max_age}",
            'location': f"{city}, {state}, {country}",
            'religion': religion,
            'skills': skills,
            'ctc_range': f"{min_ctc}-{max_ctc}"
        }
    })
    
    



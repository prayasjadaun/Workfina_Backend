from rest_framework import status, generics
from rest_framework.decorators import api_view, permission_classes,parser_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import SearchFilter
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser

from apps.recruiters.models import HRProfile
from django.contrib.auth import get_user_model
from .models import Candidate, UnlockHistory
from .serializers import (
    CandidateRegistrationSerializer,
    MaskedCandidateSerializer, 
    FullCandidateSerializer
)

User = get_user_model()

class CandidateRegistrationView(generics.CreateAPIView):
    """API for candidates to register their profile"""
    
    serializer_class = CandidateRegistrationSerializer
    permission_classes = [IsAuthenticated]
    parser_classes=[MultiPartParser, FormParser, JSONParser] # ÃƒÂ¢Ã…â€œÃ¢â‚¬Â¦ Important for file uploads

    
    def post(self, request, *args, **kwargs):
        print("=" * 50)
        print("DEBUG - Registration Request")
        print("=" * 50)
        print(f"Request DATA keys: {request.data.keys()}")
        print(f"Request FILES keys: {request.FILES.keys()}")
        print(f"Resume in FILES: {'resume' in request.FILES}")
        print(f"Video intro in FILES: {'video_intro' in request.FILES}")
        print("=" * 50)

        # Check if user is candidate
        if request.user.role != 'candidate':
            return Response({
                'error': 'Only candidates can create candidate profiles'
            }, status=status.HTTP_403_FORBIDDEN)
        
        # Check if profile already exists
        if hasattr(request.user, 'candidate_profile'):
            return Response({
                'error': 'Candidate profile already exists'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        return super().post(request, *args, **kwargs)

class CandidateListView(generics.ListAPIView):
    """API to list masked candidates with filters - For HR users"""
    
    queryset = Candidate.objects.filter(is_active=True)
    serializer_class = MaskedCandidateSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, SearchFilter]
    filterset_fields = ['role', 'city', 'state', 'religion']
    search_fields = ['skills']
    
    def get(self, request, *args, **kwargs):
        # Only HR users can view candidate list
        if request.user.role != 'hr':
            return Response({
                'error': 'Only HR users can view candidates'
            }, status=status.HTTP_403_FORBIDDEN)
        
        return super().get(request, *args, **kwargs)
    
    def get_queryset(self):
        queryset = super().get_queryset()
        
        # Experience range filter
        min_exp = self.request.query_params.get('min_experience')
        max_exp = self.request.query_params.get('max_experience')
        
        if min_exp:
            queryset = queryset.filter(experience_years__gte=min_exp)
        if max_exp:
            queryset = queryset.filter(experience_years__lte=max_exp)
            
        return queryset

    def get_serializer(self, *args, **kwargs):
        # Get unlocked candidate IDs for current HR user
        unlocked_ids = UnlockHistory.objects.filter(
            hr_user=self.request.user.hr_profile
        ).values_list('candidate_id', flat=True)
        
        # Use different serializers based on unlock status
        if hasattr(self, 'object_list'):
            serialized_data = []
            for candidate in self.object_list:
                if candidate.id in unlocked_ids:
                    serializer = FullCandidateSerializer(candidate)
                else:
                    serializer = MaskedCandidateSerializer(candidate)
                serialized_data.append(serializer.data)
            return serialized_data
        
        return super().get_serializer(*args, **kwargs)

    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        self.object_list = queryset
        serializer_data = self.get_serializer()
        return Response(serializer_data)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def unlock_candidate(request, candidate_id):
    """API to unlock candidate profile using credits - For HR users"""
    
    # Only HR users can unlock
    if request.user.role != 'hr':
        return Response({
            'error': 'Only HR users can unlock candidates'
        }, status=status.HTTP_403_FORBIDDEN)
    
    try:
        candidate = Candidate.objects.get(id=candidate_id, is_active=True)
        
        # Check if already unlocked
        if UnlockHistory.objects.filter(hr_user=request.user.hr_profile, candidate=candidate).exists():
            # Return full data if already unlocked
            serializer = FullCandidateSerializer(candidate)
            return Response({
                'success': True,
                'message': 'Already unlocked',
                'candidate': serializer.data,
                'already_unlocked': True
            })
        
        # Check wallet balance
        from apps.wallet.models import Wallet
        try:
            wallet = Wallet.objects.get(hr_profile__user=request.user)
            credits_required = 10
            
            if wallet.balance < credits_required:
                return Response({
                    'error': f'Insufficient credits. You need {credits_required} credits but have {wallet.balance}.',
                    'required_credits': credits_required,
                    'current_balance': wallet.balance
                }, status=status.HTTP_400_BAD_REQUEST)
            
            # Deduct credits
            wallet.balance -= credits_required
            wallet.total_spent += credits_required
            wallet.save()
            
            # Create unlock history
            UnlockHistory.objects.create(
                hr_user=request.user.hr_profile,
                candidate=candidate,
                credits_used=credits_required
            )
            
            # Create wallet transaction
            from apps.wallet.models import WalletTransaction
            WalletTransaction.objects.create(
                wallet=wallet,
                transaction_type='UNLOCK',
                credits_used=credits_required,
                description=f'Unlocked candidate: {candidate.masked_name}'
            )
            
            # Return full candidate data
            serializer = FullCandidateSerializer(candidate)
            return Response({
                'success': True,
                'message': 'Profile unlocked successfully',
                'candidate': serializer.data,
                'credits_used': credits_required,
                'remaining_balance': wallet.balance,
                'already_unlocked': False
            })
            
        except Wallet.DoesNotExist:
            return Response({
                'error': 'Wallet not found. Please contact support.'
            }, status=status.HTTP_400_BAD_REQUEST)
        
    except Candidate.DoesNotExist:
        return Response({
            'error': 'Candidate not found'
        }, status=status.HTTP_404_NOT_FOUND)
        
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_unlocked_candidates(request):
    """Get list of unlocked candidates with full data for HR user"""
    
    if request.user.role != 'hr':
        return Response({
            'error': 'Only HR users can access this'
        }, status=status.HTTP_403_FORBIDDEN)
    
    unlocked_histories = UnlockHistory.objects.filter(
        hr_user=request.user.hr_profile
    ).select_related('candidate')
    
    unlocked_candidates = []
    for history in unlocked_histories:
        candidate = history.candidate
        serializer = FullCandidateSerializer(candidate)
        candidate_data = serializer.data
        candidate_data['credits_used'] = history.credits_used
        unlocked_candidates.append(candidate_data)
    
    return Response({
        'success': True,
        'unlocked_candidates': unlocked_candidates
    })
    
    
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_candidate_profile(request):
    """Get candidate's own profile"""
    
    if request.user.role != 'candidate':
        return Response({
            'error': 'Only candidates can access this'
        }, status=status.HTTP_403_FORBIDDEN)
    
    try:
        candidate = Candidate.objects.get(user=request.user)
        serializer = FullCandidateSerializer(candidate, context={'request': request})  # ÃƒÂ¢Ã…â€œÃ¢â‚¬Â¦ Add context
        return Response(serializer.data)
    except Candidate.DoesNotExist:
        return Response({
            'error': 'Profile not found'
        }, status=status.HTTP_404_NOT_FOUND)
    
    # Add this to your views.py

@api_view(['PUT', 'PATCH'])
@permission_classes([IsAuthenticated])
@parser_classes([MultiPartParser, FormParser, JSONParser])

def update_candidate_profile(request):
    """Update candidate's own profile"""
    
    if request.user.role != 'candidate':
        return Response({
            'error': 'Only candidates can update their profile'
        }, status=status.HTTP_403_FORBIDDEN)
    
    try:
        candidate = Candidate.objects.get(user=request.user)
        
        # Update fields from request
        serializer = CandidateRegistrationSerializer(
            candidate, 
            data=request.data, 
            partial=True,  # Allow partial updates
            context={'request': request}
        )
        
        if serializer.is_valid():
            serializer.save()
            
            # Return updated profile
            response_serializer = FullCandidateSerializer(candidate, context={'request': request})  # ÃƒÂ¢Ã…â€œÃ¢â‚¬Â¦ Add context
            return Response({
                'success': True,
                'message': 'Profile updated successfully',
                'profile': response_serializer.data
            })
        else:
            return Response({
                'error': 'Validation failed',
                'details': serializer.errors
            }, status=status.HTTP_400_BAD_REQUEST)
            
    except Candidate.DoesNotExist:
        return Response({
            'error': 'Profile not found'
        }, status=status.HTTP_404_NOT_FOUND)
        
        
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
    education = request.query_params.get('education')
    skills = request.query_params.get('skills')
    min_ctc = request.query_params.get('min_ctc')
    max_ctc = request.query_params.get('max_ctc')
    
    # Pagination
    page = int(request.query_params.get('page', 1))
    page_size = int(request.query_params.get('page_size', 20))
    
    # Base queryset
    queryset = Candidate.objects.filter(is_active=True).select_related(
        'role', 'religion', 'country', 'state', 'city', 'education'
    )
    
    # Apply dynamic filters - Updated for FilterOption model
    if role and role != 'All':
        queryset = queryset.filter(role__name__iexact=role)
        
    if religion:
        queryset = queryset.filter(religion__name__iexact=religion)
        
    if country:
        queryset = queryset.filter(country__name__iexact=country)
        
    if state:
        queryset = queryset.filter(state__name__iexact=state)
        
    if city:
        queryset = queryset.filter(city__name__iexact=city)
        
    if education:
        queryset = queryset.filter(education__name__iexact=education)
        
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
        queryset = queryset.filter(city__name__icontains=city)
        
    if state:
        queryset = queryset.filter(state__name__icontains=state)
        
    if country:
        queryset = queryset.filter(country__name__icontains=country)
        
    if religion and religion != 'All':
        queryset = queryset.filter(religion__name__iexact=religion)
        
    if education:
        queryset = queryset.filter(education__name__icontains=education)
        
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
    
    # Apply pagination
    from django.core.paginator import Paginator
    paginator = Paginator(queryset, page_size)
    candidates_page = paginator.get_page(page)
    
    # Get unlocked candidate IDs
    unlocked_ids = set(UnlockHistory.objects.filter(
        hr_user=request.user.hr_profile
    ).values_list('candidate_id', flat=True))
    
    # Serialize candidates
    candidates_data = []
    for candidate in candidates_page:
        if candidate.id in unlocked_ids:
            serializer = FullCandidateSerializer(candidate, context={'request': request})
        else:
            serializer = MaskedCandidateSerializer(candidate)
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
            'education': education,
            'skills': skills,
            'ctc_range': f"{min_ctc}-{max_ctc}"
        }
    })        
    
    
    
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_filter_options(request):
    """Get all filter options for candidate filtering"""
    
    if request.user.role != 'hr':
        return Response({
            'error': 'Only HR users can access this'
        }, status=status.HTTP_403_FORBIDDEN)
    
    from .models import FilterCategory, FilterOption
    
    filter_type = request.query_params.get('type')
    page = int(request.query_params.get('page', 1))
    page_size = int(request.query_params.get('page_size', 20))
    search = request.query_params.get('search', '')
    
    if filter_type:
        # Get specific filter category options
        try:
            category = FilterCategory.objects.get(slug=filter_type, is_active=True)
            queryset = FilterOption.objects.filter(category=category, is_active=True)
            
            if search:
                queryset = queryset.filter(name__icontains=search)
            
            data = list(queryset.values_list('name', flat=True))
            total = len(data)
            start = (page - 1) * page_size
            end = start + page_size
            paginated_data = data[start:end]
            total_pages = (total + page_size - 1) // page_size
            
            base_url = f"/api/candidates/filter-options/?type={filter_type}&page_size={page_size}"
            if search:
                base_url += f"&search={search}"
                
            next_url = f"{base_url}&page={page + 1}" if page < total_pages else None
            previous_url = f"{base_url}&page={page - 1}" if page > 1 else None
            
            # Map filter_type to correct field name
            field_mapping = {
                'department': 'role',
                'religion': 'religion', 
                'country': 'country',
                'state': 'state',
                'city': 'city',
                'education': 'education'
            }
            
            field_name = field_mapping.get(filter_type, filter_type)
            
            return Response({
                'count': total,
                'next': next_url,
                'previous': previous_url,
                'results': [
                    {
                        'value': item, 
                        'label': item,
                        'count': Candidate.objects.filter(
                            is_active=True,
                            **{f"{field_name}__name": item}
                        ).count()
                    } for item in paginated_data
                ]
            })
        except FilterCategory.DoesNotExist:
            return Response({'error': 'Invalid filter type'}, status=400)
    
    # Return all categories with counts
    results = {}
    for category in FilterCategory.objects.filter(is_active=True):
        options_count = FilterOption.objects.filter(category=category, is_active=True).count()
        icon_url = None
        if category.icon:
            icon_url = request.build_absolute_uri(category.icon.url)
        
        results[category.slug] = {
            'total_count': options_count,
            'name': category.name,
            'icon': icon_url
        }
    
    return Response({'results': results})
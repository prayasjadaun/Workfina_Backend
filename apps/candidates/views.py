from rest_framework import status, generics
from rest_framework.decorators import api_view, permission_classes,parser_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import SearchFilter
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser

from apps.recruiters.models import HRProfile
from django.contrib.auth import get_user_model
from .models import *
from .serializers import (
    CandidateRegistrationSerializer,
    MaskedCandidateSerializer, 
    FullCandidateSerializer,
    CandidateNoteSerializer,
    CandidateFollowupSerializer,
    FilterCategorySerializer
)

User = get_user_model()

class CandidateRegistrationView(generics.CreateAPIView):
    """API for candidates to register their profile"""
    
    serializer_class = CandidateRegistrationSerializer
    permission_classes = [IsAuthenticated]
    parser_classes=[MultiPartParser, FormParser, JSONParser]

    
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
        serializer = FullCandidateSerializer(candidate, context={'request': request})  
        return Response(serializer.data)
    except Candidate.DoesNotExist:
        return Response({
            'error': 'Profile not found'
        }, status=status.HTTP_404_NOT_FOUND)
    
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
        
       # Handle work experience if provided
        work_experience_data = request.data.get('work_experiences')
        if work_experience_data:
            candidate.work_experiences.all().delete()
            
            try:
                import json
                import re
                
                # Clean the string to make it valid JSON
                clean_data = re.sub(r'(\w+):', r'"\1":', work_experience_data)
                clean_data = re.sub(r': ([^",\[\]{}]+)([,}])', r': "\1"\2', clean_data)
                clean_data = clean_data.replace(': "true"', ': true').replace(': "false"', ': false').replace(': "null"', ': null')
                
                work_exp_list = json.loads(clean_data)
                for exp_data in work_exp_list:
                    WorkExperience.objects.create(
                        candidate=candidate,
                        company_name=exp_data.get('company_name', ''),
                        role_title=exp_data.get('job_role', ''),
                        start_date=f"{exp_data.get('start_year')}-{_month_to_number(exp_data.get('start_month'))}-01",
                        end_date=f"{exp_data.get('end_year')}-{_month_to_number(exp_data.get('end_month'))}-01" if not exp_data.get('is_current') and exp_data.get('end_year') not in [None, 'null'] else None,
                        is_current=exp_data.get('is_current', False),
                        location='',
                        description=''
                    )
            except Exception as e:
                print(f"Work experience parsing error: {e}")

        # Handle education if provided  
        education_data = request.data.get('educations')
        if education_data:
            candidate.educations.all().delete()
            
            try:
                import json
                import re
                
                clean_data = re.sub(r'(\w+):', r'"\1":', education_data)
                clean_data = re.sub(r': ([^",\[\]{}]+)([,}])', r': "\1"\2', clean_data)
                
                edu_list = json.loads(clean_data)
                for edu_data in edu_list:
                    Education.objects.create(
                        candidate=candidate,
                        institution_name=edu_data.get('school', ''),
                        degree=edu_data.get('degree', ''),
                        field_of_study=edu_data.get('field', ''),
                        start_year=int(edu_data.get('start_year', 2020)),
                        end_year=int(edu_data.get('end_year', 2024)),
                        is_ongoing=False,
                        grade_percentage=float(edu_data.get('grade', '0').replace('%', '')) if edu_data.get('grade') else None,
                        location=''
                    )
            except Exception as e:
                print(f"Education parsing error: {e}")
        
        # Remove work_experience and education from request.data for candidate update
        candidate_data = request.data.copy()
        candidate_data.pop('work_experience', None)
        candidate_data.pop('education', None)
        
        # Use the same serializer with the same validation logic
        serializer = CandidateRegistrationSerializer(
            candidate, 
            data=candidate_data, 
            partial=True,
            context={'request': request}
        )
        
        if serializer.is_valid():
            serializer.save()
            
            response_serializer = FullCandidateSerializer(candidate, context={'request': request})
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

def _month_to_number(month_name):
    """Convert month name to number"""
    months = {
        'January': '01', 'February': '02', 'March': '03', 'April': '04',
        'May': '05', 'June': '06', 'July': '07', 'August': '08',
        'September': '09', 'October': '10', 'November': '11', 'December': '12'
    }
    return months.get(month_name, '01')    
    
    
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
    
    # Get unlocked candidate IDs for current HR user
    unlocked_ids = set(UnlockHistory.objects.filter(
        hr_user=request.user.hr_profile
    ).values_list('candidate_id', flat=True))
    
    # Map filter_type to correct field name
    field_mapping = {
        'department': 'role',
        'religion': 'religion', 
        'country': 'country',
        'state': 'state',
        'city': 'city',
        'display_order':'display_order'
    }
    
    if filter_type and filter_type != 'all':
        # Get specific filter category options with subcategories
        try:
            category = FilterCategory.objects.get(slug=filter_type, is_active=True)
            queryset = FilterOption.objects.filter(category=category, is_active=True).order_by('display_order', 'name')
            
            if search:
                queryset = queryset.filter(name__icontains=search)
            
            # Get all options with their subcategories
            all_options = list(queryset)
            
            # Paginate
            total = len(all_options)
            start = (page - 1) * page_size
            end = start + page_size
            paginated_options = all_options[start:end]
            total_pages = (total + page_size - 1) // page_size
            
            base_url = f"/api/candidates/filter-options/?type={filter_type}&page_size={page_size}"
            if search:
                base_url += f"&search={search}"
                
            next_url = f"{base_url}&page={page + 1}" if page < total_pages else None
            previous_url = f"{base_url}&page={page - 1}" if page > 1 else None
            
            field_name = field_mapping.get(filter_type)
            
            results = []
            for option in paginated_options:
                if field_name:
                    total_count = Candidate.objects.filter(
                        is_active=True,
                        **{f"{field_name}": option}
                    ).count()
                    
                    unlocked_count = Candidate.objects.filter(
                        is_active=True,
                        id__in=unlocked_ids,
                        **{f"{field_name}": option}
                    ).count()
                    
                    locked_count = total_count - unlocked_count
                else:
                    total_count = unlocked_count = locked_count = 0
                
                # Get subcategories (children) if any
                subcategories = []
                for child in FilterOption.objects.filter(parent=option, is_active=True).order_by('display_order', 'name'):
                    if field_name:
                        child_total = Candidate.objects.filter(
                            is_active=True,
                            **{f"{field_name}": child}
                        ).count()
                        
                        child_unlocked = Candidate.objects.filter(
                            is_active=True,
                            id__in=unlocked_ids,
                            **{f"{field_name}": child}
                        ).count()
                        
                        child_locked = child_total - child_unlocked
                    else:
                        child_total = child_unlocked = child_locked = 0
                    
                    subcategories.append({
                        'value': child.name,
                        'label': child.name,
                        'count': child_total,
                        'unlocked_count': child_unlocked,
                        'locked_count': child_locked
                    })
                
                results.append({
                    'value': option.name,
                    'label': option.name,
                    'count': total_count,
                    'unlocked_count': unlocked_count,
                    'locked_count': locked_count,
                    'subcategories': subcategories
                })
            
            return Response({
                'count': total,
                'next': next_url,
                'previous': previous_url,
                'results': results
            })
        except FilterCategory.DoesNotExist:
            return Response({'error': 'Invalid filter type'}, status=400)
    
    # Return all categories with their subcategories and counts
    all_categories = FilterCategory.objects.filter(is_active=True).order_by('display_order', 'name')
    
    results = {}
    
    # Add "all" option showing total counts across all categories
    total_candidates = Candidate.objects.filter(is_active=True).count()
    total_unlocked = Candidate.objects.filter(is_active=True, id__in=unlocked_ids).count()
    total_locked = total_candidates - total_unlocked
    
    results['all'] = {
        'total_count': sum(FilterOption.objects.filter(category=cat, is_active=True).count() for cat in all_categories),
        'name': 'All Categories',
        'icon': None,
        'candidate_count': total_candidates,
        'unlocked_count': total_unlocked,
        'locked_count': total_locked,
        'subcategories': {}
    }
    
    # Add each category with subcategories
    for category in all_categories:
        options_count = FilterOption.objects.filter(category=category, is_active=True).count()
        icon_url = None
        if category.icon:
            icon_url = request.build_absolute_uri(category.icon.url)
        
        field_name = field_mapping.get(category.slug)
        
        # Get total candidates for this category
        if field_name:
            category_candidates = Candidate.objects.filter(
                is_active=True,
                **{f"{field_name}__isnull": False}
            ).count()
            
            category_unlocked = Candidate.objects.filter(
                is_active=True,
                id__in=unlocked_ids,
                **{f"{field_name}__isnull": False}
            ).count()
        else:
            category_candidates = 0
            category_unlocked = 0
        
        category_locked = category_candidates - category_unlocked
        
        # Get subcategories with counts
        subcategories = {}
        for option in FilterOption.objects.filter(category=category, is_active=True).order_by('display_order', 'name'):
            if field_name:
                option_total = Candidate.objects.filter(
                    is_active=True,
                    **{f"{field_name}": option}
                ).count()
                
                option_unlocked = Candidate.objects.filter(
                    is_active=True,
                    id__in=unlocked_ids,
                    **{f"{field_name}": option}
                ).count()
                
                option_locked = option_total - option_unlocked
            else:
                option_total = option_unlocked = option_locked = 0
            
            subcategories[option.slug] = {
                'name': option.name,
                'candidate_count': option_total,
                'unlocked_count': option_unlocked,
                'locked_count': option_locked
            }
        
        results[category.slug] = {
            'total_count': options_count,
            'name': category.name,
            'icon': icon_url,
            'candidate_count': category_candidates,
            'unlocked_count': category_unlocked,
            'locked_count': category_locked,
            'subcategories': subcategories
        }
        
        # Add subcategories to "all" option
        results['all']['subcategories'][category.slug] = {
            'name': category.name,
            'icon': icon_url,
            'candidate_count': category_candidates,
            'unlocked_count': category_unlocked,
            'locked_count': category_locked,
            'options': subcategories
        }
    
    return Response({'results': results})

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_filter_categories(request):
    """Get all filter categories"""
    
    if request.user.role != 'hr':
        return Response({
            'error': 'Only HR users can access this'
        }, status=status.HTTP_403_FORBIDDEN)
    
    from .models import FilterCategory
    
    categories = FilterCategory.objects.filter(is_active=True).order_by('display_order', 'name')
    serializer = FilterCategorySerializer(categories, many=True, context={'request': request})
    
    return Response({
        'success': True,
        'filter_categories': serializer.data
    })

# ========== Notes & Followups APIs ==========

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def add_candidate_note(request, candidate_id):
    """Add note for a candidate - For HR users"""
    
    if request.user.role != 'hr':
        return Response({
            'error': 'Only HR users can add notes'
        }, status=status.HTTP_403_FORBIDDEN)
    
    try:
        candidate = Candidate.objects.get(id=candidate_id, is_active=True)
        
        # Check if HR has unlocked this candidate
        if not UnlockHistory.objects.filter(hr_user=request.user.hr_profile, candidate=candidate).exists():
            return Response({
                'error': 'Candidate must be unlocked to add notes'
            }, status=status.HTTP_403_FORBIDDEN)
        
        serializer = CandidateNoteSerializer(data=request.data)
        if serializer.is_valid():
            note = serializer.save(
                hr_user=request.user.hr_profile,
                candidate=candidate
            )
            return Response({
                'success': True,
                'message': 'Note added successfully',
                'note': CandidateNoteSerializer(note).data
            })
        else:
            return Response({
                'error': 'Validation failed',
                'details': serializer.errors
            }, status=status.HTTP_400_BAD_REQUEST)
            
    except Candidate.DoesNotExist:
        return Response({
            'error': 'Candidate not found'
        }, status=status.HTTP_404_NOT_FOUND)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def add_candidate_followup(request, candidate_id):
    """Add followup for a candidate - For HR users"""
    
    if request.user.role != 'hr':
        return Response({
            'error': 'Only HR users can add followups'
        }, status=status.HTTP_403_FORBIDDEN)
    
    try:
        candidate = Candidate.objects.get(id=candidate_id, is_active=True)
        
        # Check if HR has unlocked this candidate
        if not UnlockHistory.objects.filter(hr_user=request.user.hr_profile, candidate=candidate).exists():
            return Response({
                'error': 'Candidate must be unlocked to add followups'
            }, status=status.HTTP_403_FORBIDDEN)
        
        serializer = CandidateFollowupSerializer(data=request.data)
        if serializer.is_valid():
            followup = serializer.save(
                hr_user=request.user.hr_profile,
                candidate=candidate
            )
            return Response({
                'success': True,
                'message': 'Followup added successfully',
                'followup': CandidateFollowupSerializer(followup).data
            })
        else:
            return Response({
                'error': 'Validation failed',
                'details': serializer.errors
            }, status=status.HTTP_400_BAD_REQUEST)
            
    except Candidate.DoesNotExist:
        return Response({
            'error': 'Candidate not found'
        }, status=status.HTTP_404_NOT_FOUND)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_candidate_notes_followups(request, candidate_id):
    """Get notes and followups for a candidate - For HR users"""
    
    if request.user.role != 'hr':
        return Response({
            'error': 'Only HR users can access this'
        }, status=status.HTTP_403_FORBIDDEN)
    
    try:
        candidate = Candidate.objects.get(id=candidate_id, is_active=True)
        
        # Check if HR has unlocked this candidate
        if not UnlockHistory.objects.filter(hr_user=request.user.hr_profile, candidate=candidate).exists():
            return Response({
                'error': 'Candidate must be unlocked to view notes and followups'
            }, status=status.HTTP_403_FORBIDDEN)
        
        # Get notes and followups for this HR user and candidate
        notes = CandidateNote.objects.filter(
            hr_user=request.user.hr_profile,
            candidate=candidate
        )
        followups = CandidateFollowup.objects.filter(
            hr_user=request.user.hr_profile,
            candidate=candidate
        )
        
        return Response({
            'success': True,
            'notes': CandidateNoteSerializer(notes, many=True).data,
            'followups': CandidateFollowupSerializer(followups, many=True).data
        })
        
    except Candidate.DoesNotExist:
        return Response({
            'error': 'Candidate not found'
        }, status=status.HTTP_404_NOT_FOUND)
from rest_framework import status, generics
from rest_framework.decorators import api_view, permission_classes,parser_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import SearchFilter
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser
from datetime import datetime
from django.utils import timezone

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
from apps.notifications.services import WorkfinaFCMService
from apps.notifications.models import ProfileStepReminder
from apps.wallet.models import Wallet


User = get_user_model()

class CandidateRegistrationView(generics.CreateAPIView):
    """API for candidates to register their profile"""
    
    serializer_class = CandidateRegistrationSerializer
    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser, JSONParser]

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
        
        # ✅ GET WORK EXPERIENCE & EDUCATION DATA
        work_experience_data = request.data.get('work_experience')
        education_data = request.data.get('education')
        
        # Call parent create method first
        response = super().post(request, *args, **kwargs)
        
        if response.status_code == 201:
            try:
                candidate = Candidate.objects.get(user=request.user)
                
                if work_experience_data:
                    try:
                        import json
                        work_exp_list = json.loads(work_experience_data)
                        
                        print("=" * 50)
                        print("SAVING WORK EXPERIENCES:")
                        print(json.dumps(work_exp_list, indent=2))
                        print("=" * 50)
                        
                        for exp_data in work_exp_list:
                            WorkExperience.objects.create(
                                candidate=candidate,
                                company_name=exp_data.get('company_name', ''),
                                role_title=exp_data.get('role_title', ''),
                                start_date=f"{exp_data.get('start_year')}-{_month_to_number(exp_data.get('start_month'))}-01",
                                end_date=f"{exp_data.get('end_year')}-{_month_to_number(exp_data.get('end_month'))}-01" if not exp_data.get('is_current') and exp_data.get('end_year') else None,
                                is_current=exp_data.get('is_current', False),
                                current_ctc=float(exp_data.get('ctc')) if exp_data.get('ctc') and exp_data.get('ctc').strip() else None,  
                                location=exp_data.get('location', ''),
                                description=exp_data.get('description', ''),
                            )
                            print(f"✅ Saved work experience: {exp_data.get('company_name')}")
                    except Exception as e:
                        print(f"❌ Work experience error: {e}")
                        import traceback
                        traceback.print_exc()
                
                # ✅ SAVE EDUCATION
                if education_data:
                    try:
                        import json
                        edu_list = json.loads(education_data)
                        
                        print("=" * 50)
                        print("SAVING EDUCATION:")
                        print(json.dumps(edu_list, indent=2))
                        print("=" * 50)
                        
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
                            print(f"✅ Saved education: {edu_data.get('school')}")
                    except Exception as e:
                        print(f"❌ Education error: {e}")
                        import traceback
                        traceback.print_exc()
                
                # Return full profile data with work_experiences and educations
                candidate.refresh_from_db()

                candidate = Candidate.objects.prefetch_related('educations', 'work_experiences').get(id=candidate.id)

                serializer = FullCandidateSerializer(candidate, context={'request': request})
                return Response(serializer.data, status=status.HTTP_201_CREATED)
                
            except Exception as e:
                print(f"❌ Error saving work/education: {e}")
                import traceback
                traceback.print_exc()
        
        return response

class CandidateListView(generics.ListAPIView):
    """API to list masked candidates with filters - For HR users"""

    queryset = Candidate.objects.filter(is_active=True, is_available_for_hiring=True)
    serializer_class = MaskedCandidateSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, SearchFilter]
    filterset_fields = ['role', 'city', 'state', 'religion', 'is_available_for_hiring']
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
        

        try:
            wallet = Wallet.objects.get(hr_profile__user=request.user)
            credits_required = 10

            # Check if user can unlock (checks subscription + wallet)
            if not wallet.can_unlock(credits_required):
                return Response({
                    'error': f'Insufficient credits. You need {credits_required} credits but have {wallet.balance}.',
                    'required_credits': credits_required,
                    'current_balance': wallet.balance
                }, status=status.HTTP_400_BAD_REQUEST)

            # Deduct credits (handles subscription + wallet automatically)
            old_balance = wallet.balance
            if not wallet.deduct_credits(credits_required):
                return Response({
                    'error': 'Failed to deduct credits. Please try again.',
                    'required_credits': credits_required,
                    'current_balance': wallet.balance
                }, status=status.HTTP_400_BAD_REQUEST)
            
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
            # Send credit deduction notification
            try:
                WorkfinaFCMService.send_to_user(
                    user=request.user,
                    title=f"Profile Unlocked! 🔓",
                    body=f"You unlocked {candidate.masked_name}'s profile for {credits_required} credits. Balance: {wallet.balance}",
                    notification_type='CREDIT_UPDATE',
                    data={
                        'candidate_id': str(candidate.id),
                        'candidate_name': candidate.masked_name,
                        'credits_used': credits_required,
                        'old_balance': old_balance,
                        'new_balance': wallet.balance,
                        'action': 'unlock_profile'
                    }
                )
                print(f'[DEBUG] Sent unlock notification to {request.user.email}')
            except Exception as e:
                print(f'[DEBUG] Failed to send unlock notification: {str(e)}')
            
                       
            
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
                
                # ✅ DIRECTLY PARSE JSON - NO REGEX CLEANING
                work_exp_list = json.loads(work_experience_data)
                
                print("=" * 80)
                print("WORK EXPERIENCES RECEIVED:")
                print(json.dumps(work_exp_list, indent=2))
                print("=" * 80)
                
                for i, exp_data in enumerate(work_exp_list, 1):
                    print(f"\n--- Creating Experience #{i} ---")
                    print(f"Company: {exp_data.get('company_name')}")
                    print(f"Role: {exp_data.get('job_role')}")
                    print(f"Location: '{exp_data.get('location')}'")
                    print(f"Description: '{exp_data.get('description')}'")
                    
                    work_exp = WorkExperience.objects.create(
                        candidate=candidate,
                        company_name=exp_data.get('company_name', ''),
                        role_title=exp_data.get('role_title', ''),
                        start_date=f"{exp_data.get('start_year')}-{_month_to_number(exp_data.get('start_month'))}-01",
                        end_date=f"{exp_data.get('end_year')}-{_month_to_number(exp_data.get('end_month'))}-01" if not exp_data.get('is_current') and exp_data.get('end_year') else None,
                        is_current=exp_data.get('is_current', False),
                        current_ctc=float(exp_data.get('ctc')) if exp_data.get('ctc') and exp_data.get('ctc').strip() else None,                        location=exp_data.get('location', ''),
                        description=exp_data.get('description', ''),
                    )
                    
                    print(f"✅ Saved - Location: '{work_exp.location}', Description: '{work_exp.description}'")
                    
            except json.JSONDecodeError as e:
                print(f"❌ JSON parsing error: {e}")
                print(f"Raw data: {work_experience_data}")
            except Exception as e:
                print(f"❌ Work experience error: {e}")
                import traceback
                traceback.print_exc()

        # Handle education if provided  
        education_data = request.data.get('educations')
        if education_data:
            candidate.educations.all().delete()
            
            try:
                import json
                
                # ✅ DIRECTLY PARSE JSON - NO REGEX CLEANING
                edu_list = json.loads(education_data)
                
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
                        location=edu_data.get('location', '')
                    )
            except Exception as e:
                print(f"Education parsing error: {e}")
        
        # Remove work_experiences and educations from request.data for candidate update
        candidate_data = request.data.copy()
        candidate_data.pop('work_experiences', None)
        candidate_data.pop('educations', None)
        
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
    """Get all filter categories with subcategories and candidate counts"""

    if request.user.role != 'hr':
        return Response({
            'error': 'Only HR users can access this'
        }, status=status.HTTP_403_FORBIDDEN)

    from .models import FilterCategory, FilterOption
    from django.core.paginator import Paginator

    page = int(request.query_params.get('page', 1))
    page_size = int(request.query_params.get('page_size', 20))
    subcategory_page = int(request.query_params.get('subcategory_page', 1))
    subcategory_limit = int(request.query_params.get('subcategory_limit', 20))

    categories = FilterCategory.objects.filter(is_active=True).order_by('display_order', 'name')
    paginator = Paginator(categories, page_size)
    categories_page = paginator.get_page(page)
    
    field_mapping = {
        'department': 'role',
        'religion': 'religion', 
        'country': 'country',
        'state': 'state',
        'city': 'city'
    }
    
    unlocked_ids = set(UnlockHistory.objects.filter(
        hr_user=request.user.hr_profile
    ).values_list('candidate_id', flat=True))

    results = []

    for category in categories_page:
        icon_url = None
        if category.icon:
            icon_url = request.build_absolute_uri(category.icon.url)
        
        field_name = field_mapping.get(category.slug)
        
        if category.slug in ['state', 'city']:
            options = FilterOption.objects.filter(
                category=category,
                is_active=True
            ).order_by('display_order', 'name')
        else:
            options = FilterOption.objects.filter(
                category=category,
                is_active=True,
                parent__isnull=True
            ).order_by('display_order', 'name')

        # Paginate subcategories
        subcategory_paginator = Paginator(options, subcategory_limit)
        subcategory_page_obj = subcategory_paginator.get_page(subcategory_page)

        subcategories = []

        for option in subcategory_page_obj:
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
            
            children = FilterOption.objects.filter(
                parent=option, 
                is_active=True
            ).order_by('display_order', 'name')
            
            child_subcategories = []
            
            for child in children:
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
                
                # Get icon URL for child subcategory
                child_icon_url = None
                if child.icon:
                    child_icon_url = request.build_absolute_uri(child.icon.url)

                child_subcategories.append({
                    'id': str(child.id),
                    'name': child.name,
                    'slug': child.slug,
                    'icon': child_icon_url,
                    'total_candidates': child_total,
                    'locked_candidates': child_locked,
                    'unlocked_candidates': child_unlocked
                })
            
            # Get icon URL for subcategory
            option_icon_url = None
            if option.icon:
                option_icon_url = request.build_absolute_uri(option.icon.url)

            subcategories.append({
                'id': str(option.id),
                'name': option.name,
                'slug': option.slug,
                'icon': option_icon_url,
                'total_candidates': total_count,
                'locked_candidates': locked_count,
                'unlocked_candidates': unlocked_count,
                'children': child_subcategories
            })
        
        # Build subcategory pagination URLs
        subcategory_next = None
        subcategory_previous = None

        if subcategory_page_obj.has_next():
            subcategory_next = f"/api/candidates/filter-categories/?page={page}&page_size={page_size}&subcategory_page={subcategory_page_obj.next_page_number()}&subcategory_limit={subcategory_limit}"

        if subcategory_page_obj.has_previous():
            subcategory_previous = f"/api/candidates/filter-categories/?page={page}&page_size={page_size}&subcategory_page={subcategory_page_obj.previous_page_number()}&subcategory_limit={subcategory_limit}"

        results.append({
            'id': str(category.id),
            'name': category.name,
            'slug': category.slug,
            'icon': icon_url,
            'display_order': category.display_order,
            'is_active': category.is_active,
            'bento_grid': category.bento_grid,
            'dashboard_display': category.dashboard_display,
            'inner_filter': category.inner_filter,
            'subcategories': subcategories,
            'subcategory_count': subcategory_paginator.count,
            'subcategory_next': subcategory_next,
            'subcategory_previous': subcategory_previous
        })

    next_url = None
    previous_url = None

    if categories_page.has_next():
        next_url = f"/api/candidates/filter-categories/?page={categories_page.next_page_number()}&page_size={page_size}"

    if categories_page.has_previous():
        previous_url = f"/api/candidates/filter-categories/?page={categories_page.previous_page_number()}&page_size={page_size}"

    return Response({
        'success': True,
        'count': paginator.count,
        'next': next_url,
        'previous': previous_url,
        'filter_categories': results
    })

# ========== Notes & Followups APIs ==========

@api_view(['POST', 'DELETE'])
@permission_classes([IsAuthenticated])
def add_candidate_note(request, candidate_id, note_id=None):
    """Add or delete note for a candidate - For HR users"""

    if request.user.role != 'hr':
        return Response({
            'error': 'Only HR users can manage notes'
        }, status=status.HTTP_403_FORBIDDEN)

    try:
        candidate = Candidate.objects.get(id=candidate_id, is_active=True)

        # Check if HR has unlocked this candidate
        if not UnlockHistory.objects.filter(hr_user=request.user.hr_profile, candidate=candidate).exists():
            return Response({
                'error': 'Candidate must be unlocked to manage notes'
            }, status=status.HTTP_403_FORBIDDEN)

        # DELETE: Remove note
        if request.method == 'DELETE':
            if not note_id:
                return Response({
                    'error': 'Note ID is required for deletion'
                }, status=status.HTTP_400_BAD_REQUEST)

            try:
                note = CandidateNote.objects.get(
                    id=note_id,
                    hr_user=request.user.hr_profile,
                    candidate=candidate
                )
                note.delete()
                return Response({
                    'success': True,
                    'message': 'Note deleted successfully'
                })
            except CandidateNote.DoesNotExist:
                return Response({
                    'error': 'Note not found'
                }, status=status.HTTP_404_NOT_FOUND)

        # POST: Add note
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

@api_view(['POST', 'DELETE'])
@permission_classes([IsAuthenticated])
def add_candidate_followup(request, candidate_id, followup_id=None):
    """Add or delete followup for a candidate - For HR users"""

    if request.user.role != 'hr':
        return Response({
            'error': 'Only HR users can manage followups'
        }, status=status.HTTP_403_FORBIDDEN)

    try:
        candidate = Candidate.objects.get(id=candidate_id, is_active=True)

        # Check if HR has unlocked this candidate
        if not UnlockHistory.objects.filter(hr_user=request.user.hr_profile, candidate=candidate).exists():
            return Response({
                'error': 'Candidate must be unlocked to manage followups'
            }, status=status.HTTP_403_FORBIDDEN)

        # DELETE: Remove followup
        if request.method == 'DELETE':
            if not followup_id:
                return Response({
                    'error': 'Followup ID is required for deletion'
                }, status=status.HTTP_400_BAD_REQUEST)

            try:
                followup = CandidateFollowup.objects.get(
                    id=followup_id,
                    hr_user=request.user.hr_profile,
                    candidate=candidate
                )
                followup.delete()
                return Response({
                    'success': True,
                    'message': 'Followup deleted successfully'
                })
            except CandidateFollowup.DoesNotExist:
                return Response({
                    'error': 'Followup not found'
                }, status=status.HTTP_404_NOT_FOUND)

        # POST: Add followup
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
    

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_states(request):
    try:
        state_category = FilterCategory.objects.get(slug='state')
        country_category = FilterCategory.objects.get(slug='country')
        india = FilterOption.objects.get(category=country_category, slug='india')
        
        states = FilterOption.objects.filter(
            category=state_category,
            parent=india,
            is_active=True
        ).order_by('name')
        
        states_data = [
            {
                'id': str(state.id),
                'name': state.name,
                'slug': state.slug
            }
            for state in states
        ]
        
        return Response({'success': True, 'states': states_data})
        
    except FilterCategory.DoesNotExist:
        return Response({'error': 'Location data not initialized'}, status=404)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_cities(request):
    state_slug = request.query_params.get('state')
    
    if not state_slug:
        return Response({'error': 'State parameter is required'}, status=400)
    
    try:
        city_category = FilterCategory.objects.get(slug='city')
        state_category = FilterCategory.objects.get(slug='state')
        
        state = FilterOption.objects.get(
            category=state_category,
            slug=state_slug,
            is_active=True
        )
        
        cities = FilterOption.objects.filter(
            category=city_category,
            parent=state,
            is_active=True
        ).order_by('name')
        
        cities_data = [
            {
                'id': str(city.id),
                'name': city.name,
                'slug': city.slug
            }
            for city in cities
        ]
        
        return Response({'success': True, 'state': state.name, 'cities': cities_data})
        
    except FilterOption.DoesNotExist:
        return Response({'error': 'State not found'}, status=404)
    except FilterCategory.DoesNotExist:
        return Response({'error': 'Location data not initialized'}, status=404)
    
@api_view(['POST', 'PATCH'])
@permission_classes([IsAuthenticated])
@parser_classes([MultiPartParser, FormParser, JSONParser])
def save_candidate_step(request):
    """Save candidate profile step-by-step (auto-save)"""
    
    if request.user.role != 'candidate':
        return Response({'error': 'Only candidates can save profile steps'}, status=403)
    
    step = request.data.get('step')
    if not step or int(step) not in [1, 2, 3, 4]:
        return Response({'error': 'Invalid step. Must be 1, 2, 3, or 4'}, status=400)
    
    step = int(step)
    
    try:
        candidate, created = Candidate.objects.get_or_create(
            user=request.user,
            defaults={
                'first_name': '',
                'last_name': '',
                'phone': '',
                'age': 0,
                'experience_years': 0,
                'skills': '',
                'profile_step': step
            }
        )
        # Get or create profile reminder tracker
        reminder, reminder_created = ProfileStepReminder.objects.get_or_create(
            user=request.user,
            defaults={'current_step': step}
        )
        
        # Update step progress
        old_step = reminder.current_step
        if step > old_step:
            reminder.update_step(step)
            print(f'[DEBUG] Updated profile step from {old_step} to {step} for {request.user.email}')
                
        
        update_data = {'profile_step': step}
        
        # Step 1: Personal Information
        if step == 1:
            if request.data.get('first_name'):
                update_data['first_name'] = request.data.get('first_name')
            if request.data.get('last_name'):
                update_data['last_name'] = request.data.get('last_name')
            if request.data.get('phone'):
                update_data['phone'] = request.data.get('phone')
            if request.data.get('age'):
                update_data['age'] = int(request.data.get('age'))
            if request.data.get('current_ctc'):
                update_data['current_ctc'] = float(request.data.get('current_ctc'))
            if request.data.get('expected_ctc'):
                update_data['expected_ctc'] = float(request.data.get('expected_ctc'))
            if request.data.get('languages'):
                update_data['languages'] = request.data.get('languages')
            if request.data.get('street_address'):
                update_data['street_address'] = request.data.get('street_address')
            if request.data.get('willing_to_relocate') is not None:
                update_data['willing_to_relocate'] = request.data.get('willing_to_relocate') == 'true' or request.data.get('willing_to_relocate') == True
            if request.data.get('career_objective'):
                update_data['career_objective'] = request.data.get('career_objective')
            if request.data.get('joining_availability'):
                update_data['joining_availability'] = request.data.get('joining_availability')
            if request.data.get('notice_period_details'):
                update_data['notice_period_details'] = request.data.get('notice_period_details')

            # Mark step 1 as completed
            if not candidate.step1_completed:
                update_data['step1_completed'] = True
                update_data['step1_completed_at'] = timezone.now()

            # Handle role
            role_value = request.data.get('role')
            if role_value:
                dept_category, _ = FilterCategory.objects.get_or_create(
                    slug='department',
                    defaults={'name': 'Department', 'display_order': 1}
                )
                role_slug = role_value.lower().replace(' ', '-')
                role, _ = FilterOption.objects.get_or_create(
                    category=dept_category,
                    slug=role_slug,
                    defaults={'name': role_value, 'is_active': True}
                )
                update_data['role'] = role
            
            # Handle religion
            religion_value = request.data.get('religion')
            if religion_value:
                religion_category, _ = FilterCategory.objects.get_or_create(
                    slug='religion',
                    defaults={'name': 'Religion', 'display_order': 2}
                )
                religion_slug = religion_value.lower().replace(' ', '-')
                religion, _ = FilterOption.objects.get_or_create(
                    category=religion_category,
                    slug=religion_slug,
                    defaults={'name': religion_value, 'is_active': True}
                )
                update_data['religion'] = religion
            
            # Handle location
            state_value = request.data.get('state')
            city_value = request.data.get('city')
            
            if state_value or city_value:
                country_category, _ = FilterCategory.objects.get_or_create(
                    slug='country',
                    defaults={'name': 'Country', 'display_order': 3}
                )
                state_category, _ = FilterCategory.objects.get_or_create(
                    slug='state',
                    defaults={'name': 'State', 'display_order': 4}
                )
                city_category, _ = FilterCategory.objects.get_or_create(
                    slug='city',
                    defaults={'name': 'City', 'display_order': 5}
                )
                
                country, _ = FilterOption.objects.get_or_create(
                    category=country_category,
                    slug='india',
                    defaults={'name': 'India', 'is_active': True}
                )
                update_data['country'] = country
                
                if state_value:
                    state_slug = state_value.lower().replace(' ', '-')
                    state, _ = FilterOption.objects.get_or_create(
                        category=state_category,
                        slug=state_slug,
                        defaults={'name': state_value.title(), 'parent': country, 'is_active': True}
                    )
                    update_data['state'] = state
                    
                    if city_value:
                        city_slug = f"{state_slug}-{city_value.lower().replace(' ', '-')}"
                        city, _ = FilterOption.objects.get_or_create(
                            category=city_category,
                            slug=city_slug,
                            defaults={'name': city_value.title(), 'parent': state, 'is_active': True}
                        )
                        update_data['city'] = city
            
            if 'profile_image' in request.FILES:
                update_data['profile_image'] = request.FILES['profile_image']
        
        # Step 2: Work Experience
        elif step == 2:
            # Handle joining availability (can be saved without work experience)
            if request.data.get('joining_availability'):
                update_data['joining_availability'] = request.data.get('joining_availability')
            if request.data.get('notice_period_details'):
                update_data['notice_period_details'] = request.data.get('notice_period_details')

            work_experience_data = request.data.get('work_experience')
            if work_experience_data:
                candidate.work_experiences.all().delete()

                import json
                work_exp_list = json.loads(work_experience_data)

                for exp_data in work_exp_list:
                    WorkExperience.objects.create(
                        candidate=candidate,
                        company_name=exp_data.get('company_name', ''),
                        role_title=exp_data.get('role_title', ''),
                        start_date=f"{exp_data.get('start_year')}-{_month_to_number(exp_data.get('start_month'))}-01",
                        end_date=f"{exp_data.get('end_year')}-{_month_to_number(exp_data.get('end_month'))}-01" if not exp_data.get('is_current') and exp_data.get('end_year') else None,
                        is_current=exp_data.get('is_current', False),
                        current_ctc=float(exp_data.get('ctc', 0)) if exp_data.get('ctc') else None,
                        location=exp_data.get('location', ''),
                        description=exp_data.get('description', ''),
                    )

            # Calculate experience
            total_exp = 0
            from datetime import datetime
            for exp in candidate.work_experiences.all():
                start_year = exp.start_date.year
                end_year = exp.end_date.year if exp.end_date else datetime.now().year
                total_exp += (end_year - start_year)

            if total_exp > 0:
                update_data['experience_years'] = total_exp

            # Mark step 2 as completed ONLY if work experience was added
            if not candidate.step2_completed and candidate.work_experiences.exists():
                update_data['step2_completed'] = True
                update_data['step2_completed_at'] = timezone.now()
        
        # Step 3: Education + Skills
        elif step == 3:
            if request.data.get('skills'):
                update_data['skills'] = request.data.get('skills')

            education_data = request.data.get('education')
            if education_data:
                candidate.educations.all().delete()

                import json
                edu_list = json.loads(education_data)

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
                        location=edu_data.get('location', '')
                    )

            # Mark step 3 as completed
            if not candidate.step3_completed:
                update_data['step3_completed'] = True
                update_data['step3_completed_at'] = timezone.now()

        # Step 4: Documents
        elif step == 4:
            update_data['is_profile_completed'] = True
            reminder.is_profile_completed = True
            reminder.save()

        has_agreed = request.data.get('has_agreed_to_declaration')
        if has_agreed == 'true' or has_agreed is True:
            update_data['has_agreed_to_declaration'] = True
            update_data['declaration_agreed_at'] = timezone.now()
            # Mark step 4 as completed
            if not candidate.step4_completed:
                update_data['step4_completed'] = True
                update_data['step4_completed_at'] = timezone.now()

            # Send profile completion notification
            try:
                WorkfinaFCMService.send_to_user(
                    user=request.user,
                    title="🎉 Profile Completed!",
                    body="Great! Your profile is now complete. You're ready to connect with top recruiters!",
                    notification_type='COMPLETE_PROFILE',
                    data={
                        'profile_completed': True,
                        'step': step,
                        'action': 'profile_complete'
                    }
                )
                print(f'[DEBUG] Sent profile completion notification to {request.user.email}')
            except Exception as e:
                print(f'[DEBUG] Failed to send profile completion notification: {str(e)}')

            if 'resume' in request.FILES:
                update_data['resume'] = request.FILES['resume']
            if 'video_intro' in request.FILES:
                update_data['video_intro'] = request.FILES['video_intro']
            update_data['is_profile_completed'] = True
        
        # Update candidate
        for field, value in update_data.items():
            setattr(candidate, field, value)
        candidate.save()
        
        serializer = FullCandidateSerializer(candidate, context={'request': request})
        
        return Response({
            'success': True,
            'message': f'Step {step} saved successfully',
            'current_step': candidate.profile_step,
            'is_completed': candidate.is_profile_completed,
            'profile': serializer.data
        })
        
    except Exception as e:
        return Response({'error': f'Failed to save step: {str(e)}'}, status=500)
    

@api_view(['GET'])
def get_public_filter_options(request):
    """Get department and religion options - publicly accessible"""
    
    from .models import FilterCategory, FilterOption
    
    try:
        dept_category = FilterCategory.objects.get(slug='department', is_active=True)
        religion_category = FilterCategory.objects.get(slug='religion', is_active=True)
        skills_category = FilterCategory.objects.get(slug='skills', is_active=True)
        languages_category = FilterCategory.objects.get(slug='languages', is_active=True)
        
        
        departments = FilterOption.objects.filter(
            category=dept_category, 
            is_active=True
        ).order_by('display_order', 'name')
        
        religions = FilterOption.objects.filter(
            category=religion_category,
            is_active=True
        ).order_by('display_order', 'name')

        skills = FilterOption.objects.filter(
            category=skills_category,
            is_active=True
        ).order_by('display_order', 'name')
        
        languages = FilterOption.objects.filter(
            category=languages_category,
            is_active=True
        ).order_by('display_order', 'name')

        
        return Response({
            'success': True,
            'departments': [{'value': dept.slug, 'label': dept.name} for dept in departments],
            'religions': [{'value': relig.slug, 'label': relig.name} for relig in religions],
            'skills': [{'value': skill.slug, 'label': skill.name} for skill in skills],
            'languages': [{'value': lang.slug, 'label': lang.name} for lang in languages]
        })
        
    except FilterCategory.DoesNotExist:
        return Response({
            'success': True,
            'departments': [],
            'religions': []
        })
        
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_candidate_availability(request):
    """Get candidate's current availability status for hiring with dynamic UI configuration"""

    if request.user.role != 'candidate':
        return Response({
            'error': 'Only candidates can access this'
        }, status=status.HTTP_403_FORBIDDEN)

    try:
        candidate = Candidate.objects.get(user=request.user)

        # Check if we should show the prompt (show if date has changed)
        should_show_prompt = True
        if candidate.last_availability_update:
            import pytz
            ist = pytz.timezone('Asia/Kolkata')

            # Get current date in IST
            current_date = timezone.now().astimezone(ist).date()

            # Get last update date in IST
            last_update_date = candidate.last_availability_update.astimezone(ist).date()

            # Show prompt only if current date is different from last update date
            should_show_prompt = current_date != last_update_date

        # Get dynamic UI configuration from HiringAvailabilityUI model
        from apps.candidates.models import HiringAvailabilityUI
        ui_config = HiringAvailabilityUI.objects.filter(is_active=True).first()

        # Default UI configuration
        default_config = {
            'title': "Are you still available for hiring?",
            'message': "Please confirm if you're still open to new job opportunities.",
            'button_layout': 'column',
            'content_vertical_alignment': 'center',
            'background_type': 'color',
            'background_color': '#FFFFFF',
            'background_image': None,
            'gradient_start_color': '#FFFFFF',
            'gradient_end_color': '#F5F5F5',
            'icon': {
                'show': True,
                'source': 'material',
                'type': 'work_outline_rounded',
                'image_url': None,
                'size': 60.0,
                'color': '#4CAF50',
                'background_color': '#4CAF5019'
            },
            'title_style': {
                'font_size': 24.0,
                'font_weight': 'bold',
                'color': '#000000',
                'alignment': 'center'
            },
            'message_style': {
                'font_size': 16.0,
                'font_weight': 'normal',
                'color': '#757575',
                'alignment': 'center'
            },
            'primary_button': {
                'text': "Yes, I'm Available",
                'bg_color': '#4CAF50',
                'text_color': '#FFFFFF',
                'font_size': 18.0,
                'font_weight': 'w600',
                'height': 56.0,
                'border_radius': 12.0
            },
            'secondary_button': {
                'text': "No, Not Available",
                'bg_color': '#FFFFFF',
                'text_color': '#616161',
                'border_color': '#BDBDBD',
                'font_size': 18.0,
                'font_weight': 'w600',
                'height': 56.0,
                'border_radius': 12.0
            },
            'spacing': {
                'between_buttons': 16.0,
                'padding_horizontal': 24.0,
                'padding_vertical': 32.0
            },
            'extra_content': []
        }

        # If UI config exists, use it
        if ui_config:
            config_data = {
                'title': ui_config.title,
                'message': ui_config.message,
                'button_layout': ui_config.button_layout,
                'content_vertical_alignment': ui_config.content_vertical_alignment,
                'background_type': ui_config.background_type,
                'background_color': ui_config.background_color,
                'background_image': request.build_absolute_uri(ui_config.background_image.url) if ui_config.background_image else None,
                'gradient_start_color': ui_config.gradient_start_color,
                'gradient_end_color': ui_config.gradient_end_color,
                'icon': {
                    'show': ui_config.show_icon,
                    'source': ui_config.icon_source,
                    'type': ui_config.icon_type,
                    'image_url': request.build_absolute_uri(ui_config.icon_image.url) if ui_config.icon_image else None,
                    'size': ui_config.icon_size,
                    'color': ui_config.icon_color,
                    'background_color': ui_config.icon_background_color
                },
                'title_style': {
                    'font_size': ui_config.title_font_size,
                    'font_weight': ui_config.title_font_weight,
                    'color': ui_config.title_color,
                    'alignment': ui_config.title_alignment
                },
                'message_style': {
                    'font_size': ui_config.message_font_size,
                    'font_weight': ui_config.message_font_weight,
                    'color': ui_config.message_color,
                    'alignment': ui_config.message_alignment
                },
                'primary_button': {
                    'text': ui_config.primary_button_text,
                    'bg_color': ui_config.primary_button_bg_color,
                    'text_color': ui_config.primary_button_text_color,
                    'font_size': ui_config.primary_button_font_size,
                    'font_weight': ui_config.primary_button_font_weight,
                    'height': ui_config.primary_button_height,
                    'border_radius': ui_config.primary_button_border_radius
                },
                'secondary_button': {
                    'text': ui_config.secondary_button_text,
                    'bg_color': ui_config.secondary_button_bg_color,
                    'text_color': ui_config.secondary_button_text_color,
                    'border_color': ui_config.secondary_button_border_color,
                    'font_size': ui_config.secondary_button_font_size,
                    'font_weight': ui_config.secondary_button_font_weight,
                    'height': ui_config.secondary_button_height,
                    'border_radius': ui_config.secondary_button_border_radius
                },
                'spacing': {
                    'between_buttons': ui_config.spacing_between_buttons,
                    'padding_horizontal': ui_config.content_padding_horizontal,
                    'padding_vertical': ui_config.content_padding_vertical
                },
                'extra_content': ui_config.extra_content if ui_config.extra_content else []
            }
        else:
            config_data = default_config

        # Format last_availability_update to IST
        last_update_ist = None
        if candidate.last_availability_update:
            import pytz
            ist = pytz.timezone('Asia/Kolkata')
            last_update_ist = candidate.last_availability_update.astimezone(ist).strftime('%d %b %Y, %I:%M %p IST')

        return Response({
            'success': True,
            'is_available_for_hiring': candidate.is_available_for_hiring,
            'last_availability_update': last_update_ist,
            'should_show_prompt': should_show_prompt,
            'ui_config': config_data
        })
    except Candidate.DoesNotExist:
        return Response({
            'error': 'Profile not found'
        }, status=status.HTTP_404_NOT_FOUND)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def update_candidate_availability(request):
    """Update candidate's availability status for hiring"""

    if request.user.role != 'candidate':
        return Response({
            'error': 'Only candidates can update their availability'
        }, status=status.HTTP_403_FORBIDDEN)

    try:
        candidate = Candidate.objects.get(user=request.user)

        is_available = request.data.get('is_available_for_hiring')
        if is_available is None:
            return Response({
                'error': 'is_available_for_hiring field is required'
            }, status=status.HTTP_400_BAD_REQUEST)

        # Convert to boolean
        if isinstance(is_available, str):
            is_available = is_available.lower() in ['true', '1', 'yes']

        # Store old availability status to check if it changed
        old_availability = candidate.is_available_for_hiring

        candidate.is_available_for_hiring = is_available
        candidate.last_availability_update = timezone.now()
        candidate.save()

        # If candidate marked themselves as NOT available (hired/unavailable)
        # Notify all recruiters who unlocked this candidate
        if old_availability and not is_available:
            try:
                # Get all HR users who unlocked this candidate
                unlocked_hrs = UnlockHistory.objects.filter(
                    candidate=candidate
                ).select_related('hr_user__user')

                # Send notification to each HR
                for unlock_history in unlocked_hrs:
                    hr_user = unlock_history.hr_user.user
                    try:
                        WorkfinaFCMService.send_to_user(
                            user=hr_user,
                            title="Candidate No Longer Available",
                            body=f"{candidate.masked_name} is no longer available for hiring opportunities.",
                            notification_type='CANDIDATE_UNAVAILABLE',
                            data={
                                'candidate_id': str(candidate.id),
                                'candidate_name': candidate.masked_name,
                                'is_available': False,
                                'action': 'candidate_unavailable'
                            }
                        )
                        print(f'[DEBUG] Sent unavailability notification to HR: {hr_user.email}')
                    except Exception as e:
                        print(f'[DEBUG] Failed to send notification to HR {hr_user.email}: {str(e)}')
            except Exception as e:
                print(f'[DEBUG] Error notifying HRs about candidate unavailability: {str(e)}')

        return Response({
            'success': True,
            'message': 'Availability status updated successfully',
            'is_available_for_hiring': candidate.is_available_for_hiring,
            'last_availability_update': candidate.last_availability_update
        })
    except Candidate.DoesNotExist:
        return Response({
            'error': 'Profile not found'
        }, status=status.HTTP_404_NOT_FOUND)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def update_candidate_hiring_status(request, candidate_id):
    """Update candidate hiring status (for HR users)"""
    
    if request.user.role != 'hr':
        return Response({
            'error': 'Only HR users can update hiring status'
        }, status=403)
    
    try:
        candidate = Candidate.objects.get(id=candidate_id, is_active=True)
        
        # Check if HR has unlocked this candidate
        if not UnlockHistory.objects.filter(hr_user=request.user.hr_profile, candidate=candidate).exists():
            return Response({
                'error': 'Candidate must be unlocked to update hiring status'
            }, status=403)
        
        new_status = request.data.get('status')
        company_name = request.data.get('company_name', '')
        position_title = request.data.get('position_title', '')
        notes = request.data.get('notes', '')
        
        if new_status not in ['HIRED', 'ON_HOLD', 'REJECTED', 'WITHDRAWN']:
            return Response({
                'error': 'Invalid status'
            }, status=400)
        
        # Update or create candidate status
        from notifications.models import CandidateStatus
        candidate_status, created = CandidateStatus.objects.update_or_create(
            candidate=candidate,
            defaults={
                'status': new_status,
                'updated_by': request.user.hr_profile,
                'company_name': company_name,
                'position_title': position_title,
                'notes': notes
            }
        )
        
        # Send notification to candidate about status update
        if new_status == 'HIRED':
            try:
                WorkfinaFCMService.send_to_user(
                    user=candidate.user,
                    title="🎉 Congratulations! You've been hired!",
                    body=f"Great news! You've been selected for {position_title} at {company_name}. Check your profile for details.",
                    notification_type='CANDIDATE_HIRED',
                    data={
                        'status': new_status,
                        'company_name': company_name,
                        'position_title': position_title,
                        'hr_company': request.user.hr_profile.company_name
                    }
                )
                print(f'[DEBUG] Sent hiring notification to candidate {candidate.user.email}')
            except Exception as e:
                print(f'[DEBUG] Failed to send hiring notification to candidate: {str(e)}')
            
            # Notify other HRs who unlocked this candidate
            try:
                WorkfinaFCMService.notify_hrs_about_hired_candidate(candidate)
                print(f'[DEBUG] Notified other HRs about hired candidate {candidate.masked_name}')
            except Exception as e:
                print(f'[DEBUG] Failed to notify HRs about hired candidate: {str(e)}')
        
        return Response({
            'success': True,
            'message': f'Candidate status updated to {new_status}',
            'status': new_status,
            'candidate': candidate.masked_name
        })
        
    except Candidate.DoesNotExist:
        return Response({
            'error': 'Candidate not found'
        }, status=404)        
    



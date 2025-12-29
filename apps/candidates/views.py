from rest_framework import status, generics
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import SearchFilter
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
    
    def post(self, request, *args, **kwargs):
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
            hr_user=self.request.user
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
        if UnlockHistory.objects.filter(hr_user=request.user, candidate=candidate).exists():
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
                hr_user=request.user,
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
        hr_user=request.user
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
        serializer = FullCandidateSerializer(candidate)
        return Response(serializer.data)
    except Candidate.DoesNotExist:
        return Response({
            'error': 'Profile not found'
        }, status=status.HTTP_404_NOT_FOUND)
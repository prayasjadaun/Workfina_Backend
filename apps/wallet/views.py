from rest_framework import status, generics
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from .models import Wallet, WalletTransaction
from .serializers import WalletSerializer, WalletTransactionSerializer, RechargeWalletSerializer
from apps.recruiters.models import HRProfile

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def wallet_balance(request):
    try:
        hr_profile = request.user.hr_profile
        wallet, created = Wallet.objects.get_or_create(hr_profile=hr_profile)
        
        serializer = WalletSerializer(wallet)
        return Response({
            'success': True,
            'wallet': serializer.data
        })
    except HRProfile.DoesNotExist:
        return Response({
            'error': 'HR profile not found'
        }, status=status.HTTP_404_NOT_FOUND)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def recharge_wallet(request):
    try:
        hr_profile = request.user.hr_profile
        wallet, created = Wallet.objects.get_or_create(hr_profile=hr_profile)
        
        serializer = RechargeWalletSerializer(data=request.data)
        if serializer.is_valid():
            credits = serializer.validated_data['credits']
            payment_reference = serializer.validated_data.get('payment_reference', '')
            
            # Add credits to wallet
            wallet.balance += credits
            wallet.save()
            
            # Create transaction record
            WalletTransaction.objects.create(
                wallet=wallet,
                transaction_type='RECHARGE',
                credits_added=credits,
                reference_id=payment_reference,
                description=f'Wallet recharged with {credits} credits'
            )
            
            return Response({
                'success': True,
                'message': 'Wallet recharged successfully',
                'new_balance': wallet.balance
            })
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
    except HRProfile.DoesNotExist:
        return Response({
            'error': 'HR profile not found'
        }, status=status.HTTP_404_NOT_FOUND)

class TransactionHistoryView(generics.ListAPIView):
    serializer_class = WalletTransactionSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        try:
            hr_profile = self.request.user.hr_profile
            wallet = Wallet.objects.get(hr_profile=hr_profile)
            return WalletTransaction.objects.filter(wallet=wallet)
        except (HRProfile.DoesNotExist, Wallet.DoesNotExist):
            return WalletTransaction.objects.none()
    
    def list(self, request, *args, **kwargs):
        try:
            queryset = self.get_queryset()
            serializer = self.get_serializer(queryset, many=True)
            return Response({
                'success': True,
                'transactions': serializer.data
            })
        except Exception as e:
            return Response({
                'error': 'Failed to fetch transactions'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
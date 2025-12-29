from rest_framework import status, generics
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from .models import HRProfile
from .serializers import HRRegistrationSerializer, HRProfileSerializer

class HRRegistrationView(generics.CreateAPIView):
    serializer_class = HRRegistrationSerializer
    permission_classes = [IsAuthenticated]
    
    def post(self, request, *args, **kwargs):
        if request.user.role != 'hr':
            return Response({
                'error': 'Only HR users can create HR profiles'
            }, status=status.HTTP_403_FORBIDDEN)
        
        if hasattr(request.user, 'hr_profile'):
            return Response({
                'error': 'HR profile already exists'
            }, status=status.HTTP_400_BAD_REQUEST)
        
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
        
        
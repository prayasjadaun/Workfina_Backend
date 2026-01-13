from rest_framework import status, serializers
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.permissions import AllowAny, IsAuthenticated
from django.contrib.auth import authenticate
from rest_framework_simplejwt.tokens import RefreshToken
from drf_yasg.utils import swagger_auto_schema
from .serializers import LoginSerializer
from rest_framework_simplejwt.serializers import TokenRefreshSerializer

from .serializers import (
    SendOTPSerializer,
    VerifyOTPSerializer,
    CreateAccountSerializer,
    LoginSerializer,   
)
from .models import EmailOTP



# ================= SEND OTP =================
class SendOTPView(APIView):
    permission_classes = [AllowAny]

    @swagger_auto_schema(request_body=SendOTPSerializer)
    def post(self, request):
        serializer = SendOTPSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(
                {'message': 'OTP sent successfully'},
                status=status.HTTP_200_OK
            )
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


# ================= VERIFY OTP =================
class VerifyOTPView(APIView):
    permission_classes = [AllowAny]

    @swagger_auto_schema(request_body=VerifyOTPSerializer)
    def post(self, request):
        serializer = VerifyOTPSerializer(data=request.data)
        if serializer.is_valid():
            otp_instance = serializer.validated_data['otp_instance']
            otp_instance.is_used = True
            otp_instance.save()

            return Response(
                {'message': 'OTP verified successfully'},
                status=status.HTTP_200_OK
            )
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


# ================= CREATE ACCOUNT =================
class CreateAccountView(APIView):
    permission_classes = [AllowAny]

    @swagger_auto_schema(request_body=CreateAccountSerializer)
    def post(self, request):
        serializer = CreateAccountSerializer(data=request.data)
        if serializer.is_valid():
            user = serializer.save()
            refresh = RefreshToken.for_user(user)

            return Response({
                'refresh': str(refresh),
                'access': str(refresh.access_token),
                'user': {
                    'id': str(user.id),
                    'email': user.email,
                    'first_name': user.first_name,
                    'last_name': user.last_name,
                    'role': user.role
                }
            }, status=status.HTTP_201_CREATED)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


# ================= LOGIN =================
class LoginView(APIView):
    permission_classes = [AllowAny]

    @swagger_auto_schema(request_body=LoginSerializer)
    def post(self, request):
        email = request.data.get('email')
        password = request.data.get('password')

        user = authenticate(username=email, password=password)

        if user and user.is_email_verified:
            refresh = RefreshToken.for_user(user)
            return Response({
                'refresh': str(refresh),
                'access': str(refresh.access_token),
                'user': {
                    'id': str(user.id),
                    'email': user.email,
                    'first_name': user.first_name,
                    'last_name': user.last_name,
                    'role': user.role
                }
            }, status=status.HTTP_200_OK)

        return Response(
            {'error': 'Invalid credentials or email not verified'},
            status=status.HTTP_401_UNAUTHORIZED
        )


# ================= UPDATE ROLE =================
class UpdateRoleView(APIView):
    permission_classes = [IsAuthenticated]

    def patch(self, request):
        user = request.user
        role = request.data.get('role')
        
        if role not in ['candidate', 'hr']:
            return Response(
                {'error': 'Invalid role'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        user.role = role
        user.save()
        
        return Response(
            {'message': 'Role updated successfully'},
            status=status.HTTP_200_OK
        )


class RefreshTokenView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        try:
            refresh_token = request.data.get('refresh')
            if not refresh_token:
                return Response(
                    {'error': 'Refresh token required'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            serializer = TokenRefreshSerializer(data={'refresh': refresh_token})
            if serializer.is_valid():
                return Response(serializer.validated_data, status=status.HTTP_200_OK)
            else:
                return Response(
                    {'error': 'Invalid refresh token'},
                    status=status.HTTP_401_UNAUTHORIZED
                )
        except Exception as e:
            return Response(
                {'error': 'Token refresh failed'},
                status=status.HTTP_401_UNAUTHORIZED
            )



# ================= LOGOUT =================
class LogoutView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        try:
            refresh_token = request.data.get('refresh')
            token = RefreshToken(refresh_token)
            token.blacklist()
            return Response(
                {'message': 'Logged out successfully'},
                status=status.HTTP_200_OK
            )
        except Exception:
            return Response(
                {'message': 'Logged out successfully'},
                status=status.HTTP_200_OK
            )
# ================= UPDATE FCM TOKEN =================
class UpdateFCMTokenView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        try:
            token = request.data.get('token')
            if token:
                user = request.user
                user.fcm_token = token
                user.save()
                return Response({'success': True}, status=status.HTTP_200_OK)
            return Response({'error': 'Token required'}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
from rest_framework import serializers
from .models import User, EmailOTP
from .utils import send_otp_email

# Login Serializer (Swagger ke liye)
class LoginSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField()


class SendOTPSerializer(serializers.Serializer):
    email = serializers.EmailField()
    
    def validate_email(self, value):
        if User.objects.filter(email=value).exists():
            raise serializers.ValidationError('This email is already registered. Please login instead.')
        return value
    
    def create(self, validated_data):
        email = validated_data['email']
        otp_instance = EmailOTP.generate_otp(email)
        send_otp_email(email, otp_instance.otp)
        return otp_instance

class VerifyOTPSerializer(serializers.Serializer):
    email = serializers.EmailField()
    otp = serializers.CharField(max_length=6)
    
    def validate(self, attrs):
        email = attrs.get('email')
        otp = attrs.get('otp')
        
        otp_instance = EmailOTP.objects.filter(
            email=email, otp=otp, is_used=False
        ).first()
        
        if not otp_instance or otp_instance.is_expired():
            raise serializers.ValidationError('Invalid or expired OTP')
        
        attrs['otp_instance'] = otp_instance
        return attrs

class CreateAccountSerializer(serializers.Serializer):
    email = serializers.EmailField()
    username = serializers.CharField(max_length=150, required=False, allow_blank=True)
    first_name = serializers.CharField(max_length=50, required=False, allow_blank=True)
    last_name = serializers.CharField(max_length=50, required=False, allow_blank=True)
    password = serializers.CharField(min_length=6)
    confirm_password = serializers.CharField()
    
    def validate_email(self, value):
        if User.objects.filter(email=value).exists():
            raise serializers.ValidationError('User with this email already exists')
        return value
    
    def validate(self, attrs):
        if attrs['password'] != attrs['confirm_password']:
            raise serializers.ValidationError("Passwords don't match")
        
        # Check if OTP was verified for this email
        verified_otp = EmailOTP.objects.filter(
            email=attrs['email'], 
            is_used=True
        ).order_by('-created_at').first()
        
        if not verified_otp:
            raise serializers.ValidationError('Email not verified. Please verify OTP first.')
        
        return attrs
    
    def create(self, validated_data):
        validated_data.pop('confirm_password')
        password = validated_data.pop('password')

        # Generate username from email if not provided
        if not validated_data.get('username'):
            validated_data['username'] = validated_data['email'].split('@')[0]

        user = User.objects.create_user(
            password=password,
            is_email_verified=True,
            **validated_data
        )
        return user
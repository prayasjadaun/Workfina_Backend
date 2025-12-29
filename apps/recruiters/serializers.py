# serializers.py
from rest_framework import serializers
from .models import HRProfile

class HRRegistrationSerializer(serializers.ModelSerializer):
    class Meta:
        model = HRProfile
        fields = [
            'full_name',
            'company_name', 'designation', 'phone', 
            'company_website', 'company_size'
        ]
    
    def create(self, validated_data):
        user = self.context['request'].user
        validated_data['user'] = user
        return super().create(validated_data)

class HRProfileSerializer(serializers.ModelSerializer):
    email = serializers.CharField(source='user.email', read_only=True)
    balance = serializers.SerializerMethodField()
    total_spent = serializers.SerializerMethodField()
    
    class Meta:
        model = HRProfile
        fields = [
            'email','full_name',
            'company_name', 'designation', 'phone',
            'company_website', 'company_size', 'balance', 'total_spent',
            'is_verified'
        ]
        read_only_fields = ['email', 'balance', 'total_spent', 'is_verified'] 
    
    def get_balance(self, obj):
        try:
            return obj.wallet.balance
        except:
            return 0
    
    def get_total_spent(self, obj):
        try:
            return obj.wallet.total_spent
        except:
            return 0
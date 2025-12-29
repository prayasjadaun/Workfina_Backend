from rest_framework import serializers
from django.contrib.auth import get_user_model
from .models import Candidate, UnlockHistory

User = get_user_model()

class CandidateRegistrationSerializer(serializers.ModelSerializer):
    """Serializer for candidate profile creation"""
    
    class Meta:
        model = Candidate
        fields = [
            'full_name', 'phone', 'age', 'role', 'experience_years',
            'current_ctc', 'expected_ctc', 'religion', 'country',
            'state', 'city', 'education', 'skills', 'resume'
        ]
    
    def create(self, validated_data):
        user = self.context['request'].user
        validated_data['user'] = user
        return super().create(validated_data)

class MaskedCandidateSerializer(serializers.ModelSerializer):
    """Serializer for masked candidate data (before unlock)"""
    
    class Meta:
        model = Candidate
        fields = [
            'id', 'masked_name', 'role', 'experience_years',
            'city', 'age', 'skills', 'is_active'
        ]

class FullCandidateSerializer(serializers.ModelSerializer):
    """Serializer for full candidate data (after unlock)"""
    
    skills_list = serializers.SerializerMethodField()
    email = serializers.CharField(source='user.email', read_only=True)
    credits_used = serializers.IntegerField(read_only=True, required=False)
    
    class Meta:
        model = Candidate
        fields = [
            'id', 'full_name', 'email', 'phone', 'age',
            'role', 'experience_years', 'current_ctc', 'expected_ctc',
            'religion', 'country', 'state', 'city',
            'education', 'skills', 'skills_list', 'resume', 'credits_used'
        ]
    
    def get_skills_list(self, obj):
        return obj.get_skills_list()

class CandidateFilterSerializer(serializers.Serializer):
    """Serializer for candidate filtering"""
    
    role = serializers.ChoiceField(choices=Candidate.ROLE_CHOICES, required=False)
    min_experience = serializers.IntegerField(required=False, min_value=0)
    max_experience = serializers.IntegerField(required=False)
    city = serializers.CharField(required=False, max_length=100)
    state = serializers.CharField(required=False, max_length=100)
    religion = serializers.ChoiceField(choices=Candidate.RELIGION_CHOICES, required=False)
    skills = serializers.CharField(required=False)
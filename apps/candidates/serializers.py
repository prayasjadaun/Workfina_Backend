from rest_framework import serializers
from django.contrib.auth import get_user_model
from .models import Candidate, UnlockHistory, FilterCategory, FilterOption

User = get_user_model()

class CandidateRegistrationSerializer(serializers.ModelSerializer):
    # Accept strings for foreign key fields
    role = serializers.CharField(write_only=True)
    religion = serializers.CharField(write_only=True)
    country = serializers.CharField(write_only=True)
    state = serializers.CharField(write_only=True)
    city = serializers.CharField(write_only=True)
    education = serializers.CharField(write_only=True)
    
    class Meta:
        model = Candidate
        fields = [
            'full_name', 'phone', 'age', 'role', 'experience_years',
            'current_ctc', 'expected_ctc', 'religion', 'country',
            'state', 'city', 'education', 'skills', 'resume', 'video_intro'
        ]
        extra_kwargs = {
            'resume': {'required': False, 'allow_null': True},
            'video_intro': {'required': False, 'allow_null': True},
        }

    def validate(self, data):
        # Create/get categories first (with default creation if not exist)
        dept_category, _ = FilterCategory.objects.get_or_create(
            slug='department',
            defaults={'name': 'Department', 'display_order': 1}
        )
        religion_category, _ = FilterCategory.objects.get_or_create(
            slug='religion', 
            defaults={'name': 'Religion', 'display_order': 2}
        )
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
        education_category, _ = FilterCategory.objects.get_or_create(
            slug='education',
            defaults={'name': 'Education', 'display_order': 6}
        )

        # Create/get role
        role_name = data.get('role')
        if role_name:
            role, _ = FilterOption.objects.get_or_create(
                category=dept_category,
                name=role_name,
                defaults={'slug': role_name.lower().replace(' ', '-'), 'is_active': True}
            )
            data['role'] = role

        # Create/get religion
        religion_name = data.get('religion')
        if religion_name:
            religion, _ = FilterOption.objects.get_or_create(
                category=religion_category,
                name=religion_name,
                defaults={'slug': religion_name.lower(), 'is_active': True}
            )
            data['religion'] = religion

        # Create/get education
        education_name = data.get('education')
        if education_name:
            # Normalize education to standard levels
            if '10th' in education_name or 'tenth' in education_name.lower():
                normalized_education = '10th'
            elif '12th' in education_name or 'twelfth' in education_name.lower():
                normalized_education = '12th'
            elif 'graduation' in education_name.lower() or 'bachelor' in education_name.lower():
                normalized_education = 'Graduation'
            elif 'post' in education_name.lower() or 'master' in education_name.lower():
                normalized_education = 'Post Graduation'
            else:
                normalized_education = 'Other'
            
            education, _ = FilterOption.objects.get_or_create(
                category=education_category,
                name=normalized_education,
                defaults={'slug': normalized_education.lower().replace(' ', '-'), 'is_active': True}
            )
            data['education'] = education

        # Default country to India
        country_name = data.get('country', 'India')  # Default to India
        country, _ = FilterOption.objects.get_or_create(
            category=country_category,
            name=country_name,
            defaults={'slug': country_name.lower(), 'is_active': True}
        )
        data['country'] = country

        # Create/get state with country reference
        state_name = data.get('state')
        if state_name:
            state, _ = FilterOption.objects.get_or_create(
                category=state_category,
                name=state_name,
                parent=country,
                defaults={'slug': state_name.lower().replace(' ', '-'), 'is_active': True}
            )
            data['state'] = state
        else:
            state = None

        # Create/get city with state reference
        city_name = data.get('city')
        if city_name and state:
            city, _ = FilterOption.objects.get_or_create(
                category=city_category,
                name=city_name,
                parent=state,
                defaults={'slug': city_name.lower(), 'is_active': True}
            )
            data['city'] = city

        return data

    def create(self, validated_data):
        user = self.context['request'].user
        validated_data['user'] = user
        return super().create(validated_data)

class MaskedCandidateSerializer(serializers.ModelSerializer):
    role_name = serializers.CharField(source='role.name', read_only=True)
    city_name = serializers.CharField(source='city.name', read_only=True)
    
    class Meta:
        model = Candidate
        fields = [
            'id', 'masked_name', 'role_name', 'experience_years',
            'city_name', 'age', 'skills', 'is_active'
        ]

class FullCandidateSerializer(serializers.ModelSerializer):
    skills_list = serializers.SerializerMethodField()
    email = serializers.CharField(source='user.email', read_only=True)
    credits_used = serializers.IntegerField(read_only=True, required=False)
    resume_url = serializers.SerializerMethodField()
    video_intro_url = serializers.SerializerMethodField()
    
    # Dynamic field names
    role_name = serializers.CharField(source='role.name', read_only=True)
    religion_name = serializers.CharField(source='religion.name', read_only=True)
    country_name = serializers.CharField(source='country.name', read_only=True)
    state_name = serializers.CharField(source='state.name', read_only=True)
    city_name = serializers.CharField(source='city.name', read_only=True)
    education_name = serializers.CharField(source='education.name', read_only=True)

    class Meta:
        model = Candidate
        fields = [
            'id', 'full_name', 'email', 'phone', 'age',
            'role_name', 'experience_years', 'current_ctc', 'expected_ctc',
            'religion_name', 'country_name', 'state_name', 'city_name',
            'education_name', 'skills', 'skills_list', 
            'resume_url', 'video_intro_url', 'credits_used'
        ]
    
    def get_skills_list(self, obj):
        return obj.get_skills_list()
    
    def get_resume_url(self, obj):
        if obj.resume:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.resume.url)
            return obj.resume.url
        return None
        
    def get_video_intro_url(self, obj):
        if obj.video_intro:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.video_intro.url)
            return obj.video_intro.url
        return None
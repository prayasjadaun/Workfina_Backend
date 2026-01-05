from rest_framework import serializers
from django.contrib.auth import get_user_model
from .models import Candidate, UnlockHistory, FilterCategory, FilterOption, CandidateNote, CandidateFollowup, WorkExperience, Education

User = get_user_model()

class WorkExperienceSerializer(serializers.ModelSerializer):
    class Meta:
        model = WorkExperience
        fields = ['id', 'company_name', 'role_title', 'start_date', 'end_date', 'is_current', 'location', 'description']

class EducationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Education
        fields = ['id', 'institution_name', 'degree', 'field_of_study', 'start_year', 'end_year', 'is_ongoing', 'grade_percentage', 'location']

class CandidateNoteSerializer(serializers.ModelSerializer):
    class Meta:
        model = CandidateNote
        fields = ['id', 'note_text', 'created_at', 'updated_at']
        read_only_fields = ['id', 'created_at', 'updated_at']

class CandidateFollowupSerializer(serializers.ModelSerializer):
    class Meta:
        model = CandidateFollowup
        fields = ['id', 'followup_date', 'notes', 'is_completed', 'created_at', 'updated_at']
        read_only_fields = ['id', 'created_at', 'updated_at']

class CandidateRegistrationSerializer(serializers.ModelSerializer):
    # Accept strings for foreign key fields
    role = serializers.CharField(write_only=True)
    religion = serializers.CharField(write_only=True)
    country = serializers.CharField(write_only=True)
    state = serializers.CharField(write_only=True)
    city = serializers.CharField(write_only=True)
    
    class Meta:
        model = Candidate
        fields = [
            'full_name', 'phone', 'age', 'role', 'experience_years',
            'current_ctc', 'expected_ctc', 'religion', 'country',
            'state', 'city', 'skills', 'resume', 'video_intro', 'profile_image',
            'languages', 'street_address', 'willing_to_relocate', 'career_objective'
        ]
        extra_kwargs = {
            'resume': {'required': False, 'allow_null': True},
            'video_intro': {'required': False, 'allow_null': True},
            'profile_image': {'required': False, 'allow_null': True},
            'languages': {'required': False, 'allow_blank': True},
            'street_address': {'required': False, 'allow_blank': True},
            'willing_to_relocate': {'required': False},
            'work_experience': {'required': False, 'allow_blank': True},
            'career_objective': {'required': False, 'allow_blank': True},
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

        # Create/get role - Check if already FilterOption
        role_name = data.get('role')
        if role_name:
            if isinstance(role_name, FilterOption):
                data['role'] = role_name
            else:
                role, _ = FilterOption.objects.get_or_create(
                    category=dept_category,
                    name=role_name,
                    defaults={'slug': role_name.lower().replace(' ', '-'), 'is_active': True}
                )
                data['role'] = role

        # Create/get religion - Check if already FilterOption
        religion_name = data.get('religion')
        if religion_name:
            if isinstance(religion_name, FilterOption):
                data['religion'] = religion_name
            else:
                religion, _ = FilterOption.objects.get_or_create(
                    category=religion_category,
                    name=religion_name,
                    defaults={'slug': religion_name.lower(), 'is_active': True}
                )
                data['religion'] = religion

        # Default country to India - Check if already FilterOption
        country_name = data.get('country', 'India')
        if isinstance(country_name, FilterOption):
            country = country_name
        else:
            country, _ = FilterOption.objects.get_or_create(
                category=country_category,
                name=country_name,
                defaults={'slug': country_name.lower(), 'is_active': True}
            )
        data['country'] = country

        # Create/get state - Check if already FilterOption
        state_name = data.get('state')
        if state_name:
            if isinstance(state_name, FilterOption):
                state = state_name
            else:
                state, _ = FilterOption.objects.get_or_create(
                    category=state_category,
                    slug=state_name.lower().replace(' ', '-'),
                    defaults={'name': state_name.title(), 'parent': country, 'is_active': True}
                )
            data['state'] = state
        else:
            state = None

        # Create/get city - Check if already FilterOption
        city_name = data.get('city')
        if city_name and state:
            if isinstance(city_name, FilterOption):
                data['city'] = city_name
            else:
                city, _ = FilterOption.objects.get_or_create(
                    category=city_category,
                    slug=city_name.lower().replace(' ', '-'),
                    defaults={'name': city_name.title(), 'parent': state, 'is_active': True}
                )
                data['city'] = city

        return data

    def create(self, validated_data):
        user = self.context['request'].user
        validated_data['user'] = user
        return super().create(validated_data)

    def update(self, instance, validated_data):
        # Apply same validation for updates
        validated_data = self.validate(validated_data)
        return super().update(instance, validated_data)


class MaskedCandidateSerializer(serializers.ModelSerializer):
    role_name = serializers.CharField(source='role.name', read_only=True)
    city_name = serializers.CharField(source='city.name', read_only=True)
    profile_image_url = serializers.SerializerMethodField()
    
    class Meta:
        model = Candidate
        fields = [
            'id', 'masked_name', 'role_name', 'experience_years',
            'city_name', 'age', 'skills', 'profile_image_url', 'is_active'
        ]
    
    def get_profile_image_url(self, obj):
        if hasattr(obj, 'profile_image') and obj.profile_image:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.profile_image.url)
            return obj.profile_image.url
        return None


class FullCandidateSerializer(serializers.ModelSerializer):
    skills_list = serializers.SerializerMethodField()
    email = serializers.CharField(source='user.email', read_only=True)
    credits_used = serializers.IntegerField(read_only=True, required=False)
    resume_url = serializers.SerializerMethodField()
    video_intro_url = serializers.SerializerMethodField()
    profile_image_url = serializers.SerializerMethodField()
    
    # Dynamic field names for FilterOptions
    role_name = serializers.CharField(source='role.name', read_only=True)
    religion_name = serializers.CharField(source='religion.name', read_only=True)
    country_name = serializers.CharField(source='country.name', read_only=True)
    state_name = serializers.CharField(source='state.name', read_only=True)
    city_name = serializers.CharField(source='city.name', read_only=True)
    
    # Add work experience and education data
    work_experiences = WorkExperienceSerializer(many=True, read_only=True)
    educations = EducationSerializer(many=True, read_only=True)

    class Meta:
        model = Candidate
        fields = [
            'id', 'full_name', 'email', 'phone', 'age',
            'role_name', 'experience_years', 'current_ctc', 'expected_ctc',
            'religion_name', 'country_name', 'state_name', 'city_name',
            'skills', 'skills_list', 
            'resume_url', 'video_intro_url', 'profile_image_url', 'credits_used',
            'languages', 'street_address', 'willing_to_relocate', 'career_objective',
            'work_experiences', 'educations'
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
    
    def get_profile_image_url(self, obj):
        if hasattr(obj, 'profile_image') and obj.profile_image:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.profile_image.url)
            return obj.profile_image.url
        return None


class UnlockHistorySerializer(serializers.ModelSerializer):
    candidate_name = serializers.CharField(source='candidate.masked_name', read_only=True)
    hr_email = serializers.CharField(source='hr_user.user.email', read_only=True)
    
    class Meta:
        model = UnlockHistory
        fields = [
            'id', 'candidate_name', 'hr_email', 'credits_used', 'unlocked_at'
        ]
        read_only_fields = ['unlocked_at']


class FilterCategorySerializer(serializers.ModelSerializer):
    options_count = serializers.SerializerMethodField()
    icon_url = serializers.SerializerMethodField()
    
    class Meta:
        model = FilterCategory
        fields = [
            'id', 'name', 'slug', 'icon_url', 'display_order', 
            'is_active', 'options_count', 'created_at'
        ]
    
    def get_options_count(self, obj):
        return obj.options.filter(is_active=True).count()
    
    def get_icon_url(self, obj):
        if obj.icon:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.icon.url)
            return obj.icon.url
        return None


class FilterOptionSerializer(serializers.ModelSerializer):
    category_name = serializers.CharField(source='category.name', read_only=True)
    parent_name = serializers.CharField(source='parent.name', read_only=True)
    candidates_count = serializers.SerializerMethodField()
    
    class Meta:
        model = FilterOption
        fields = [
            'id', 'name', 'slug', 'category_name', 'parent_name',
            'display_order', 'is_active', 'candidates_count', 'created_at'
        ]
    
    def get_candidates_count(self, obj):
        # Count candidates using this filter option in any relevant field
        from django.db.models import Q
        count = Candidate.objects.filter(
            Q(role=obj) | Q(religion=obj) | Q(country=obj) | 
            Q(state=obj) | Q(city=obj) | Q(education=obj),
            is_active=True
        ).count()
        return count


class CandidateUpdateSerializer(serializers.ModelSerializer):
    """Serializer for candidate profile updates"""
    role = serializers.CharField(required=False)
    religion = serializers.CharField(required=False)
    country = serializers.CharField(required=False)
    state = serializers.CharField(required=False)
    city = serializers.CharField(required=False)
    
    class Meta:
        model = Candidate
        fields = [
            'full_name', 'phone', 'age', 'role', 'experience_years',
            'current_ctc', 'expected_ctc', 'religion', 'country',
            'state', 'city', 'skills', 'resume', 'video_intro','profile_image',
            'languages', 'street_address', 'willing_to_relocate', 'work_experience', 'career_objective'

        ]
        extra_kwargs = {
            'resume': {'required': False, 'allow_null': True},
            'video_intro': {'required': False, 'allow_null': True},
            'profile_image': {'required': False, 'allow_null': True},
            'languages': {'required': False, 'allow_blank': True},
            'street_address': {'required': False, 'allow_blank': True},
            'willing_to_relocate': {'required': False},
            'work_experience': {'required': False, 'allow_blank': True},
            'career_objective': {'required': False, 'allow_blank': True},
        }

    def validate(self, data):
        # Use same conversion logic but don't call parent validate to avoid recursion
        return self._convert_to_filter_options(data)
        
    def _convert_to_filter_options(self, data):
        """Convert string values to FilterOption instances"""
        # Create/get categories
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
        
        # Convert role - check if it's already a FilterOption
        role_value = data.get('role')
        if role_value:
            if isinstance(role_value, FilterOption):
                data['role'] = role_value
            else:
                role, _ = FilterOption.objects.get_or_create(
                    category=dept_category,
                    name=role_value,
                    defaults={'slug': role_value.lower().replace(' ', '-'), 'is_active': True}
                )
                data['role'] = role
        
        # Convert religion - check if it's already a FilterOption
        religion_value = data.get('religion')
        if religion_value:
            if isinstance(religion_value, FilterOption):
                data['religion'] = religion_value
            else:
                religion, _ = FilterOption.objects.get_or_create(
                    category=religion_category,
                    name=religion_value,
                    defaults={'slug': religion_value.lower(), 'is_active': True}
                )
                data['religion'] = religion
        
        # Default country to India
        country_value = data.get('country', 'India')
        if isinstance(country_value, FilterOption):
            country = country_value
        else:
            country, _ = FilterOption.objects.get_or_create(
                category=country_category,
                name=country_value,
                defaults={'slug': country_value.lower(), 'is_active': True}
            )
        data['country'] = country
        
        # Convert state - check if it's already a FilterOption
        state_value = data.get('state')
        if state_value:
            if isinstance(state_value, FilterOption):
                state = state_value
            else:
                state, _ = FilterOption.objects.get_or_create(
                    category=state_category,
                    slug=state_value.lower().replace(' ', '-'),
                    defaults={'name': state_value.title(), 'parent': country, 'is_active': True}
                )
            data['state'] = state
        else:
            state = None
        
        # Convert city
        city_value = data.get('city')
        if city_value and state:
            if isinstance(city_value, FilterOption):
                data['city'] = city_value
            else:
                city, _ = FilterOption.objects.get_or_create(
                    category=city_category,
                    slug=city_value.lower().replace(' ', '-'),
                    defaults={'name': city_value.title(), 'parent': state, 'is_active': True}
                )
                data['city'] = city
        
        return data

    def update(self, instance, validated_data):
        # Don't allow user change
        validated_data.pop('user', None)
        return super().update(instance, validated_data)
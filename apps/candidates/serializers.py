from rest_framework import serializers
from django.contrib.auth import get_user_model
from .models import Candidate, UnlockHistory, FilterCategory, FilterOption, CandidateNote, CandidateFollowup, WorkExperience, Education
from django.utils import timezone
import pytz

User = get_user_model()

class WorkExperienceSerializer(serializers.ModelSerializer):
    class Meta:
        model = WorkExperience
        fields = ['id', 'company_name', 'role_title', 'start_date', 'end_date', 'is_current', 'current_ctc','location', 'description']

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
    role = serializers.CharField(write_only=True)
    religion = serializers.CharField(write_only=True)
    country = serializers.CharField(write_only=True)
    state = serializers.CharField(write_only=True)
    city = serializers.CharField(write_only=True)
    
    class Meta:
        model = Candidate
        fields = [
           'first_name','last_name', 'phone', 'age', 'role', 'experience_years',
             'religion', 'country',
            'state', 'city', 'skills', 'resume', 'video_intro', 'profile_image',
            'languages', 'street_address', 'willing_to_relocate', 'career_objective','joining_availability', 'notice_period_details'
        ]
        extra_kwargs = {
        'first_name': {'required': True},
        'last_name': {'required': True},
        'phone': {'required': True},
        'age': {'required': True},
        'role': {'required': True},
        'state': {'required': True},
        'city': {'required': True},
        'religion': {'required': True},
        'languages': {'required': True},
        'street_address': {'required': True},
        'career_objective': {'required': True},
        # 'current_ctc': {'required': False},
        # 'expected_ctc': {'required': False},
        'joining_availability': {'required': True},
        'notice_period_details': {'required': True},  
        'resume': {'required': False},
        'video_intro': {'required': False},
        'profile_image': {'required': True},
        'experience_years': {'required': False},
        'country': {'required': False},
        'skills': {'required': False},
        'willing_to_relocate': {'required': False}
    }
        
        def validate_willing_to_relocate(self, value):
        # """Convert YES/NO to boolean"""
            if isinstance(value, bool):
               return value
            if isinstance(value, str):
              return value.upper() == 'YES'
            return False

        def validate(self, data):
        # Validate notice period
         if data.get('joining_availability') == 'NOTICE_PERIOD':
            if not data.get('notice_period_details'):
                raise serializers.ValidationError({
                    'notice_period_details': 'Required when joining availability is notice period'
                })

    def validate(self, data):
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

        role_name = data.get('role')
        if role_name and not isinstance(role_name, FilterOption):
            role_slug = role_name.lower().replace(' ', '-')
            try:
                data['role'] = FilterOption.objects.get(category=dept_category, slug=role_slug)
            except FilterOption.DoesNotExist:
                data['role'] = FilterOption.objects.create(
                    category=dept_category,
                    slug=role_slug,
                    name=role_name,
                    is_active=True
                )

        religion_name = data.get('religion')
        if religion_name and not isinstance(religion_name, FilterOption):
            religion_slug = religion_name.lower().replace(' ', '-')
            try:
                data['religion'] = FilterOption.objects.get(category=religion_category, slug=religion_slug)
            except FilterOption.DoesNotExist:
                data['religion'] = FilterOption.objects.create(
                    category=religion_category,
                    slug=religion_slug,
                    name=religion_name,
                    is_active=True
                )

        country_name = data.get('country', 'India')
        if not isinstance(country_name, FilterOption):
            country_slug = country_name.lower().replace(' ', '-')
            try:
                country = FilterOption.objects.get(category=country_category, slug=country_slug)
            except FilterOption.DoesNotExist:
                country = FilterOption.objects.create(
                    category=country_category,
                    slug=country_slug,
                    name=country_name,
                    is_active=True
                )
            data['country'] = country

        state_name = data.get('state')
        state = None
        if state_name and not isinstance(state_name, FilterOption):
            state_slug = state_name.lower().replace(' ', '-')
            try:
                state = FilterOption.objects.get(category=state_category, slug=state_slug)
            except FilterOption.DoesNotExist:
                state = FilterOption.objects.create(
                    category=state_category,
                    slug=state_slug,
                    name=state_name.title(),
                    parent=data.get('country'),
                    is_active=True
                )
            data['state'] = state
        elif isinstance(state_name, FilterOption):
            state = state_name
            data['state'] = state

        city_name = data.get('city')
        if city_name and state and not isinstance(city_name, FilterOption):
            city_slug = f"{state.slug}-{city_name.lower().replace(' ', '-')}"
            try:
                data['city'] = FilterOption.objects.get(category=city_category, slug=city_slug)
            except FilterOption.DoesNotExist:
                data['city'] = FilterOption.objects.create(
                    category=city_category,
                    slug=city_slug,
                    name=city_name.title(),
                    parent=state,
                    is_active=True
                )

        return data

    def create(self, validated_data):
        user = self.context['request'].user
        validated_data['user'] = user
        return super().create(validated_data)

    def update(self, instance, validated_data):
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
            'city_name', 'age', 'skills', 'profile_image_url', 'is_active', 'is_available_for_hiring'
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
    last_availability_update = serializers.SerializerMethodField()

    role_name = serializers.CharField(source='role.name', read_only=True)
    religion_name = serializers.CharField(source='religion.name', read_only=True)
    country_name = serializers.CharField(source='country.name', read_only=True)
    state_name = serializers.CharField(source='state.name', read_only=True)
    city_name = serializers.CharField(source='city.name', read_only=True)

    work_experiences = WorkExperienceSerializer(many=True, read_only=True)
    educations = EducationSerializer(many=True, read_only=True)

    class Meta:
        model = Candidate
        fields = [
            'id', 'first_name', 'last_name', 'email', 'phone', 'age',
            'role_name', 'experience_years',
            'religion_name', 'country_name', 'state_name', 'city_name',
            'skills', 'skills_list',
            'resume_url', 'video_intro_url', 'profile_image_url', 'credits_used',
            'languages', 'street_address', 'willing_to_relocate', 'career_objective',
            'work_experiences', 'educations','profile_step', 'is_profile_completed',
            'joining_availability', 'notice_period_details',
            'is_available_for_hiring', 'last_availability_update',
            'has_agreed_to_declaration', 'declaration_agreed_at'
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

    def get_last_availability_update(self, obj):
        if obj.last_availability_update:
            ist = pytz.timezone('Asia/Kolkata')
            ist_time = obj.last_availability_update.astimezone(ist)
            return ist_time.strftime('%d %b %Y, %I:%M %p IST')
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
            'is_active', 'options_count', 'created_at', 
            'bento_grid', 'dashboard_display', 'inner_filter'
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
        from django.db.models import Q
        count = Candidate.objects.filter(
            Q(role=obj) | Q(religion=obj) | Q(country=obj) | 
            Q(state=obj) | Q(city=obj),
            is_active=True
        ).count()
        return count


class CandidateUpdateSerializer(serializers.ModelSerializer):
    role = serializers.CharField(required=False)
    religion = serializers.CharField(required=False)
    country = serializers.CharField(required=False)
    state = serializers.CharField(required=False)
    city = serializers.CharField(required=False)
    
    class Meta:
        model = Candidate
        fields = [
            'first_name', 'last_name', 'phone', 'age', 'role', 'experience_years',
            'current_ctc', 'expected_ctc', 'religion', 'country',
            'state', 'city', 'skills', 'resume', 'video_intro','profile_image',
            'languages', 'street_address', 'willing_to_relocate', 'work_experience', 'career_objective','joining_availability', 'notice_period_details'
        ]
        extra_kwargs = {
            'resume': {'required': False, 'allow_null': True},
            'video_intro': {'required': False, 'allow_null': True},
            'profile_image': {'required': True, 'allow_null': False},
            'languages': {'required': False, 'allow_blank': True},
            'street_address': {'required': False, 'allow_blank': True},
            'willing_to_relocate': {'required': False},
            'work_experience': {'required': False, 'allow_blank': True},
            'career_objective': {'required': False, 'allow_blank': True},
            'joining_availability': {'required': False},
            'notice_period_details': {'required': True},
        }

    def validate(self, data):
        return self._convert_to_filter_options(data)
        
    def _convert_to_filter_options(self, data):
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
        
        role_value = data.get('role')
        if role_value and not isinstance(role_value, FilterOption):
            role_slug = role_value.lower().replace(' ', '-')
            try:
                data['role'] = FilterOption.objects.get(category=dept_category, slug=role_slug)
            except FilterOption.DoesNotExist:
                data['role'] = FilterOption.objects.create(
                    category=dept_category,
                    slug=role_slug,
                    name=role_value,
                    is_active=True
                )
        
        religion_value = data.get('religion')
        if religion_value and not isinstance(religion_value, FilterOption):
            religion_slug = religion_value.lower().replace(' ', '-')
            try:
                data['religion'] = FilterOption.objects.get(category=religion_category, slug=religion_slug)
            except FilterOption.DoesNotExist:
                data['religion'] = FilterOption.objects.create(
                    category=religion_category,
                    slug=religion_slug,
                    name=religion_value,
                    is_active=True
                )
        
        country_value = data.get('country', 'India')
        if not isinstance(country_value, FilterOption):
            country_slug = country_value.lower().replace(' ', '-')
            try:
                country = FilterOption.objects.get(category=country_category, slug=country_slug)
            except FilterOption.DoesNotExist:
                country = FilterOption.objects.create(
                    category=country_category,
                    slug=country_slug,
                    name=country_value,
                    is_active=True
                )
            data['country'] = country
        
        state_value = data.get('state')
        state = None
        if state_value and not isinstance(state_value, FilterOption):
            state_slug = state_value.lower().replace(' ', '-')
            try:
                state = FilterOption.objects.get(category=state_category, slug=state_slug)
            except FilterOption.DoesNotExist:
                state = FilterOption.objects.create(
                    category=state_category,
                    slug=state_slug,
                    name=state_value.title(),
                    parent=data.get('country'),
                    is_active=True
                )
            data['state'] = state
        elif isinstance(state_value, FilterOption):
            state = state_value
            data['state'] = state
        
        city_value = data.get('city')
        if city_value and state and not isinstance(city_value, FilterOption):
            city_slug = f"{state.slug}-{city_value.lower().replace(' ', '-')}"
            try:
                data['city'] = FilterOption.objects.get(category=city_category, slug=city_slug)
            except FilterOption.DoesNotExist:
                data['city'] = FilterOption.objects.create(
                    category=city_category,
                    slug=city_slug,
                    name=city_value.title(),
                    parent=state,
                    is_active=True
                )
        
        return data

    def update(self, instance, validated_data):
        validated_data.pop('user', None)
        return super().update(instance, validated_data)
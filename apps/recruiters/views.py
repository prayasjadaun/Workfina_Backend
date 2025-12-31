from rest_framework import status, generics
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django.db.models import Q
from .models import HRProfile
from .serializers import HRRegistrationSerializer, HRProfileSerializer
from apps.candidates.models import Candidate, UnlockHistory
from apps.candidates.serializers import MaskedCandidateSerializer, FullCandidateSerializer

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


from django.core.paginator import Paginator

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def filter_candidates(request):
    """Filter candidates API for HR users"""
    
    if request.user.role != 'hr':
        return Response({
            'error': 'Only HR users can access this'
        }, status=status.HTTP_403_FORBIDDEN)
    
    # Debug logging
    print(f"[DEBUG] Filter parameters received: {dict(request.query_params)}")
    
    try:
        # Check if HR profile exists
        hr_profile = request.user.hr_profile
        
        # Check if company is verified
        if not hr_profile.is_verified:
            return Response({
                'error': 'Company verification pending. Cannot view candidates.'
            }, status=status.HTTP_403_FORBIDDEN)
        
    except HRProfile.DoesNotExist:
        return Response({
            'error': 'HR profile not found'
        }, status=status.HTTP_404_NOT_FOUND)
    
    # Get filter and pagination parameters
    role = request.query_params.get('role')
    min_experience = request.query_params.get('min_experience')
    max_experience = request.query_params.get('max_experience')
    min_age = request.query_params.get('min_age')
    max_age = request.query_params.get('max_age')
    city = request.query_params.get('city')
    state = request.query_params.get('state')
    country = request.query_params.get('country')
    religion = request.query_params.get('religion')
    education = request.query_params.get('education')
    skills = request.query_params.get('skills')
    min_ctc = request.query_params.get('min_ctc')
    max_ctc = request.query_params.get('max_ctc')
    
    # Pagination parameters
    page = int(request.query_params.get('page', 1))
    page_size = int(request.query_params.get('page_size', 20))
    
    # Base queryset
    queryset = Candidate.objects.filter(is_active=True)
    
    # Apply filters
    if role and role != 'All':
        queryset = queryset.filter(role=role)
        
    if min_experience:
        try:
            queryset = queryset.filter(experience_years__gte=int(min_experience))
        except ValueError:
            pass
            
    if max_experience:
        try:
            queryset = queryset.filter(experience_years__lte=int(max_experience))
        except ValueError:
            pass
            
    if min_age:
        try:
            queryset = queryset.filter(age__gte=int(min_age))
        except ValueError:
            pass
            
    if max_age:
        try:
            queryset = queryset.filter(age__lte=int(max_age))
        except ValueError:
            pass
            
    if city:
        queryset = queryset.filter(city__icontains=city)
        
    if state:
        queryset = queryset.filter(state__icontains=state)
        
    if country:
        queryset = queryset.filter(country__icontains=country)
        
    if religion and religion != 'All':
        queryset = queryset.filter(religion__iexact=religion)
        
    if education:
        queryset = queryset.filter(education__icontains=education)
        
    if skills:
        queryset = queryset.filter(skills__icontains=skills)
        
    if min_ctc:
        try:
            queryset = queryset.filter(expected_ctc__gte=float(min_ctc))
        except (ValueError, TypeError):
            pass
            
    if max_ctc:
        try:
            queryset = queryset.filter(expected_ctc__lte=float(max_ctc))
        except (ValueError, TypeError):
            pass
    
    # Apply pagination
    paginator = Paginator(queryset, page_size)
    candidates_page = paginator.get_page(page)
    
    # Get unlocked candidate IDs for current HR user
    unlocked_ids = set(UnlockHistory.objects.filter(
        hr_user=request.user
    ).values_list('candidate_id', flat=True))
    
    # Serialize candidates based on unlock status
    candidates_data = []
    for candidate in candidates_page:
        if candidate.id in unlocked_ids:
            serializer = FullCandidateSerializer(candidate)
        else:
            serializer = MaskedCandidateSerializer(candidate)
        candidates_data.append(serializer.data)
    
    return Response({
        'success': True,
        'candidates': candidates_data,
        'pagination': {
            'current_page': page,
            'page_size': page_size,
            'total_pages': paginator.num_pages,
            'total_count': paginator.count,
            'has_next': candidates_page.has_next(),
            'has_previous': candidates_page.has_previous(),
        },
        'filters_applied': {
            'role': role,
            'experience_range': f"{min_experience}-{max_experience}",
            'age_range': f"{min_age}-{max_age}",
            'location': f"{city}, {state}, {country}",
            'religion': religion,
            'education': education,
            'skills': skills,
            'ctc_range': f"{min_ctc}-{max_ctc}"
        }
    })
        

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_filter_options(request):
    """Get all filter options for candidate filtering"""
    
    if request.user.role != 'hr':
        return Response({
            'error': 'Only HR users can access this'
        }, status=status.HTTP_403_FORBIDDEN)
    
    # Predefined departments
    predefined_departments = [
        'Information Technology', 'Software Development', 'Web Development',
        'Mobile Development', 'Data Science', 'Data Analytics', 'Machine Learning',
        'Artificial Intelligence', 'DevOps', 'Cloud Computing', 'Cybersecurity',
        'Network Administration', 'Database Administration', 'Quality Assurance',
        'UI/UX Design', 'Graphic Design', 'Product Design', 'Digital Marketing',
        'Sales', 'Business Development', 'Customer Support', 'Customer Success',
        'Human Resources', 'Finance', 'Accounting', 'Operations', 'Supply Chain',
        'Project Management', 'Product Management', 'Business Analysis',
        'Content Writing', 'Copywriting', 'Technical Writing', 'Legal',
        'Civil Engineering', 'Mechanical Engineering', 'Electrical Engineering',
        'Chemical Engineering', 'Electronics Engineering', 'Manufacturing',
        'Research & Development', 'Telecommunications', 'Healthcare',
        'Education', 'Consulting', 'Real Estate', 'Retail', 'E-commerce'
    ]
    
    # Predefined religions
    predefined_religions = [
        'Hindu', 'Muslim', 'Christian', 'Sikh', 'Buddhist', 'Jain',
        'Parsi', 'Jewish', 'Others', 'Prefer not to say'
    ]
    
    # Predefined countries
    predefined_countries = ['India', 'United States', 'Canada', 'United Kingdom', 'Australia', 'Germany', 'France', 'Singapore', 'UAE']
    
    # Predefined Indian states
    predefined_states = [
        'Andhra Pradesh', 'Arunachal Pradesh', 'Assam', 'Bihar', 'Chhattisgarh',
        'Goa', 'Gujarat', 'Haryana', 'Himachal Pradesh', 'Jharkhand', 'Karnataka',
        'Kerala', 'Madhya Pradesh', 'Maharashtra', 'Manipur', 'Meghalaya', 'Mizoram',
        'Nagaland', 'Odisha', 'Punjab', 'Rajasthan', 'Sikkim', 'Tamil Nadu',
        'Telangana', 'Tripura', 'Uttar Pradesh', 'Uttarakhand', 'West Bengal',
        'Andaman and Nicobar Islands', 'Chandigarh', 'Dadra and Nagar Haveli and Daman and Diu',
        'Delhi', 'Jammu and Kashmir', 'Ladakh', 'Lakshadweep', 'Puducherry'
    ]
    
    # Predefined major cities
    predefined_cities = [
        'Mumbai', 'Delhi', 'Bangalore', 'Kolkata', 'Chennai', 'Hyderabad',
        'Pune', 'Ahmedabad', 'Surat', 'Jaipur', 'Lucknow', 'Kanpur',
        'Nagpur', 'Indore', 'Thane', 'Bhopal', 'Visakhapatnam', 'Pimpri-Chinchwad',
        'Patna', 'Vadodara', 'Ghaziabad', 'Ludhiana', 'Agra', 'Nashik',
        'Faridabad', 'Meerut', 'Rajkot', 'Kalyan-Dombivli', 'Vasai-Virar',
        'Varanasi', 'Srinagar', 'Aurangabad', 'Dhanbad', 'Amritsar',
        'Navi Mumbai', 'Allahabad', 'Ranchi', 'Howrah', 'Coimbatore',
        'Jabalpur', 'Gwalior', 'Vijayawada', 'Jodhpur', 'Madurai',
        'Raipur', 'Kota', 'Guwahati', 'Chandigarh', 'Solapur',
        'Hubli-Dharwad', 'Bareilly', 'Moradabad', 'Mysore', 'Gurgaon',
        'Aligarh', 'Jalandhar', 'Tiruchirappalli', 'Bhubaneswar', 'Salem',
        'Mira-Bhayandar', 'Warangal', 'Thiruvananthapuram', 'Guntur',
        'Bhiwandi', 'Saharanpur', 'Gorakhpur', 'Bikaner', 'Amravati',
        'Noida', 'Jamshedpur', 'Bhilai', 'Cuttack', 'Firozabad',
        'Kochi', 'Nellore', 'Bhavnagar', 'Dehradun', 'Durgapur'
    ]
    
    # Predefined education options
    predefined_education = [
        'Bachelor of Technology', 'Bachelor of Engineering', 'Bachelor of Computer Application',
        'Bachelor of Science', 'Bachelor of Commerce', 'Bachelor of Arts',
        'Bachelor of Business Administration', 'Bachelor of Pharmacy',
        'Master of Technology', 'Master of Engineering', 'Masters of Computer Application',
        'Master of Science', 'Master of Commerce', 'Master of Arts',
        'Master of Business Administration', 'Master of Pharmacy',
        'Doctor of Philosophy', 'Diploma in Engineering', 'Polytechnic Diploma',
        'Certificate Course', 'ITI', 'Class 12th', 'Class 10th'
    ]
    
    # Get pagination parameters
    filter_type = request.query_params.get('type', 'all')
    page = int(request.query_params.get('page', 1))
    page_size = int(request.query_params.get('page_size', 20))
    search = request.query_params.get('search', '').lower()
    
    def paginate_data(data, page, page_size, search='', filter_name=''):
        # Filter data based on search
        if search:
            data = [item for item in data if search in item.lower()]
        
        total = len(data)
        start = (page - 1) * page_size
        end = start + page_size
        paginated_data = data[start:end]
        total_pages = (total + page_size - 1) // page_size
        
        # Build next and previous URLs
        base_url = f"/api/recruiters/filter-options/?type={filter_name}&page_size={page_size}"
        if search:
            base_url += f"&search={search}"
            
        next_url = f"{base_url}&page={page + 1}" if page < total_pages else None
        previous_url = f"{base_url}&page={page - 1}" if page > 1 else None
        
        return {
            'count': total,
            'next': next_url,
            'previous': previous_url,
            'results': [{'value': item, 'label': item} for item in paginated_data]
        }
    
    # Handle specific filter type requests
    if filter_type == 'departments':
        return Response(paginate_data(sorted(predefined_departments), page, page_size, search, 'departments'))
    elif filter_type == 'religions':
        return Response(paginate_data(predefined_religions, page, page_size, search, 'religions'))
    elif filter_type == 'countries':
        return Response(paginate_data(predefined_countries, page, page_size, search, 'countries'))
    elif filter_type == 'states':
        return Response(paginate_data(sorted(predefined_states), page, page_size, search, 'states'))
    elif filter_type == 'cities':
        return Response(paginate_data(sorted(predefined_cities), page, page_size, search, 'cities'))
    elif filter_type == 'education':
        return Response(paginate_data(sorted(predefined_education), page, page_size, search, 'education'))
    
    # Return all filters with basic info (for initial load)
    return Response({
        'count': 6,
        'next': None,
        'previous': None,
        'results': {
            'departments': {
                'total_count': len(predefined_departments),
                'sample': sorted(predefined_departments)[:10]
            },
            'religions': {
                'total_count': len(predefined_religions),
                'sample': predefined_religions
            },
            'countries': {
                'total_count': len(predefined_countries),
                'sample': predefined_countries
            },
            'states': {
                'total_count': len(predefined_states),
                'sample': sorted(predefined_states)[:10]
            },
            'cities': {
                'total_count': len(predefined_cities),
                'sample': sorted(predefined_cities)[:10]
            },
            'education_options': {
                'total_count': len(predefined_education),
                'sample': sorted(predefined_education)[:10]
            }
        }
    })
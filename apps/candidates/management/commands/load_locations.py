from django.core.management.base import BaseCommand
from apps.candidates.models import FilterCategory, FilterOption
import json

class Command(BaseCommand):
    help = 'Load Indian states and cities from JSON file'

    def add_arguments(self, parser):
        parser.add_argument('json_file', type=str, help='Path to JSON file')

    def handle(self, *args, **kwargs):
        json_file = kwargs['json_file']
        
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
        
        india, _ = FilterOption.objects.get_or_create(
            category=country_category,
            slug='india',
            defaults={'name': 'India', 'is_active': True}
        )
        
        with open(json_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        states_data = data.get('states', [])
        
        for state_data in states_data:
            state_name = state_data.get('name')
            cities = state_data.get('cities', [])
            
            state, created = FilterOption.objects.get_or_create(
                category=state_category,
                slug=state_name.lower().replace(' ', '-'),
                defaults={
                    'name': state_name,
                    'parent': india,
                    'is_active': True
                }
            )
            
            if created:
                self.stdout.write(self.style.SUCCESS(f'Created state: {state_name}'))
            
            for city_name in cities:
                city, city_created = FilterOption.objects.get_or_create(
                    category=city_category,
                    slug=f"{state.slug}-{city_name.lower().replace(' ', '-')}",
                    defaults={
                        'name': city_name,
                        'parent': state,
                        'is_active': True
                    }
                )
                
                if city_created:
                    self.stdout.write(f'  - Added city: {city_name}')
        
        self.stdout.write(self.style.SUCCESS('Successfully loaded all locations!'))
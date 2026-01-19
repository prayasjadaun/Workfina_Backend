from django.core.management.base import BaseCommand
from apps.candidates.models import FilterCategory, FilterOption
import json
import os

class Command(BaseCommand):
    help = 'Load comprehensive filter data (religions, departments, languages, skills, education, states, cities) into database'

    def handle(self, *args, **kwargs):
        # Path to JSON file
        json_file = os.path.join(
            os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
            'fixtures',
            'filter_data.json'
        )

        self.stdout.write(f'Loading data from: {json_file}')

        # Load JSON data
        with open(json_file, 'r', encoding='utf-8') as f:
            data = json.load(f)

        # Create/Get filter categories
        religion_category, _ = FilterCategory.objects.get_or_create(
            slug='religion',
            defaults={'name': 'Religion', 'display_order': 1, 'is_active': True}
        )
        self.stdout.write(self.style.SUCCESS(f'Category: Religion'))

        dept_category, _ = FilterCategory.objects.get_or_create(
            slug='department',
            defaults={'name': 'Department', 'display_order': 2, 'is_active': True}
        )
        self.stdout.write(self.style.SUCCESS(f'Category: Department'))

        language_category, _ = FilterCategory.objects.get_or_create(
            slug='languages',
            defaults={'name': 'Language', 'display_order': 3, 'is_active': True}
        )
        self.stdout.write(self.style.SUCCESS(f'Category: Languages'))

        skills_category, _ = FilterCategory.objects.get_or_create(
            slug='skills',
            defaults={'name': 'Skills', 'display_order': 7, 'is_active': True}
        )
        self.stdout.write(self.style.SUCCESS(f'Category: Skills'))

        education_category, _ = FilterCategory.objects.get_or_create(
            slug='education',
            defaults={'name': 'Education', 'display_order': 6, 'is_active': True}
        )
        self.stdout.write(self.style.SUCCESS(f'Category: Education'))

        country_category, _ = FilterCategory.objects.get_or_create(
            slug='country',
            defaults={'name': 'Country', 'display_order': 3, 'is_active': True}
        )
        self.stdout.write(self.style.SUCCESS(f'Category: Country'))

        state_category, _ = FilterCategory.objects.get_or_create(
            slug='state',
            defaults={'name': 'State', 'display_order': 4, 'is_active': True}
        )
        self.stdout.write(self.style.SUCCESS(f'Category: State'))

        city_category, _ = FilterCategory.objects.get_or_create(
            slug='city',
            defaults={'name': 'City', 'display_order': 5, 'is_active': True}
        )
        self.stdout.write(self.style.SUCCESS(f'Category: City'))

        # Load Religions
        self.stdout.write('\n' + '='*50)
        self.stdout.write(self.style.WARNING('Loading Religions...'))
        religions = data.get('religions', [])
        religion_count = 0
        for idx, religion in enumerate(religions, 1):
            _, created = FilterOption.objects.get_or_create(
                category=religion_category,
                slug=religion.lower().replace(' ', '-'),
                defaults={
                    'name': religion,
                    'display_order': idx,
                    'is_active': True
                }
            )
            if created:
                religion_count += 1
                self.stdout.write(f'  + {religion}')
        self.stdout.write(self.style.SUCCESS(f'✓ Loaded {religion_count} religions'))

        # Load Departments
        self.stdout.write('\n' + '='*50)
        self.stdout.write(self.style.WARNING('Loading Departments...'))
        departments = data.get('departments', [])
        dept_count = 0
        for idx, dept in enumerate(departments, 1):
            _, created = FilterOption.objects.get_or_create(
                category=dept_category,
                slug=dept.lower().replace(' ', '-').replace('/', '-'),
                defaults={
                    'name': dept,
                    'display_order': idx,
                    'is_active': True
                }
            )
            if created:
                dept_count += 1
                self.stdout.write(f'  + {dept}')
        self.stdout.write(self.style.SUCCESS(f'✓ Loaded {dept_count} departments'))

        # Load Languages
        self.stdout.write('\n' + '='*50)
        self.stdout.write(self.style.WARNING('Loading Languages...'))
        languages = data.get('languages', [])
        lang_count = 0
        for idx, language in enumerate(languages, 1):
            _, created = FilterOption.objects.get_or_create(
                category=language_category,
                slug=language.lower().replace(' ', '-'),
                defaults={
                    'name': language,
                    'display_order': idx,
                    'is_active': True
                }
            )
            if created:
                lang_count += 1
                self.stdout.write(f'  + {language}')
        self.stdout.write(self.style.SUCCESS(f'✓ Loaded {lang_count} languages'))

        # Load Skills
        self.stdout.write('\n' + '='*50)
        self.stdout.write(self.style.WARNING('Loading Skills...'))
        skills = data.get('skills', [])
        skill_count = 0
        for idx, skill in enumerate(skills, 1):
            _, created = FilterOption.objects.get_or_create(
                category=skills_category,
                slug=skill.lower().replace(' ', '-').replace('.', '-').replace('/', '-'),
                defaults={
                    'name': skill,
                    'display_order': idx,
                    'is_active': True
                }
            )
            if created:
                skill_count += 1
                if skill_count % 20 == 0:  # Print every 20th skill to reduce output
                    self.stdout.write(f'  + Loaded {skill_count} skills...')
        self.stdout.write(self.style.SUCCESS(f'✓ Loaded {skill_count} skills'))

        # Load Education Levels
        self.stdout.write('\n' + '='*50)
        self.stdout.write(self.style.WARNING('Loading Education Levels...'))
        education_levels = data.get('education_levels', [])
        edu_count = 0
        for idx, edu in enumerate(education_levels, 1):
            _, created = FilterOption.objects.get_or_create(
                category=education_category,
                slug=edu.lower().replace(' ', '-').replace('/', '-').replace("'", ''),
                defaults={
                    'name': edu,
                    'display_order': idx,
                    'is_active': True
                }
            )
            if created:
                edu_count += 1
                self.stdout.write(f'  + {edu}')
        self.stdout.write(self.style.SUCCESS(f'✓ Loaded {edu_count} education levels'))

        # Load Country (India)
        self.stdout.write('\n' + '='*50)
        self.stdout.write(self.style.WARNING('Loading Country...'))
        india, created = FilterOption.objects.get_or_create(
            category=country_category,
            slug='india',
            defaults={'name': 'India', 'is_active': True}
        )
        if created:
            self.stdout.write(self.style.SUCCESS('  + India'))
        else:
            self.stdout.write('  India already exists')

        # Load States and Cities
        self.stdout.write('\n' + '='*50)
        self.stdout.write(self.style.WARNING('Loading States and Cities...'))
        states_data = data.get('states', [])
        state_count = 0
        city_count = 0

        for idx, state_data in enumerate(states_data, 1):
            state_name = state_data.get('name')
            cities = state_data.get('cities', [])

            state, state_created = FilterOption.objects.get_or_create(
                category=state_category,
                slug=state_name.lower().replace(' ', '-'),
                defaults={
                    'name': state_name,
                    'parent': india,
                    'display_order': idx,
                    'is_active': True
                }
            )

            if state_created:
                state_count += 1
                self.stdout.write(self.style.SUCCESS(f'\n  + {state_name}'))
            else:
                self.stdout.write(f'\n  {state_name} (exists)')

            # Load cities for this state
            new_cities = 0
            for city_idx, city_name in enumerate(cities, 1):
                _, city_created = FilterOption.objects.get_or_create(
                    category=city_category,
                    slug=f"{state.slug}-{city_name.lower().replace(' ', '-')}",
                    defaults={
                        'name': city_name,
                        'parent': state,
                        'display_order': city_idx,
                        'is_active': True
                    }
                )

                if city_created:
                    new_cities += 1
                    city_count += 1

            if new_cities > 0:
                self.stdout.write(f'    Added {new_cities} cities')

        self.stdout.write(self.style.SUCCESS(f'\n✓ Loaded {state_count} states'))
        self.stdout.write(self.style.SUCCESS(f'✓ Loaded {city_count} cities'))

        # Final summary
        self.stdout.write('\n' + '='*50)
        self.stdout.write(self.style.SUCCESS('SUMMARY:'))
        self.stdout.write(self.style.SUCCESS(f'  Religions: {religion_count}'))
        self.stdout.write(self.style.SUCCESS(f'  Departments: {dept_count}'))
        self.stdout.write(self.style.SUCCESS(f'  Languages: {lang_count}'))
        self.stdout.write(self.style.SUCCESS(f'  Skills: {skill_count}'))
        self.stdout.write(self.style.SUCCESS(f'  Education Levels: {edu_count}'))
        self.stdout.write(self.style.SUCCESS(f'  States: {state_count}'))
        self.stdout.write(self.style.SUCCESS(f'  Cities: {city_count}'))
        self.stdout.write('\n' + '='*50)
        self.stdout.write(self.style.SUCCESS('\n🎉 All filter data loaded successfully!'))

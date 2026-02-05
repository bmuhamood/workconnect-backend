# users/management/commands/generate_dummy_workers.py
import os
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'workconnect.settings')
import django
django.setup()

import random
from datetime import date, timedelta
from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone
from faker import Faker
from ...models import (
    User, WorkerProfile, JobCategory, WorkerSkill, 
    Verification, WorkerReference, UserManager
)

fake = Faker()
fake.seed_instance(4321)  # For consistent results

class Command(BaseCommand):
    help = 'Generate dummy worker data for testing'

    def add_arguments(self, parser):
        parser.add_argument(
            '--count',
            type=int,
            default=50,
            help='Number of workers to generate (default: 50)'
        )
        parser.add_argument(
            '--clear',
            action='store_true',
            help='Clear existing dummy data before generating'
        )

    def handle(self, *args, **options):
        count = options['count']
        clear_existing = options['clear']
        
        self.stdout.write(self.style.SUCCESS(
            f'Generating {count} dummy workers...'
        ))
        
        if clear_existing:
            self.clear_existing_dummy_data()
        
        try:
            with transaction.atomic():
                created_count = self.generate_workers(count)
                self.stdout.write(self.style.SUCCESS(
                    f'Successfully generated {created_count} dummy workers!'
                ))
        except Exception as e:
            self.stdout.write(self.style.ERROR(
                f'Error generating dummy workers: {str(e)}'
            ))

    def clear_existing_dummy_data(self):
        """Clear existing dummy worker data"""
        self.stdout.write('Clearing existing dummy data...')
        
        # Find and delete dummy workers
        dummy_workers = WorkerProfile.objects.filter(
            user__email__icontains='dummy_worker'
        )
        
        if dummy_workers.exists():
            count = dummy_workers.count()
            dummy_workers.delete()
            self.stdout.write(f'Deleted {count} existing dummy workers')
        else:
            self.stdout.write('No existing dummy workers found')

    def generate_workers(self, count):
        """Generate dummy workers with profiles"""
        
        # Create job categories if they don't exist
        categories = self.create_job_categories()
        
        created_count = 0
        
        for i in range(count):
            try:
                worker = self.create_worker_user(i)
                profile = self.create_worker_profile(worker, i)
                
                # Create skills
                self.create_worker_skills(profile, categories)
                
                # Create verifications
                self.create_verifications(profile)
                
                # Create references
                self.create_references(profile)
                
                created_count += 1
                
                if (i + 1) % 10 == 0:
                    self.stdout.write(f'Created {i + 1} workers...')
                    
            except Exception as e:
                self.stdout.write(self.style.WARNING(
                    f'Error creating worker {i}: {str(e)}'
                ))
                continue
        
        return created_count

    def create_job_categories(self):
        """Create or get job categories"""
        categories_data = [
            {'name': 'Housekeeper', 'icon': '🏠'},
            {'name': 'Nanny/Caregiver', 'icon': '👶'},
            {'name': 'Cook/Chef', 'icon': '👨‍🍳'},
            {'name': 'Gardener', 'icon': '🌿'},
            {'name': 'Driver', 'icon': '🚗'},
            {'name': 'Security Guard', 'icon': '🛡️'},
            {'name': 'Electrician', 'icon': '⚡'},
            {'name': 'Plumber', 'icon': '🔧'},
            {'name': 'Cleaner', 'icon': '🧹'},
            {'name': 'Babysitter', 'icon': '👧'},
        ]
        
        categories = []
        for cat_data in categories_data:
            category, created = JobCategory.objects.get_or_create(
                name=cat_data['name'],
                defaults={'icon': cat_data['icon']}
            )
            categories.append(category)
        
        return categories

    def create_worker_user(self, index):
        """Create a dummy worker user"""
        
        # Generate unique email and phone
        base_email = f'dummy_worker_{index}_{fake.random_int(1000, 9999)}@example.com'
        phone = f'+2567{random.randint(10000000, 99999999)}'
        
        # Check if phone already exists
        while User.objects.filter(phone=phone).exists():
            phone = f'+2567{random.randint(10000000, 99999999)}'
        
        # Create user with raw password
        user = User(
            email=base_email,
            phone=phone,
            first_name=fake.first_name(),
            last_name=fake.last_name(),
            role='worker',
            status='active',
            email_verified=True,
            phone_verified=True,
            is_verified=True,
            is_active=True
        )
        
        # Use set_password to hash the password
        user.set_password('Test@1234')  # Standard password for all dummy users
        
        user.save()
        return user

    def create_worker_profile(self, user, index):
        """Create worker profile"""
        
        cities = ['Kampala', 'Entebbe', 'Jinja', 'Mbarara', 'Gulu', 'Lira', 'Mbale', 'Soroti']
        districts = ['Kampala', 'Wakiso', 'Mukono', 'Jinja', 'Mbarara', 'Gulu', 'Lira']
        
        # Generate date of birth (18-60 years old)
        today = date.today()
        start_date = today - timedelta(days=365 * 60)
        end_date = today - timedelta(days=365 * 18)
        dob = fake.date_between(start_date=start_date, end_date=end_date)
        
        professions = [
            'Housekeeper', 'Nanny', 'Cook', 'Gardener', 'Driver', 
            'Security Guard', 'Electrician', 'Plumber', 'Cleaner', 'Babysitter'
        ]
        
        skills_list = [
            'Cooking', 'Cleaning', 'Child Care', 'Gardening', 'Driving',
            'Electrical Work', 'Plumbing', 'First Aid', 'Communication', 'Organization'
        ]
        
        profile = WorkerProfile.objects.create(
            user=user,
            first_name=user.first_name,
            last_name=user.last_name,
            date_of_birth=dob,
            gender=random.choice(['male', 'female']),
            national_id=f'CM{random.randint(1000000, 9999999)}',
            bio=fake.paragraph(nb_sentences=3),
            city=random.choice(cities),
            district=random.choice(districts),
            experience_years=random.randint(0, 20),
            education_level=random.choice(['Primary', 'Secondary', 'Diploma', 'Degree']),
            languages=random.sample(['English', 'Luganda', 'Swahili', 'Runyankole'], random.randint(1, 3)),
            profession=random.choice(professions),
            additional_skills=', '.join(random.sample(skills_list, random.randint(3, 6))),
            hourly_rate=random.uniform(5.0, 25.0),
            availability=random.choice(['available', 'full_time', 'part_time', 'flexible']),
            expected_salary_min=random.randint(200000, 500000),
            expected_salary_max=random.randint(500000, 1200000),
            verification_status=random.choice(['verified', 'verified', 'verified', 'pending']),  # 75% verified
            trust_score=random.randint(70, 100),
            rating_average=round(random.uniform(3.5, 5.0), 2),
            total_reviews=random.randint(0, 50),
            total_placements=random.randint(0, 10),
            subscription_tier=random.choice(['basic', 'premium', 'pro']),
            subscription_expires_at=timezone.now() + timedelta(days=random.randint(30, 365)),
            completion_percentage=random.randint(60, 100)
        )
        
        # Add location coordinates
        if profile.city == 'Kampala':
            profile.location_lat = round(random.uniform(0.3136, 0.3456), 6)
            profile.location_lng = round(random.uniform(32.5250, 32.6550), 6)
        else:
            profile.location_lat = round(random.uniform(-1.0, 3.0), 6)
            profile.location_lng = round(random.uniform(29.0, 35.0), 6)
        
        profile.save()
        return profile

    def create_worker_skills(self, profile, categories):
        """Create worker skills"""
        
        skills_data = [
            # Housekeeping skills
            {'name': 'General Cleaning', 'proficiency': 'advanced'},
            {'name': 'Laundry', 'proficiency': 'intermediate'},
            {'name': 'Ironing', 'proficiency': 'intermediate'},
            
            # Child care skills
            {'name': 'Child Supervision', 'proficiency': 'advanced'},
            {'name': 'Homework Assistance', 'proficiency': 'intermediate'},
            {'name': 'First Aid', 'proficiency': 'beginner'},
            
            # Cooking skills
            {'name': 'Meal Preparation', 'proficiency': 'advanced'},
            {'name': 'Baking', 'proficiency': 'intermediate'},
            {'name': 'Menu Planning', 'proficiency': 'intermediate'},
            
            # Technical skills
            {'name': 'Electrical Repair', 'proficiency': 'advanced'},
            {'name': 'Plumbing', 'proficiency': 'intermediate'},
            {'name': 'Gardening', 'proficiency': 'advanced'},
            
            # Other skills
            {'name': 'Driving', 'proficiency': 'expert'},
            {'name': 'Security', 'proficiency': 'advanced'},
            {'name': 'Communication', 'proficiency': 'intermediate'},
        ]
        
        # Select 3-5 random skills for this worker
        selected_skills = random.sample(skills_data, random.randint(3, 5))
        
        for skill_data in selected_skills:
            WorkerSkill.objects.create(
                worker=profile,
                category=random.choice(categories),
                skill_name=skill_data['name'],
                proficiency_level=skill_data['proficiency'],
                years_of_experience=random.randint(1, profile.experience_years),
                is_primary=random.choice([True, False])
            )

    def create_verifications(self, profile):
        """Create verification records"""
        
        verification_types = ['identity', 'background_check', 'reference', 'skills_certification']
        
        for v_type in random.sample(verification_types, random.randint(1, 3)):
            status_choices = ['approved', 'approved', 'pending']  # 2/3 chance of approved
            status = random.choice(status_choices)
            
            Verification.objects.create(
                worker=profile,
                verification_type=v_type,
                status=status,
                verification_notes=fake.sentence() if status == 'approved' else None,
                verified_at=timezone.now() - timedelta(days=random.randint(1, 90)) if status == 'approved' else None,
                expires_at=timezone.now() + timedelta(days=random.randint(30, 365)) if status == 'approved' else None
            )

    def create_references(self, profile):
        """Create worker references"""
        
        if random.random() > 0.3:  # 70% chance of having references
            num_references = random.randint(1, 3)
            
            for i in range(num_references):
                company = fake.company() if random.random() > 0.5 else None
                
                WorkerReference.objects.create(
                    worker=profile,
                    referee_name=fake.name(),
                    referee_phone=f'+2567{random.randint(10000000, 99999999)}',
                    referee_email=fake.email() if random.random() > 0.3 else None,
                    relationship=random.choice(['Former Employer', 'Family Friend', 'Relative', 'Community Leader']),
                    company_name=company,
                    is_verified=random.choice([True, False]),
                    verified_at=timezone.now() - timedelta(days=random.randint(1, 365)) if random.random() > 0.5 else None,
                    notes=fake.sentence()
                )
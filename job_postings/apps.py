# job_postings/apps.py
from django.apps import AppConfig


class JobPostingsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'job_postings'
    
    def ready(self):
        import job_postings.signals  # This now exists
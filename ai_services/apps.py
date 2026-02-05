# ai_services/apps.py
from django.apps import AppConfig

class AiServicesConfig(AppConfig):
    name = 'ai_services'
    
    def ready(self):
        import ai_services.signals  # This should exist
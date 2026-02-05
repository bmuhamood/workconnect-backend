"""
WSGI config for workconnect project.
"""

import os
from django.core.wsgi import get_wsgi_application

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'workconnect.settings.production')

application = get_wsgi_application()

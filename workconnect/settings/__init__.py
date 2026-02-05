import os
from .base import *

# Determine environment
ENVIRONMENT = os.getenv('DJANGO_ENV', 'development')

if ENVIRONMENT == 'production':
    from .production import *
elif ENVIRONMENT == 'staging':
    from .staging import *
else:
    from .development import *

# Local settings override
try:
    from .local import *
except ImportError:
    pass
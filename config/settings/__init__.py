"""
Settings package initialization for Aurevia Motors.
Selects settings profile based on DJANGO_ENV environment variable:
- 'development' (default)
- 'production'
"""

import os

env = os.environ.get('DJANGO_ENV', 'development').lower()

if env == 'production':
    from .production import *
else:
    from .development import *

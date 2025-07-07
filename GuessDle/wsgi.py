import os
from django.core.wsgi import get_wsgi_application

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'GuessDle.settings')

application = get_wsgi_application()

# --------- Añade estas dos líneas:
from whitenoise import WhiteNoise
application = WhiteNoise(application, root='/app/staticfiles')
# (Ajusta el path si tu STATIC_ROOT es diferente)

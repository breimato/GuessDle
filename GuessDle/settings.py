from pathlib import Path
from dotenv import load_dotenv
import os

# Cargar variables desde el archivo .env
BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / '.env')

# Seguridad
SECRET_KEY = os.getenv("SECRET_KEY")
DEBUG = os.getenv("DEBUG", "False") == "True"
ALLOWED_HOSTS = os.getenv("ALLOWED_HOSTS", "").split(",")
CSRF_TRUSTED_ORIGINS = os.getenv("CSRF_TRUSTED_ORIGINS", "").split(",")

CSRF_COOKIE_SECURE = not DEBUG
SESSION_COOKIE_SECURE = not DEBUG

ROOT_URLCONF = 'GuessDle.urls'

# Configuración del modelo ScoringRule
SCORING_FALLBACK = {"decrement": 10, "floor": 0}

# Bote semanal del rosco Pasapalabra (ELO aportado cada semana)
ROSCO_WEEKLY_POT_CONTRIBUTION = float(os.getenv("ROSCO_WEEKLY_POT_CONTRIBUTION", "1000"))


# Redirecciones
LOGIN_REDIRECT_URL = 'dashboard'
LOGIN_URL = '/accounts/login/'
LOGOUT_REDIRECT_URL = '/accounts/login/'

# Idioma y zona horaria
LANGUAGE_CODE = os.getenv("LANGUAGE_CODE", "es-es")
TIME_ZONE = os.getenv("TIME_ZONE", "UTC")

USE_I18N = True
USE_TZ = True

# Archivos estáticos y media
STATIC_URL = '/static/'
STATICFILES_DIRS = [BASE_DIR / 'static']
STATIC_ROOT = os.path.join(BASE_DIR, 'staticfiles')
MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

# Base de datos SQLite (esto podrías adaptarlo también al .env si algún día usás MySQL/PostgreSQL)
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
    }
}

# Aplicaciones instaladas
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'apps.accounts',
    'apps.games',
    'tailwind',
    'colorfield',
]

# Middleware
MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

# Templates
TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'GuessDle.wsgi.application'

# Validadores de contraseñas
AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

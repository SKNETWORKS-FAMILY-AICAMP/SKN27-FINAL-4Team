from pathlib import Path
import os
from dotenv import dotenv_values, load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
PROJECT_ROOT = BASE_DIR.parent.parent

load_dotenv(PROJECT_ROOT / '.env')
load_dotenv(BASE_DIR / '.env')

backend_env = dotenv_values(BASE_DIR / '.env')
for key in ('KAKAO_CLIENT_SECRET', 'NAVER_CLIENT_SECRET', 'GOOGLE_CLIENT_SECRET'):
    if not os.environ.get(key) and backend_env.get(key):
        os.environ[key] = backend_env[key]

SECRET_KEY = os.environ.get('DJANGO_SECRET_KEY', 'django-insecure-af7tf^s)+euab4fl@0w!@fi%rgw_gi7dxh)cm8236d^9_h5@f9')

DEBUG = os.environ.get('DEBUG', 'True') == 'True'

ALLOWED_HOSTS = ['*']

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    # Third-party
    'rest_framework',
    'corsheaders',
    # Local apps
    'user',
    'chat',
    'wellness',
    'character',
    'calendar_api',
    'game.tarot_api',
    'mindreport',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'corsheaders.middleware.CorsMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'config.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
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

WSGI_APPLICATION = 'config.wsgi.application'

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': os.environ.get('PG_DB', 'wellness_db'),
        'USER': os.environ.get('PG_USER', 'postgres'),
        'PASSWORD': os.environ.get('PG_PASSWORD', 'password'),
        'HOST': os.environ.get('PG_HOST', 'localhost'),
        'PORT': os.environ.get('PG_PORT', '5432'),
    }
}

AUTH_USER_MODEL = 'user.User'

REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'rest_framework.authentication.SessionAuthentication',
    ],
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.AllowAny',
    ],
}

CORS_ALLOWED_ORIGINS = [
    'http://localhost:5173',  # Vue dev server
    'http://127.0.0.1:5173',
]

FRONTEND_BASE_URL = os.environ.get('FRONTEND_BASE_URL', 'http://localhost:5173').rstrip('/')

SOCIAL_LOGIN = {
    'providers': {
        'kakao': {
            'client_id': os.environ.get('KAKAO_CLIENT_ID', ''),
            'client_secret': os.environ.get('KAKAO_CLIENT_SECRET', ''),
            'redirect_uri': os.environ.get('KAKAO_REDIRECT_URI', f'{FRONTEND_BASE_URL}/login/callback/kakao'),
            'authorization_url': 'https://kauth.kakao.com/oauth/authorize',
            'token_url': 'https://kauth.kakao.com/oauth/token',
            'profile_url': 'https://kapi.kakao.com/v2/user/me',
            'scope': os.environ.get('KAKAO_SCOPE', 'profile_nickname account_email'),
        },
        'naver': {
            'client_id': os.environ.get('NAVER_CLIENT_ID', ''),
            'client_secret': os.environ.get('NAVER_CLIENT_SECRET', ''),
            'redirect_uri': os.environ.get('NAVER_REDIRECT_URI', f'{FRONTEND_BASE_URL}/login/callback/naver'),
            'authorization_url': 'https://nid.naver.com/oauth2.0/authorize',
            'token_url': 'https://nid.naver.com/oauth2.0/token',
            'profile_url': 'https://openapi.naver.com/v1/nid/me',
            'scope': os.environ.get('NAVER_SCOPE', ''),
            'authorization_params': {
                'locale': os.environ.get('NAVER_LOCALE', 'ko_KR'),
            },
        },
        'google': {
            'client_id': os.environ.get('GOOGLE_CLIENT_ID', ''),
            'client_secret': os.environ.get('GOOGLE_CLIENT_SECRET', ''),
            'redirect_uri': os.environ.get('GOOGLE_REDIRECT_URI', f'{FRONTEND_BASE_URL}/login/callback/google'),
            'authorization_url': 'https://accounts.google.com/o/oauth2/v2/auth',
            'token_url': 'https://oauth2.googleapis.com/token',
            'profile_url': 'https://www.googleapis.com/oauth2/v3/userinfo',
            'scope': os.environ.get('GOOGLE_SCOPE', 'openid email profile'),
        },
    },
}

AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

LANGUAGE_CODE = 'ko-kr'
TIME_ZONE = 'Asia/Seoul'
USE_I18N = True
USE_TZ = True

STATIC_URL = 'static/'

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

OPENAI_API_KEY = os.environ.get('OPENAI_API_KEY', '')
NEO4J_URI = os.environ.get('NEO4J_URI', 'bolt://localhost:7687')
NEO4J_USER = os.environ.get('NEO4J_USER', 'neo4j')
NEO4J_PASSWORD = os.environ.get('NEO4J_PASSWORD', 'password')

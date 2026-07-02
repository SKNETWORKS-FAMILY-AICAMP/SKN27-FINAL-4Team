from pathlib import Path
import os
import sys
from dotenv import load_dotenv

# 프로젝트 루트 기준으로 .env 로드 (config/ → backend/ → app/ → 루트)
_PROJECT_ROOT = Path(__file__).resolve().parents[3]
load_dotenv(_PROJECT_ROOT / '.env')

# ai/, etl/ 등 루트 패키지를 import 가능하게
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

BASE_DIR = Path(__file__).resolve().parent.parent

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

# ── TTS mp3 등 미디어 파일 (API 명세서 v6.0 §3-2) ──
MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

OPENAI_API_KEY = os.environ.get('OPENAI_API_KEY', '')
TAVILY_API_KEY = os.environ.get('TAVILY_API_KEY', '')

# ── ElevenLabs TTS (TTS_음성설정 v2.0) ──
ELEVENLABS_API_KEY = os.environ.get('ELEVENLABS_API_KEY', '')
ELEVENLABS_MODEL_ID = os.environ.get('ELEVENLABS_MODEL_ID', 'eleven_v3')   # 감정 연기(오디오 태그) 지원
# voice_id 4종은 Voice Library에서 팀이 선정 후 .env에 설정 (TODO)
ELEVENLABS_VOICES = {
    'pori':  os.environ.get('VOICE_ID_PORI', ''),
    'kkami': os.environ.get('VOICE_ID_KKAMI', ''),
    'toto':  os.environ.get('VOICE_ID_TOTO', ''),
    'yeoul': os.environ.get('VOICE_ID_YEOUL', ''),
}
OPENWEATHERMAP_API_KEY = os.environ.get('OPENWEATHERMAP_API_KEY', '')

# ── 캐시 설정 ─────────────────────────────────────────────
# v6.0: Redis는 2차 확장(ERD v6.0 §3-2) — REDIS_URL이 명시된 경우에만 사용,
# 기본은 인메모리(LocMem). 시크릿 모드 대화 캐시는 chat/secret_cache.py가 담당.
import sys
_REDIS_URL = os.environ.get('REDIS_URL', '')
if _REDIS_URL and 'test' not in sys.argv:
    CACHES = {
        "default": {
            "BACKEND": "django_redis.cache.RedisCache",
            "LOCATION": _REDIS_URL,
            "OPTIONS": {
                "CLIENT_CLASS": "django_redis.client.DefaultClient",
                "SOCKET_CONNECT_TIMEOUT": 5,
                "SOCKET_TIMEOUT": 5,
            }
        }
    }
else:
    CACHES = {
        "default": {
            "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
            "LOCATION": "wellness-cache",
        }
    }

# ── 테스트는 로컬 sqlite로 실행 (Postgres 불필요: python manage.py test chat) ──
if 'test' in sys.argv:
    DATABASES = {'default': {'ENGINE': 'django.db.backends.sqlite3', 'NAME': ':memory:'}}



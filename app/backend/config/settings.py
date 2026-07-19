from pathlib import Path
import os
import sys
from dotenv import dotenv_values, load_dotenv

# 프로젝트 루트 기준으로 .env 로드 (config/ → backend/ → app/ → 루트)
_PROJECT_ROOT = Path(__file__).resolve().parents[3]
load_dotenv(_PROJECT_ROOT / '.env')

# ai/, etl/ 등 루트 패키지를 import 가능하게
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

BASE_DIR = Path(__file__).resolve().parent.parent
PROJECT_ROOT = BASE_DIR.parent.parent

# app/backend/.env 가 있으면 추가 로드 (OAuth 시크릿 등 로컬 전용 키)
load_dotenv(BASE_DIR / ".env", override=True)

backend_env = dotenv_values(BASE_DIR / '.env')
for key in ('KAKAO_CLIENT_SECRET', 'NAVER_CLIENT_SECRET', 'GOOGLE_CLIENT_SECRET'):
    if not os.environ.get(key) and backend_env.get(key):
        os.environ[key] = backend_env[key]

#  실제 키는 .env(DJANGO_SECRET_KEY)에서 읽는다. 아래 폴백은 개발 임시값 —
#  운영/공유 환경에선 반드시 .env로 주입(폴백이 뜨면 안 됨).
SECRET_KEY = (
    os.environ.get('DJANGO_SECRET_KEY')
    or os.environ.get('SECRET_KEY')
    or 'django-insecure-dev-only-set-DJANGO_SECRET_KEY-in-env'
)

#  보안 기본값은 안전(운영)에 맞춤. 개발은 .env에 DEBUG=True 를 둔다.
DEBUG = os.environ.get('DEBUG', 'False') == 'True'

#  개발은 .env에 ALLOWED_HOSTS=* , 운영은 실제 도메인만.
ALLOWED_HOSTS = [
    h.strip() for h in os.environ.get('ALLOWED_HOSTS', 'localhost,127.0.0.1').split(',')
    if h.strip()
]

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
    'mbti',
    'myprofile',
    'taste',
    'character',
    'calendar_api',
    'game.tarot_api',
    'mindreport',
    'mybook',
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
        'PASSWORD': os.environ.get('PG_PASSWORD', ''),   # 약한 기본값 제거 — .env에서 주입
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
]
CORS_ALLOW_CREDENTIALS = True

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

# ── TTS mp3 등 미디어 파일 (API 명세서 v6.0 §3-2) ──
MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

OPENAI_API_KEY = os.environ.get('OPENAI_API_KEY', '')
# (TAVILY_API_KEY는 장소 추천 기능 폐기로 제거 — 2026-07-05)

# ── TTS 공급자 (openai=gpt-audio | off=생성 차단·비용 절약) ──
# ElevenLabs(키 만료·크레딧 소진)·Typecast(월 5분 제한)는 2026-07-19 은퇴 — 설정 삭제.
# OPENAI_API_KEY는 LLM이 이미 쓰는 키라 전 팀원 추가 설정 없이 동작.
TTS_PROVIDER = os.environ.get('TTS_PROVIDER', 'openai').strip().lower()

# ── OpenAI gpt-audio (대화형 오디오 모델 — 2026-07-19 실청취로 전용 TTS 대신 확정) ──
OPENAI_AUDIO_MODEL = os.environ.get('OPENAI_AUDIO_MODEL', 'gpt-audio')   # 절약판: gpt-audio-mini
# gpt-audio 지원 목소리: alloy·ash·ballad·coral·echo·sage·shimmer·verse·marin·cedar
# (nova·onyx·fable은 전용 TTS 전용 — 이 모델에선 불가) 아래는 1차 배정, 오디션 후 .env로 교체
OPENAI_TTS_VOICES = {   # 여성 4종 확정 (2026-07-19) — 바꾸려면 .env 한 줄
    'pori':  os.environ.get('OPENAI_TTS_VOICE_PORI', 'coral'),    # 레서판다·밝음·응원
    'kkami': os.environ.get('OPENAI_TTS_VOICE_KKAMI', 'sage'),    # 고양이·차분·묵직
    'toto':  os.environ.get('OPENAI_TTS_VOICE_TOTO', 'marin'),    # 수달·장난·활달
    'yeoul': os.environ.get('OPENAI_TTS_VOICE_YEOUL', 'shimmer'), # 뱁새·포근
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



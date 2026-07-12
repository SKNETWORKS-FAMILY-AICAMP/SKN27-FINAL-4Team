from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/user/', include('user.urls')),
    path('api/mypage/', include('wellness.urls')),
    path('api/', include('chat.urls')),            # 챗봇: /api/session/, /api/chat/, /api/tts/, /api/mbti/
    path('api/myprofile/', include('myprofile.urls')),
    path('api/myweather/', include('myweather.urls')),
    path('api/mywardrobe/', include('mywardrobe.urls')),
    path('api/mbti/', include('mbti.urls')),
    path('api/characters/', include('character.urls')),
    path('api/calendar/', include('calendar_api.urls')),
    path('api/tarot/', include('game.tarot_api.urls')),
    path('api/report/', include('mindreport.urls')),
]

# TTS mp3 등 미디어 파일 서빙 (개발용 — 운영은 웹서버가 담당)
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

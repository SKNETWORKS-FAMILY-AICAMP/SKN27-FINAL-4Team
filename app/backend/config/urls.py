from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/user/', include('user.urls')),      # 로그인/온보딩
    path('api/mypage/', include('wellness.urls')), # 마이페이지
    path('api/', include('chat.urls')),            # 챗봇 (전체 목록: chat/views.py 참조)
]

# TTS mp3 등 미디어 파일 서빙 (개발용 — 운영은 웹서버가 담당)
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

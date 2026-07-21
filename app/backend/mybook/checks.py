import os

from django.core.checks import Warning, register

from .constants import KAKAO_API_KEY_ENV_VARS


@register()
def kakao_book_credentials_check(app_configs, **kwargs):
    service_key = next(
        (
            os.environ.get(name, '').strip()
            for name in KAKAO_API_KEY_ENV_VARS
            if os.environ.get(name, '').strip()
        ),
        '',
    )
    if service_key:
        return []
    return [
        Warning(
            'Kakao Daum 책 검색 API 인증키가 설정되지 않았습니다.',
            hint=(
                'Kakao Developers 앱의 REST API 키를 '
                'KAKAO_REST_API_KEY 또는 KAKAO_CLIENT_ID로 설정하세요.'
            ),
            id='mybook.W001',
        )
    ]

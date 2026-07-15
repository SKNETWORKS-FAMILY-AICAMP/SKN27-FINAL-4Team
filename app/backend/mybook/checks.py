import os

from django.core.checks import Warning, register


@register()
def nlk_book_credentials_check(app_configs, **kwargs):
    service_key = (
        os.environ.get('NLK_BIBLIO_SERVICE_KEY')
        or os.environ.get('DATA_GO_KR_SERVICE_KEY')
        or ''
    ).strip()
    if service_key:
        return []
    return [
        Warning(
            '국립중앙도서관 국가서지 LOD API 인증키가 설정되지 않았습니다.',
            hint=(
                '공공데이터포털의 국립중앙도서관 서지 정보 제공 서비스를 활용 신청한 뒤 '
                'NLK_BIBLIO_SERVICE_KEY 또는 DATA_GO_KR_SERVICE_KEY를 설정하세요.'
            ),
            id='mybook.W001',
        )
    ]

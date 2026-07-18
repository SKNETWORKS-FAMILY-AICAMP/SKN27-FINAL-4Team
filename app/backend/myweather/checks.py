import os
from urllib.parse import urlparse

from django.core.checks import Warning, register


@register()
def tavily_commercial_plan_check(app_configs, **kwargs):
    warnings = []
    tavily_key = os.environ.get('TAVILY_API_KEY', '').strip()
    if tavily_key:
        confirmed = os.environ.get('TAVILY_COMMERCIAL_USE_CONFIRMED', 'false').strip().lower()
        if confirmed not in {'1', 'true', 'yes', 'on'}:
            warnings.append(Warning(
            'Tavily API 키는 있으나 상용 이용 플랜 확인 표시가 없습니다.',
            hint=(
                'Tavily 계약/구독과 최종 이용자 약관·개인정보처리방침 반영을 확인한 뒤 '
                'TAVILY_PLAN_NAME과 TAVILY_COMMERCIAL_USE_CONFIRMED=true를 설정하세요.'
            ),
            id='myweather.W001',
            ))
        if os.environ.get('TAVILY_SEARCH_DEPTH', 'basic').strip().lower() == 'advanced':
            warnings.append(Warning(
                'Tavily advanced 검색은 호출당 2크레딧을 사용합니다.',
                hint='일반 날씨 근거 검색은 TAVILY_SEARCH_DEPTH=basic을 권장합니다.',
                id='myweather.W002',
            ))

    if not os.environ.get('OPENAI_API_KEY', '').strip():
        warnings.append(Warning(
            'OPENAI_API_KEY가 없어 날씨 개인화 해설과 추천을 제공하지 않습니다.',
            hint='개인화 생성문을 사용하려면 배포 환경의 OPENAI_API_KEY와 결제·한도를 확인하세요.',
            id='myweather.W003',
        ))

    kma_hub_key = (
        os.environ.get('KMA_API_HUB_AUTH_KEY', '')
        or os.environ.get('KMA_APIHUB_AUTH_KEY', '')
    ).strip()
    if not kma_hub_key:
        warnings.append(Warning(
            '기상청 API허브 인증키가 없어 실황·초단기·주간예보·특보 기능을 사용할 수 없습니다.',
            hint=(
                'API허브 가입 후 동네예보·중기예보·특보현황의 필요한 세부 API를 활용 신청하고 '
                'KMA_API_HUB_AUTH_KEY를 설정하세요.'
            ),
            id='myweather.W004',
        ))
    elif os.environ.get('KMA_API_HUB_SERVICES_CONFIRMED', 'false').strip().lower() not in {
        '1', 'true', 'yes', 'on'
    }:
        warnings.append(Warning(
            'API허브 인증키는 있으나 동네예보·중기예보·특보현황 활용신청 확인 표시가 없습니다.',
            hint=(
                '두 API가 정상 호출되는지 확인한 뒤 '
                'KMA_API_HUB_SERVICES_CONFIRMED=true를 설정하세요.'
            ),
            id='myweather.W005',
        ))

    if kma_hub_key and os.environ.get(
        'KMA_API_HUB_WEEKLY_SERVICES_CONFIRMED', 'false'
    ).strip().lower() not in {'1', 'true', 'yes', 'on'}:
        warnings.append(Warning(
            '검색 기반 주간예보에 필요한 중기기온·중기육상예보 승인 확인 표시가 없습니다.',
            hint=(
                'getVilageFcst, getMidTa, getMidLandFcst 실호출이 모두 성공한 뒤 '
                'KMA_API_HUB_WEEKLY_SERVICES_CONFIRMED=true를 설정하세요.'
            ),
            id='myweather.W008',
        ))

    life_index_key = (
        os.environ.get('KMA_LIFE_INDEX_SERVICE_KEY', '')
        or os.environ.get('KMA_API_KEY', '')
    ).strip()
    if not life_index_key:
        warnings.append(Warning(
            '기상청 생활기상지수 V5 키가 없어 자외선지수를 제공하지 않습니다.',
            hint=(
                '공공데이터포털에서 기상청_생활기상지수 조회서비스(3.0)를 활용 신청한 뒤 '
                'KMA_LIFE_INDEX_SERVICE_KEY를 설정하세요. 기존 KMA_API_KEY에 해당 서비스의 '
                '활용신청을 추가한 경우 그 키도 재사용할 수 있습니다.'
            ),
            id='myweather.W009',
        ))
    elif os.environ.get(
        'KMA_LIFE_INDEX_SERVICE_CONFIRMED', 'false'
    ).strip().lower() not in {'1', 'true', 'yes', 'on'}:
        warnings.append(Warning(
            '생활기상지수 키는 있으나 자외선지수 실호출 확인 표시가 없습니다.',
            hint='getUVIdxV5 호출 성공 후 KMA_LIFE_INDEX_SERVICE_CONFIRMED=true를 설정하세요.',
            id='myweather.W010',
        ))

    if tavily_key:
        configured_domains = {
            domain.strip().lower()
            for domain in os.environ.get(
                'TAVILY_INCLUDE_DOMAINS',
                'weather.naver.com,weatheri.co.kr,kweather.co.kr',
            ).split(',')
            if domain.strip()
        }
        required_domains = {'weather.naver.com', 'weatheri.co.kr', 'kweather.co.kr'}
        missing_domains = sorted(required_domains - configured_domains)
        if missing_domains:
            warnings.append(Warning(
                'Tavily 민간 날씨 검색 도메인이 일부 빠져 있습니다.',
                hint=f"TAVILY_INCLUDE_DOMAINS에 {', '.join(missing_domains)}를 추가하세요.",
                id='myweather.W006',
            ))

    hub_endpoint_variables = (
        'KMA_API_HUB_VILAGE_ENDPOINT',
        'KMA_API_HUB_MID_ENDPOINT',
        'KMA_API_HUB_WARNING_ENDPOINT',
    )
    non_hub_endpoints = []
    for variable in hub_endpoint_variables:
        configured_endpoint = os.environ.get(variable, '').strip()
        if configured_endpoint and urlparse(configured_endpoint).hostname != 'apihub.kma.go.kr':
            non_hub_endpoints.append(variable)
    if non_hub_endpoints:
        warnings.append(Warning(
            '기상정보 API 주소가 기상청 API허브 외부 호스트로 설정되어 있습니다.',
            hint=(
                f"{', '.join(non_hub_endpoints)}를 apihub.kma.go.kr 공식 API 주소로 설정하세요. "
                '내부 프록시를 의도한 경우에도 원천 데이터가 기상청 API허브인지 별도로 확인하세요.'
            ),
            id='myweather.W007',
        ))

    life_index_endpoint = os.environ.get('KMA_UV_INDEX_ENDPOINT', '').strip()
    if life_index_endpoint and urlparse(life_index_endpoint).hostname != 'apis.data.go.kr':
        warnings.append(Warning(
            '자외선지수 API 주소가 공공데이터포털 공식 호스트가 아닙니다.',
            hint='KMA_UV_INDEX_ENDPOINT를 apis.data.go.kr 공식 주소로 설정하세요.',
            id='myweather.W011',
        ))

    return warnings

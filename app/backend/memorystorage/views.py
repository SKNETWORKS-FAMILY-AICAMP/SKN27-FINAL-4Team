# -*- coding: utf-8 -*-
"""기억보관함 HTTP 엔드포인트.

그래프 조회·조립·삭제 정책은 ``services``에 두고 이 모듈은 인증과 HTTP 응답
변환만 담당한다.
"""

from rest_framework import status
from rest_framework.decorators import (
    api_view,
    authentication_classes,
    permission_classes,
)
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from user.views import CsrfExemptSessionAuthentication

from .constants import (
    DRIVER_UNAVAILABLE_MESSAGE,
    MEMORY_DELETE_ERROR_MESSAGE,
    MEMORY_LOAD_ERROR_MESSAGE,
    MEMORY_NOT_FOUND_MESSAGE,
)
from .driver import get_memory_driver
from .services import (
    _cause_lead,
    _memory_content,
    _memory_introduction,
    _serialise_units,
    delete_memory_unit,
    find_memory_origin,
    load_memory_units,
)

# 기존 내부 import를 사용하는 코드와 테스트를 위한 호환 별칭.
_load_memory_units = load_memory_units
_find_memory_origin = find_memory_origin
_delete_memory_unit = delete_memory_unit


@api_view(['GET'])
@authentication_classes([CsrfExemptSessionAuthentication])
@permission_classes([IsAuthenticated])
def memory_vault_list(request):
    """User 사실을 원문 작성 시각별 연결 맥락으로 묶어서 반환한다."""
    driver = get_memory_driver()
    if driver is None:
        return Response(
            {
                'memories': [],
                'detail': DRIVER_UNAVAILABLE_MESSAGE,
            },
            status=status.HTTP_503_SERVICE_UNAVAILABLE,
        )

    try:
        with driver.session() as session:
            memories = load_memory_units(session, request.user.id)
        return Response({'memories': memories})
    except Exception as exc:
        return Response(
            {
                'memories': [],
                'notice': f'{MEMORY_LOAD_ERROR_MESSAGE}: {exc}',
            },
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


@api_view(['DELETE'])
@authentication_classes([CsrfExemptSessionAuthentication])
@permission_classes([IsAuthenticated])
def memory_vault_delete(request, memory_id):
    """원문 작성 시점별 User 기억 단위와 그 전용 맥락을 삭제한다."""
    driver = get_memory_driver()
    if driver is None:
        return Response(
            {'detail': DRIVER_UNAVAILABLE_MESSAGE},
            status=status.HTTP_503_SERVICE_UNAVAILABLE,
        )

    try:
        with driver.session() as session:
            deleted = session.execute_write(
                lambda tx: delete_memory_unit(
                    tx, request.user.id, memory_id))
        if deleted is None:
            return Response(
                {'detail': MEMORY_NOT_FOUND_MESSAGE},
                status=status.HTTP_404_NOT_FOUND,
            )
        return Response({'success': True, 'deleted': deleted})
    except Exception as exc:
        return Response(
            {'detail': f'{MEMORY_DELETE_ERROR_MESSAGE}: {exc}'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )

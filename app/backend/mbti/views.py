from __future__ import annotations

from json import JSONDecodeError

from django.db import DatabaseError
from rest_framework.decorators import api_view
from rest_framework.response import Response

from mbti.examples.monthly_demo_payload import (
    build_frontend_payload_from_pipeline_result,
    read_demo_payload,
    run_local_monthly_demo_pipeline,
)
from mbti.services.dashboard_payload import load_latest_frontend_payload


def _has_frontend_mbti_data(payload):
    mbti_data = payload.get('mbti_data') if isinstance(payload, dict) else None
    if not isinstance(mbti_data, dict):
        return False

    current = mbti_data.get('current') or {}
    previous = mbti_data.get('previous') or {}
    onboarding = mbti_data.get('onboarding') or {}

    return all(
        [
            current.get('type'),
            previous.get('type'),
            onboarding.get('type'),
            current.get('axes'),
            mbti_data.get('report'),
        ]
    )


@api_view(['GET'])
def monthly_demo(request):
    user_id = int(request.query_params.get('user_id') or 1)
    period_key = request.query_params.get('period_key') or None

    try:
        db_payload = load_latest_frontend_payload(
            user_id=user_id,
            period_key=period_key,
        )
    except DatabaseError:
        db_payload = None

    if db_payload is not None and _has_frontend_mbti_data(db_payload):
        return Response(db_payload)

    try:
        payload = read_demo_payload()
    except (OSError, JSONDecodeError, ValueError):
        payload = None

    if payload is not None and _has_frontend_mbti_data(payload):
        return Response(payload)

    result = run_local_monthly_demo_pipeline()
    return Response(
        build_frontend_payload_from_pipeline_result(
            result,
            source='django_live_demo_fallback',
        )
    )

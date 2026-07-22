from __future__ import annotations

import logging

from django.db import DatabaseError
from rest_framework.decorators import api_view, authentication_classes, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from mbti.constants import EMPTY_AXIS_COUNTS, MBTI_AXES
from mbti.services.dashboard_payload import load_latest_frontend_payload
from mbti.services.job_service import enqueue_user_month_job, latest_job_payload
from mbti.services.mbti_utils import is_valid_mbti_type
from mbti.services.onboarding_service import save_onboarding_mbti
from mbti.services.qna_service import (
    current_period_key,
    generate_question,
    load_axis_counts,
    reset_current_month,
    save_answer,
)
from user.views import CsrfExemptSessionAuthentication


logger = logging.getLogger(__name__)


@api_view(["GET"])
@authentication_classes([CsrfExemptSessionAuthentication])
@permission_classes([IsAuthenticated])
def monthly_demo(request):
    user_id = request.user.id
    period_key = request.query_params.get("period_key") or current_period_key()

    # 이전 클라이언트의 force=true도 동기 LLM 호출 대신 작업 큐로 보낸다.
    if request.query_params.get("force") == "true":
        try:
            enqueue_user_month_job(
                user_id=user_id,
                period_key=period_key,
                trigger_source='dashboard_on_demand',
            )
        except Exception:
            logger.exception("Failed to enqueue monthly MBTI analysis.")

    try:
        payload = load_latest_frontend_payload(user_id=user_id, period_key=period_key)
    except DatabaseError:
        logger.exception("Failed to load the monthly MBTI dashboard payload.")
        payload = None

    if payload is None:
        return Response({"error": "Failed to load payload"}, status=500)
    payload['analysis_job'] = latest_job_payload(
        user_id=user_id,
        period_key=period_key,
    )
    return Response(payload)


@api_view(["POST"])
@authentication_classes([CsrfExemptSessionAuthentication])
@permission_classes([IsAuthenticated])
def request_monthly_analysis(request):
    period_key = request.data.get('period_key') or current_period_key()
    try:
        result = enqueue_user_month_job(
            user_id=request.user.id,
            period_key=period_key,
            trigger_source='dashboard_on_demand',
        )
    except ValueError as exc:
        return Response({'error': str(exc)}, status=400)
    except DatabaseError:
        logger.exception("Failed to enqueue monthly MBTI analysis.")
        return Response({'error': 'Failed to enqueue analysis'}, status=500)

    if not result.eligible:
        return Response({
            'status': 'not_eligible',
            'period_key': period_key,
            'reason': result.reason,
            'analysis_job': None,
        })
    return Response({
        'status': result.job.status,
        'period_key': period_key,
        'created': result.created,
        'analysis_job': latest_job_payload(
            user_id=request.user.id,
            period_key=period_key,
        ),
    }, status=202 if result.job.status in {'pending', 'running'} else 200)


@api_view(["POST", "PUT"])
@authentication_classes([CsrfExemptSessionAuthentication])
@permission_classes([IsAuthenticated])
def set_onboarding_mbti(request):
    mbti_type = is_valid_mbti_type(request.data.get("mbti_type"))
    if mbti_type is None:
        return Response({"error": "유효한 4자리 MBTI 유형을 입력해주세요."}, status=400)

    save_onboarding_mbti(user_id=request.user.id, mbti_type=mbti_type)
    return Response({"message": "성공적으로 저장되었습니다.", "mbti_type": mbti_type})


@api_view(["GET"])
@authentication_classes([CsrfExemptSessionAuthentication])
@permission_classes([IsAuthenticated])
def get_mock_question(request):
    axis = request.query_params.get("axis")
    if axis and axis not in MBTI_AXES:
        return Response({"error": "유효한 지표가 아닙니다."}, status=400)

    try:
        question = generate_question(axis=axis)
    except RuntimeError as exc:
        return Response({"error": str(exc)}, status=500)

    period_key = current_period_key()
    axis_counts = load_axis_counts(user_id=request.user.id, period_key=period_key)
    return Response({"question": question, "axis_counts": axis_counts})


@api_view(["POST"])
@authentication_classes([CsrfExemptSessionAuthentication])
@permission_classes([IsAuthenticated])
def save_mock_answer(request):
    question_text = request.data.get("question_text")
    answer_text = request.data.get("answer_text")
    target_axis = request.data.get("target_axis")

    if not question_text or not answer_text or target_axis not in MBTI_AXES:
        return Response({"error": "필수 입력값이 누락되었거나 올바르지 않습니다."}, status=400)

    response, axis_counts = save_answer(
        user_id=request.user.id,
        question_text=question_text,
        answer_text=answer_text,
        target_axis=target_axis,
    )
    return Response(
        {
            "message": "Q&A 데이터가 성공적으로 저장되었습니다.",
            "id": response.id,
            "axis_counts": axis_counts,
        }
    )


@api_view(["DELETE"])
@authentication_classes([CsrfExemptSessionAuthentication])
@permission_classes([IsAuthenticated])
def reset_mock_qna(request):
    deleted_count = reset_current_month(user_id=request.user.id)
    return Response(
        {
            "message": "이번 달 MBTI 응답 데이터가 모두 초기화되었습니다.",
            "deleted_count": deleted_count,
            "axis_counts": EMPTY_AXIS_COUNTS.copy(),
        }
    )

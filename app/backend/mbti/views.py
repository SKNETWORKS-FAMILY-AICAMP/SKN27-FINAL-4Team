from __future__ import annotations

from json import JSONDecodeError

from django.db import DatabaseError
from rest_framework.decorators import api_view, authentication_classes, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from user.views import CsrfExemptSessionAuthentication
from mbti.models import MbtiOnboardingProfile

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
@authentication_classes([CsrfExemptSessionAuthentication])
@permission_classes([IsAuthenticated])
def monthly_demo(request):
    user = request.user
    user_id = user.id
    period_key = request.query_params.get('period_key') or None
    force = request.query_params.get('force') == 'true'

    if force:
        from mbti.services.monthly_pipeline import run_monthly_mbti_pipeline_for_user_month
        try:
            run_monthly_mbti_pipeline_for_user_month(user_id=user_id, period_key=period_key, persist_result=True)
        except Exception as e:
            print(f"Force pipeline failed: {e}")

    try:
        db_payload = load_latest_frontend_payload(
            user_id=user_id,
            period_key=period_key,
        )
    except DatabaseError:
        db_payload = None

    if db_payload is not None:
        return Response(db_payload)
        
    return Response({'error': 'Failed to load payload'}, status=500)

@api_view(['POST', 'PUT'])
@authentication_classes([CsrfExemptSessionAuthentication])
@permission_classes([IsAuthenticated])
def set_onboarding_mbti(request):
    mbti_type = request.data.get('mbti_type')
    if not mbti_type or len(mbti_type) != 4:
        return Response({'error': '유효한 4자리 MBTI 유형을 입력해주세요.'}, status=400)
    
    mbti_type = mbti_type.upper()
    from mbti.services.mbti_utils import is_valid_mbti_type
    
    if not is_valid_mbti_type(mbti_type):
        return Response({'error': '지원하지 않는 MBTI 유형입니다.'}, status=400)

    from django.utils.timezone import now
    
    user_id = request.user.id
    
    profile, created = MbtiOnboardingProfile.objects.update_or_create(
        user_id=user_id,
        defaults={
            'mbti_type': mbti_type,
            'updated_at': now()
        }
    )
    if created:
        profile.created_at = now()
        profile.save(update_fields=['created_at'])

    return Response({'message': '성공적으로 저장되었습니다.', 'mbti_type': mbti_type})

@api_view(['GET'])
@authentication_classes([CsrfExemptSessionAuthentication])
@permission_classes([IsAuthenticated])
def get_mock_question(request):
    axis = request.query_params.get('axis')
    if axis and axis not in ['IE', 'SN', 'TF', 'JP']:
        return Response({'error': '유효한 지표가 아닙니다.'}, status=400)
    
    from mbti.services.llm_mbti_question_node import generate_random_axis_mbti_question
    from mbti.services.mbti_question_node import get_next_mbti_question
    
    try:
        question = generate_random_axis_mbti_question(None, axis=axis if axis else None)
    except Exception as e:
        print(f"LLM 질문 생성 실패, 기본 질문으로 대체합니다. 원인: {e}")
        question = get_next_mbti_question(None, axis=axis if axis else None, strategy='random')
        if question is None:
            return Response({'error': f'LLM 질문 생성 실패 및 대체 질문 찾기 실패: {str(e)}'}, status=500)
        
    from django.utils.timezone import now
    from mbti.models import MbtiQuestionResponse
    from django.db.models import Count
    
    user_id = request.user.id
    current_time = now()
    period_key = current_time.strftime('%Y-%m')
    
    counts = MbtiQuestionResponse.objects.filter(
        user_id=user_id, period_key=period_key
    ).values('target_axis').annotate(count=Count('id'))
    
    axis_counts = { 'IE': 0, 'SN': 0, 'TF': 0, 'JP': 0 }
    for c in counts:
        if c['target_axis'] in axis_counts:
            axis_counts[c['target_axis']] = c['count']
            
    return Response({'question': question, 'axis_counts': axis_counts})


@api_view(['POST'])
@authentication_classes([CsrfExemptSessionAuthentication])
@permission_classes([IsAuthenticated])
def save_mock_answer(request):
    data = request.data
    question_text = data.get('question_text')
    answer_text = data.get('answer_text')
    target_axis = data.get('target_axis')
    
    if not all([question_text, answer_text, target_axis]):
        return Response({'error': '필수 입력값이 누락되었습니다.'}, status=400)
        
    from django.utils.timezone import now
    from mbti.models import MbtiQuestionResponse
    
    user_id = request.user.id
    current_time = now()
    period_key = current_time.strftime('%Y-%m')
    
    resp = MbtiQuestionResponse.objects.create(
        user_id=user_id,
        question_text=question_text,
        answer_text=answer_text,
        target_axis=target_axis,
        period_key=period_key,
        answered_at=current_time,
        created_at=current_time
    )
    
    from django.db.models import Count
    counts = MbtiQuestionResponse.objects.filter(
        user_id=user_id, period_key=period_key
    ).values('target_axis').annotate(count=Count('id'))
    
    axis_counts = { 'IE': 0, 'SN': 0, 'TF': 0, 'JP': 0 }
    for c in counts:
        if c['target_axis'] in axis_counts:
            axis_counts[c['target_axis']] = c['count']
    
    return Response({'message': 'Q&A 데이터가 성공적으로 저장되었습니다.', 'id': resp.id, 'axis_counts': axis_counts})

@api_view(['DELETE'])
@authentication_classes([CsrfExemptSessionAuthentication])
@permission_classes([IsAuthenticated])
def reset_mock_qna(request):
    from django.db import transaction
    from django.utils.timezone import now
    from mbti.models import (
        MbtiQuestionResponse,
        MbtiResponseScore,
        MbtiMonthlyResultRecord,
        MbtiMonthlyAxisResult,
        MbtiMonthlyReport,
    )
    
    user_id = request.user.id
    current_time = now()
    period_key = current_time.strftime('%Y-%m')
    
    with transaction.atomic():
        # 1. Delete Response Scores (child of MbtiQuestionResponse)
        MbtiResponseScore.objects.filter(
            user_id=user_id, period_key=period_key
        ).delete()
        
        # 2. Delete Question Responses
        deleted_count, _ = MbtiQuestionResponse.objects.filter(
            user_id=user_id, period_key=period_key
        ).delete()
        
        # 3. Delete Monthly Pipeline Results (children of MbtiMonthlyResultRecord)
        monthly_records = MbtiMonthlyResultRecord.objects.filter(
            user_id=user_id, period_key=period_key
        )
        for record in monthly_records:
            MbtiMonthlyAxisResult.objects.filter(monthly_result=record).delete()
            MbtiMonthlyReport.objects.filter(monthly_result=record).delete()
            
        # 4. Delete the Monthly Result Records themselves
        monthly_records.delete()
    
    return Response({
        'message': '이번 달 MBTI 응답 데이터가 모두 초기화되었습니다.',
        'deleted_count': deleted_count,
        'axis_counts': { 'IE': 0, 'SN': 0, 'TF': 0, 'JP': 0 }
    })

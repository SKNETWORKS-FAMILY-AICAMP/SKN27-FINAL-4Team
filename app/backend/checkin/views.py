from collections import Counter
from datetime import timedelta
import logging
import os

from django.conf import settings
from django.db import transaction
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from .models import (
    ActionFeedback,
    CauseOption,
    DailyCheckin,
    NeedOption,
    RecommendationAction,
    ReflectionOption,
)
from .serializers import DailyCheckinSerializer
from .services import (
    backend_character_id,
    calendar_entry,
    character_payload,
    cause_context_payload,
    cause_options_for,
    dialogue_for,
    option_payloads,
    recommendations_payload,
    score_recommendations,
    user_preference_groups,
)


logger = logging.getLogger(__name__)


def ok(data, http_status=status.HTTP_200_OK):
    return Response({'success': True, 'data': data, 'error': None}, status=http_status)


def error(code, message, http_status=status.HTTP_400_BAD_REQUEST):
    return Response({'success': False, 'data': None, 'error': {'code': code, 'message': message}}, status=http_status)


def _require_onboarding(request):
    if not request.user.onboarding_done or not request.user.character:
        return error('ONBOARDING_REQUIRED', '캐릭터와 기본 온보딩을 먼저 완료해주세요.', status.HTTP_403_FORBIDDEN)
    return None


def _stage_for(checkin):
    if checkin.completed_at:
        return 'COMPLETED'
    return checkin.stage


def _checkin_payload(checkin, include_options=True, include_recommendations=True, dialogue_stage=None):
    resolved_context = checkin.cause_context or (checkin.reflection.cause_context if checkin.reflection_id else '') or 'DIFFICULT'
    context_data = cause_context_payload(resolved_context)
    if not checkin.cause_context and checkin.reflection_id:
        checkin.cause_context = resolved_context
    preference_groups = user_preference_groups(checkin.user)
    feedback = checkin.feedback.filter(action=checkin.selected_action).first() if checkin.selected_action_id else None
    data = {
        'checkin': DailyCheckinSerializer(checkin).data,
        'checkin_id': checkin.id,
        'stage': _stage_for(checkin),
        'completed': bool(checkin.completed_at),
        'character': character_payload(checkin.user, checkin.primary_emotion or 'NORMAL'),
        'dialogue': dialogue_for(checkin, dialogue_stage or _stage_for(checkin)),
        **context_data,
        'cause_options': cause_options_for(resolved_context),
        'user_interests': preference_groups['interests'],
        'user_hobbies': preference_groups['hobbies'],
        'action_feedback': {
            'action_id': feedback.action_id,
            'completed': feedback.completed,
            'helpfulness': feedback.helpfulness,
        } if feedback else None,
    }
    if include_options:
        data['options'] = option_payloads(resolved_context)
    if include_recommendations:
        data['recommendations'] = recommendations_payload(checkin)
    return data


def _today_checkin(user):
    return DailyCheckin.objects.select_related('reflection', 'cause', 'need', 'selected_action').filter(
        user=user, checkin_date=timezone.localdate(),
    ).first()


def _reset_after(checkin, stage):
    if stage == 'REFLECTION':
        checkin.cause = None
        checkin.need = None
        checkin.selected_action = None
        checkin.primary_emotion = ''
        checkin.state_tags = []
        checkin.energy_level = ''
        checkin.cause_context = ''
        checkin.cause_display_text_snapshot = ''
    elif stage == 'CAUSE':
        checkin.need = None
        checkin.selected_action = None
    elif stage == 'NEED':
        checkin.selected_action = None
    checkin.final_route = ''
    checkin.completed_at = None
    checkin.recommendations.all().delete()


def _ensure_stage(checkin, expected, allow_completed=True):
    if allow_completed and checkin.completed_at:
        return True
    order = ['REFLECTION', 'CAUSE', 'NEED', 'RECOMMENDATION', 'FINAL_ROUTE', 'COMPLETED']
    if checkin.stage not in order or order.index(checkin.stage) < order.index(expected):
        return False
    return True


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def bootstrap(request):
    blocked = _require_onboarding(request)
    if blocked:
        return blocked
    checkin = _today_checkin(request.user)
    if not checkin:
        return ok({
            'has_checkin': False,
            'checkin': None,
            'stage': 'REFLECTION',
            'completed': False,
            'character': character_payload(request.user),
            'dialogue': '오늘 하루 어땠어? 천천히 떠올려보고, 가장 가까운 느낌 하나를 골라줘.',
            'cause_context': None,
            'cause_title': None,
            'cause_question': None,
            'show_cause_options': False,
            'cause_options': [],
            'options': option_payloads(),
            'recommendations': [],
            'user_interests': user_preference_groups(request.user)['interests'],
            'user_hobbies': user_preference_groups(request.user)['hobbies'],
        })
    payload = _checkin_payload(checkin)
    payload['has_checkin'] = True
    return ok(payload)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def create_checkin(request):
    blocked = _require_onboarding(request)
    if blocked:
        return blocked
    with transaction.atomic():
        checkin, created = DailyCheckin.objects.select_for_update().get_or_create(
            user=request.user,
            checkin_date=timezone.localdate(),
            defaults={'character_id': backend_character_id(request.user.character or 'pori')},
        )
    return ok(_checkin_payload(checkin), status.HTTP_201_CREATED if created else status.HTTP_200_OK)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def today(request):
    checkin = _today_checkin(request.user)
    if not checkin:
        return ok({'has_checkin': False, 'checkin': None})
    return ok({'has_checkin': True, **_checkin_payload(checkin)})


@api_view(['PATCH'])
@permission_classes([IsAuthenticated])
def save_reflection(request, checkin_id):
    checkin = get_object_or_404(DailyCheckin, id=checkin_id, user=request.user)
    reflection_id = str(request.data.get('reflection_id') or '')
    reflection = ReflectionOption.objects.filter(reflection_id=reflection_id, enabled=True).first()
    if not reflection:
        return error('INVALID_REFLECTION', '유효한 하루 돌아보기 선택지가 아닙니다.')
    with transaction.atomic():
        _reset_after(checkin, 'REFLECTION')
        checkin.reflection = reflection
        checkin.primary_emotion = reflection.primary_emotion
        checkin.secondary_emotion = reflection.secondary_emotion
        checkin.state_tags = reflection.state_tags or []
        checkin.energy_level = reflection.energy_level
        checkin.cause_context = reflection.cause_context
        checkin.stage = 'NEED' if reflection.cause_context == 'SKIP' or reflection.next_stage == 'NEED' else 'CAUSE'
        checkin.character_id = backend_character_id(request.user.character or 'pori')
        checkin.save()
    return ok(_checkin_payload(checkin, dialogue_stage='NEED' if checkin.stage == 'NEED' else 'CAUSE'))


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def restart(request, checkin_id):
    checkin = get_object_or_404(DailyCheckin, id=checkin_id, user=request.user)
    with transaction.atomic():
        _reset_after(checkin, 'REFLECTION')
        checkin.reflection = None
        checkin.stage = 'REFLECTION'
        checkin.character_id = backend_character_id(request.user.character or 'pori')
        checkin.save()
    return ok(_checkin_payload(checkin, dialogue_stage='REFLECTION'))


@api_view(['PATCH'])
@permission_classes([IsAuthenticated])
def save_cause(request, checkin_id):
    checkin = get_object_or_404(DailyCheckin, id=checkin_id, user=request.user)
    if not checkin.reflection_id:
        return error('INVALID_STAGE', '먼저 하루 돌아보기를 선택해주세요.', status.HTTP_409_CONFLICT)
    cause_id = str(request.data.get('cause_id') or '')
    cause = CauseOption.objects.filter(cause_id=cause_id, enabled=True).first()
    if not cause:
        return error('INVALID_CAUSE', '유효한 원인 선택지가 아닙니다.')
    if checkin.cause_context not in (cause.available_contexts or []):
        return error('CAUSE_CONTEXT_MISMATCH', '현재 하루 느낌에 맞는 원인 선택지가 아닙니다.')
    field = {
        'POSITIVE': 'option_text_positive',
        'DIFFICULT': 'option_text_difficult',
        'MIXED': 'option_text_mixed',
        'NEUTRAL': 'option_text_neutral',
    }.get(checkin.cause_context)
    display_text = getattr(cause, field, '') if field else cause.label
    with transaction.atomic():
        _reset_after(checkin, 'CAUSE')
        checkin.cause = cause
        checkin.cause_display_text_snapshot = display_text or cause.label
        checkin.stage = 'NEED'
        checkin.save()
    return ok(_checkin_payload(checkin, dialogue_stage='NEED'))


@api_view(['PATCH'])
@permission_classes([IsAuthenticated])
def save_need(request, checkin_id):
    checkin = get_object_or_404(DailyCheckin, id=checkin_id, user=request.user)
    if not checkin.cause_id and checkin.cause_context != 'SKIP':
        return error('INVALID_STAGE', '먼저 원인을 선택해주세요.', status.HTTP_409_CONFLICT)
    need_id = str(request.data.get('need_id') or '')
    need = NeedOption.objects.filter(need_id=need_id, enabled=True).first()
    if not need:
        return error('INVALID_NEED', '유효한 필요한 도움 선택지가 아닙니다.')
    with transaction.atomic():
        _reset_after(checkin, 'NEED')
        checkin.need = need
        checkin.stage = 'RECOMMENDATION'
        checkin.save()
    return ok(_checkin_payload(checkin, dialogue_stage='RECOMMENDATION'))


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def recommendations(request, checkin_id):
    checkin = get_object_or_404(DailyCheckin, id=checkin_id, user=request.user)
    if not checkin.need_id:
        return error('INVALID_STAGE', '먼저 필요한 도움을 선택해주세요.', status.HTTP_409_CONFLICT)
    generated = score_recommendations(checkin, request.user)
    if settings.DEBUG:
        logger.info(
            '[checkin-recommendations] pid=%s model=%s checkin_id=%s count=%s',
            os.getpid(),
            os.getenv('CHECKIN_RECOMMENDATION_MODEL', 'gpt-4o-mini'),
            checkin.id,
            len(generated),
        )
    if not generated:
        return error(
            'RECOMMENDATION_MODEL_UNAVAILABLE',
            'AI가 취미와 관심사를 바탕으로 행동을 만들지 못했어요. 잠시 후 다시 시도해주세요.',
            status.HTTP_503_SERVICE_UNAVAILABLE,
        )
    checkin.stage = 'FINAL_ROUTE'
    checkin.save(update_fields=['stage', 'updated_at'])
    return ok(_checkin_payload(checkin, dialogue_stage='FINAL_ROUTE'))


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def complete(request, checkin_id):
    checkin = get_object_or_404(DailyCheckin, id=checkin_id, user=request.user)
    route = str(request.data.get('final_route') or '')
    if route not in {'CHAT', 'ACTION', 'RECORD_ONLY'}:
        return error('INVALID_ROUTE', '유효한 완료 경로가 아닙니다.')
    if not checkin.need_id:
        return error('INVALID_STAGE', '필요한 도움을 먼저 선택해주세요.', status.HTTP_409_CONFLICT)
    action_id = str(request.data.get('selected_action_id') or '')
    action = None
    if action_id:
        action = RecommendationAction.objects.filter(action_id=action_id, enabled=True).first()
        if not action or not checkin.recommendations.filter(action=action).exists():
            return error('INVALID_ACTION', '오늘 추천된 행동 중에서 선택해주세요.')
    if route == 'ACTION' and not action:
        return error('ACTION_REQUIRED', '행동 경로에는 추천 행동을 하나 선택해주세요.')
    with transaction.atomic():
        checkin.selected_action = action
        checkin.final_route = route
        checkin.stage = 'COMPLETED'
        checkin.completed_at = timezone.now()
        checkin.save()
        checkin.recommendations.update(selected=False)
        if action:
            checkin.recommendations.filter(action=action).update(selected=True)
    payload = _checkin_payload(checkin, dialogue_stage='COMPLETED')
    payload['chat'] = {'checkin_id': checkin.id, 'path': f'/chat?checkinId={checkin.id}'} if route == 'CHAT' else None
    payload['feedback'] = {'action_id': action.action_id} if action else None
    return ok(payload)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def feedback(request, checkin_id):
    checkin = get_object_or_404(DailyCheckin, id=checkin_id, user=request.user)
    action_id = str(request.data.get('action_id') or '')
    try:
        helpfulness = int(request.data.get('helpfulness'))
    except (TypeError, ValueError):
        return error('INVALID_HELPFULNESS', '도움 정도를 확인할 수 없습니다.')
    if helpfulness not in range(1, 6):
        return error('INVALID_HELPFULNESS', '도움 정도는 1에서 5 사이여야 합니다.')
    action = RecommendationAction.objects.filter(action_id=action_id).first()
    if not action or not checkin.recommendations.filter(action=action).exists():
        return error('INVALID_ACTION', '오늘 추천된 행동이 아닙니다.')
    item, _ = ActionFeedback.objects.update_or_create(
        checkin=checkin,
        action=action,
        defaults={'completed': bool(request.data.get('completed')), 'helpfulness': helpfulness},
    )
    return ok({'feedback': {'action_id': action.action_id, 'completed': item.completed, 'helpfulness': item.helpfulness}})


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def weekly_current(request):
    today_date = timezone.localdate()
    checkins = list(DailyCheckin.objects.filter(
        user=request.user,
        checkin_date__gte=today_date - timedelta(days=6),
        checkin_date__lte=today_date,
        completed_at__isnull=False,
    ).select_related('reflection', 'cause', 'need', 'selected_action'))
    emotions = Counter(item.primary_emotion for item in checkins if item.primary_emotion)
    causes = Counter(item.cause.cause_code for item in checkins if item.cause)
    needs = Counter(item.need.need_id for item in checkins if item.need)
    actions = Counter(item.selected_action.action_id for item in checkins if item.selected_action)
    feedback_values = list(ActionFeedback.objects.filter(checkin__in=checkins).values('action_id', 'helpfulness'))
    helpful = Counter(item['action_id'] for item in feedback_values if item['helpfulness'] >= 2)
    return ok({
        'period': 'current_week',
        'sample_size': len(checkins),
        'is_sparse': len(checkins) < 3,
        'message': '기록이 아직 적어요. 조금 더 남기면 이번 주의 흐름을 볼 수 있어요.' if len(checkins) < 3 else '이번 주의 기록을 바탕으로 정리했어요.',
        'checkin_count': len(checkins),
        'top_emotion': emotions.most_common(1)[0][0] if emotions else None,
        'top_cause': causes.most_common(1)[0][0] if causes else None,
        'top_need': needs.most_common(1)[0][0] if needs else None,
        'top_action': actions.most_common(1)[0][0] if actions else None,
        'helpful_action': helpful.most_common(1)[0][0] if helpful else None,
    })


def calendar_entries_for(user, start_date, end_date):
    return [calendar_entry(item) for item in DailyCheckin.objects.filter(
        user=user, checkin_date__gte=start_date, checkin_date__lt=end_date,
    ).select_related('reflection', 'cause', 'need', 'selected_action')]

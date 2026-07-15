from django.conf import settings
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import status
from rest_framework.authentication import SessionAuthentication
from rest_framework.decorators import api_view, authentication_classes, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from .models import EmotionCardAnalysis, EmotionCardJob, EmotionCardScene, GeneratedEmotionCard
from .serializers import AnalysisPatchSerializer, AnalysisRequestSerializer, FeedbackSerializer, GenerationSerializer
from .services import analyze, build_scene, create_generation_job, ensure_card_image, update_analysis


class EmotionCardSessionAuthentication(SessionAuthentication):
    # 이 프로젝트의 로컬 Vue 프록시 기반 세션 흐름은 다른 기능에서도
    # CSRF exempt 인증을 사용한다. 마음카드만 기본 SessionAuthentication을
    # 사용하면 유효한 로그인 세션도 POST 시 403으로 차단된다.
    # 로그인 여부는 아래 IsAuthenticated 권한 검사가 계속 보장한다.
    def enforce_csrf(self, request):
        return

    def authenticate_header(self, request):
        return 'Session'


def _error(code, message, http_status):
    return Response({'error': {'code': code, 'message': message}}, status=http_status)


def _require_onboarding(request):
    if not request.user.onboarding_done or not request.user.character:
        return _error('ONBOARDING_REQUIRED', '캐릭터와 기본 정보 설정을 먼저 완료해주세요.', status.HTTP_403_FORBIDDEN)
    return None


def _analysis_payload(analysis):
    return {'analysis_id': str(analysis.id), 'analysis_status': analysis.analysis_status, 'safety_status': analysis.safety_status,
            'analysis': analysis.result, 'editable_fields': ['primary_emotion', 'energy_code', 'need_code', 'memory_focus'], 'image_generated': False}


def _scene_payload(scene):
    return {'scene_id': str(scene.id), 'scene_hash': scene.scene_hash, 'scene_preview': scene.scene_spec,
            'available_styles': [{'style_id': item['code'], 'display_name': item['display_name']} for item in scene.available_styles], 'safety_status': scene.safety_status}


def _card_payload(card):
    card = ensure_card_image(card)
    analysis = card.scene.analysis.result or {}
    scene = card.scene.scene_spec or {}
    analysis_summary = analysis.get('event_summary') or scene.get('memory_focus') or card.summary
    analysis_tags = []
    for value in (
        (analysis.get('primary_emotion') or {}).get('label'),
        (scene.get('location') or {}).get('label'),
        (scene.get('action') or {}).get('label'),
        (analysis.get('need') or {}).get('label'),
    ):
        if value and value not in analysis_tags:
            analysis_tags.append(value)
    return {'card_id': str(card.id), 'image_url': card.image_url, 'image_alt': card.image_alt, 'summary': card.summary,
            'style_id': card.style_id, 'scene': scene, 'analysis_summary': analysis_summary, 'analysis_tags': analysis_tags,
            'feedback': card.feedback, 'created_at': card.created_at}


@api_view(['POST'])
@authentication_classes([EmotionCardSessionAuthentication])
@permission_classes([IsAuthenticated])
def analyze_view(request):
    blocked = _require_onboarding(request)
    if blocked:
        return blocked
    serializer = AnalysisRequestSerializer(data=request.data)
    if not serializer.is_valid():
        return _error('INVALID_EMOTION_CARD_INPUT', serializer.errors, status.HTTP_400_BAD_REQUEST)
    analysis = analyze(serializer.validated_data, request.user)
    if analysis.safety_status == 'BLOCKED':
        return _error('EMOTION_CARD_SAFETY_BLOCKED', '지금은 카드 생성보다 가까운 사람이나 전문 도움과 연결하는 것이 먼저예요.', status.HTTP_422_UNPROCESSABLE_ENTITY)
    return Response(_analysis_payload(analysis), status=status.HTTP_201_CREATED)


@api_view(['PATCH'])
@authentication_classes([EmotionCardSessionAuthentication])
@permission_classes([IsAuthenticated])
def analysis_detail(request, analysis_id):
    blocked = _require_onboarding(request)
    if blocked:
        return blocked
    analysis = get_object_or_404(EmotionCardAnalysis, id=analysis_id, user=request.user)
    serializer = AnalysisPatchSerializer(data=request.data)
    if not serializer.is_valid():
        return _error('INVALID_EMOTION_CARD_UPDATE', serializer.errors, status.HTTP_400_BAD_REQUEST)
    return Response(_analysis_payload(update_analysis(analysis, serializer.validated_data)))


@api_view(['POST'])
@authentication_classes([EmotionCardSessionAuthentication])
@permission_classes([IsAuthenticated])
def scene_preview(request, analysis_id):
    blocked = _require_onboarding(request)
    if blocked:
        return blocked
    analysis = get_object_or_404(EmotionCardAnalysis, id=analysis_id, user=request.user)
    scene = build_scene(analysis)
    if not scene:
        return _error('EMOTION_CARD_SCENE_BLOCKED', '안전 검토가 필요한 내용은 장면으로 만들 수 없어요.', status.HTTP_422_UNPROCESSABLE_ENTITY)
    return Response(_scene_payload(scene), status=status.HTTP_201_CREATED)


@api_view(['POST'])
@authentication_classes([EmotionCardSessionAuthentication])
@permission_classes([IsAuthenticated])
def generate_view(request, scene_id):
    blocked = _require_onboarding(request)
    if blocked:
        return blocked
    scene = get_object_or_404(EmotionCardScene, id=scene_id, user=request.user)
    serializer = GenerationSerializer(data=request.data)
    if not serializer.is_valid():
        return _error('INVALID_EMOTION_CARD_GENERATION', serializer.errors, status.HTTP_400_BAD_REQUEST)
    try:
        job, reused = create_generation_job(scene, serializer.validated_data['style_id'], request.user, serializer.validated_data.get('idempotency_key'))
    except ValueError as error:
        code = str(error)
        http_status = status.HTTP_429_TOO_MANY_REQUESTS if code == 'EMOTION_CARD_RATE_LIMITED' else status.HTTP_422_UNPROCESSABLE_ENTITY
        message = '오늘 생성 가능한 마음카드를 모두 사용했어요.' if code == 'EMOTION_CARD_RATE_LIMITED' else '현재 장면과 그림체로는 생성할 수 없어요.'
        return _error(code, message, http_status)
    return Response({'job_id': str(job.id), 'status': job.status, 'progress': job.progress, 'reused': reused}, status=status.HTTP_202_ACCEPTED)


@api_view(['GET'])
@authentication_classes([EmotionCardSessionAuthentication])
@permission_classes([IsAuthenticated])
def job_detail(request, job_id):
    job = get_object_or_404(EmotionCardJob, id=job_id, user=request.user)
    return Response({'job_id': str(job.id), 'status': job.status, 'progress': job.progress, 'error_code': job.error_code, 'card_id': str(job.card_id) if job.card_id else None})


@api_view(['GET'])
@authentication_classes([EmotionCardSessionAuthentication])
@permission_classes([IsAuthenticated])
def card_detail(request, card_id):
    return Response(_card_payload(get_object_or_404(GeneratedEmotionCard, id=card_id, user=request.user)))


@api_view(['POST'])
@authentication_classes([EmotionCardSessionAuthentication])
@permission_classes([IsAuthenticated])
def card_feedback(request, card_id):
    card = get_object_or_404(GeneratedEmotionCard, id=card_id, user=request.user)
    serializer = FeedbackSerializer(data=request.data)
    if not serializer.is_valid():
        return _error('INVALID_EMOTION_CARD_FEEDBACK', serializer.errors, status.HTTP_400_BAD_REQUEST)
    card.feedback = {**card.feedback, **serializer.validated_data}
    card.save(update_fields=['feedback'])
    return Response(_card_payload(card))


@api_view(['GET'])
@authentication_classes([EmotionCardSessionAuthentication])
@permission_classes([IsAuthenticated])
def today_card(request):
    card = GeneratedEmotionCard.objects.filter(user=request.user, created_at__date=timezone.localdate()).select_related('scene').order_by('-created_at').first()
    used = GeneratedEmotionCard.objects.filter(user=request.user, created_at__date=timezone.localdate()).exclude(image_url='').count()
    limit = int(getattr(settings, 'EMOTION_CARD_MAX_DAILY_GENERATIONS', 2))
    return Response({'card': _card_payload(card) if card else None, 'daily_generation_count': {'used': used, 'limit': limit}})

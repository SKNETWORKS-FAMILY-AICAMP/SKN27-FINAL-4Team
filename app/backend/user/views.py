from django.contrib.auth import authenticate, login, logout
from django.middleware.csrf import get_token
from rest_framework.authentication import SessionAuthentication
from rest_framework.decorators import api_view, authentication_classes, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework import status

from .models import OAuthAccount, User, UserAgreementRecord, UserPreferenceKeyword, UserProfile
from .oauth import (
    SocialOAuthError,
    build_authorization_url,
    fetch_social_profile,
    get_provider_status,
    pop_validated_state,
)
from .serializers import UserPersonalProfileSerializer


class CsrfExemptSessionAuthentication(SessionAuthentication):
    def enforce_csrf(self, request):
        return


def _get_social_demo_email(provider, client_id):
    safe_provider = ''.join(char for char in provider if char.isalnum())[:20] or 'social'
    safe_client_id = ''.join(char for char in client_id if char.isalnum())[:32] or 'guest'
    return f'{safe_provider}.{safe_client_id}@binteumsai.local'


def _get_client_id(request):
    return (
        request.headers.get('X-Binteumsai-Client-Id')
        or request.data.get('client_id')
        or request.query_params.get('client_id')
        or ''
    ).strip()


def _get_development_user(request, nickname=''):
    client_id = _get_client_id(request)
    if not client_id:
        return None

    user, created = User.objects.get_or_create(
        email=_get_social_demo_email('guest', client_id),
        defaults={'nickname': (nickname or '임시 사용자')[:30]},
    )
    if created:
        user.set_unusable_password()
        user.save(update_fields=['password'])

    return user


def _serialize_auth_user(request, user, provider=None, created=False):
    onboarding_required = not user.onboarding_done
    payload = {
        'id': user.id,
        'email': user.email,
        'nickname': user.nickname,
        'character': user.character,
        'onboarding_done': user.onboarding_done,
        'onboarding_required': onboarding_required,
        'next_path': '/onboarding/character', #if onboarding_required else '/home',
        'csrf_token': get_token(request),
        'created': created,
    }
    if provider:
        payload['provider'] = provider
    return payload


def _get_connected_provider(user):
    account = user.oauth_accounts.order_by('-updated_at').first()
    return account.provider if account else ''


def _normalize_provider_birth_date(social_profile):
    birthyear = str(social_profile.get('birthyear') or '').strip()
    birthday = str(social_profile.get('birthday') or '').strip()
    if not birthyear or not birthday:
        return None

    candidate = f'{birthyear}-{birthday}'
    try:
        from datetime import date

        year, month, day = [int(part) for part in candidate.split('-')]
        return date(year, month, day)
    except (TypeError, ValueError):
        return None


def _sync_social_profile_defaults(user, social_profile):
    update_fields = []
    nickname = (social_profile.get('nickname') or social_profile.get('name') or '').strip()
    if nickname and (not user.nickname or user.nickname.endswith(' user')):
        user.nickname = nickname[:30]
        update_fields.append('nickname')

    if update_fields:
        user.save(update_fields=update_fields)

    defaults = {}
    birth_date = _normalize_provider_birth_date(social_profile)
    if birth_date:
        defaults['birth_date'] = birth_date

    gender = (social_profile.get('gender') or '').strip()
    if gender:
        gender_map = {'M': '남', 'F': '여', 'U': ''}
        defaults['gender'] = gender_map.get(gender.upper(), gender)[:20]

    if defaults:
        UserProfile.objects.update_or_create(user=user, defaults=defaults)


def _get_or_create_social_user(provider, social_profile):
    provider_user_id = social_profile['provider_user_id']
    email = social_profile.get('email', '').strip()
    nickname = (social_profile.get('nickname') or f'{provider} user')[:30]

    account = OAuthAccount.objects.select_related('user').filter(
        provider=provider,
        provider_user_id=provider_user_id,
    ).first()
    if account:
        account.email = email
        account.raw_profile = social_profile.get('raw_profile') or {}
        account.save(update_fields=['email', 'raw_profile', 'updated_at'])
        _sync_social_profile_defaults(account.user, social_profile)
        return account.user, False

    user = User.objects.filter(email=email).first() if email else None
    created = False
    if user is None:
        user = User.objects.create_user(
            email=email or _get_social_demo_email(provider, provider_user_id),
            password=None,
            nickname=nickname,
        )
        user.set_unusable_password()
        user.save(update_fields=['password'])
        created = True

    OAuthAccount.objects.create(
        user=user,
        provider=provider,
        provider_user_id=provider_user_id,
        email=email,
        raw_profile=social_profile.get('raw_profile') or {},
    )
    _sync_social_profile_defaults(user, social_profile)
    return user, created


def _normalize_keyword_labels(labels):
    result = []
    seen = set()
    for label in labels or []:
        normalized = str(label or '').strip()
        if not normalized or normalized in seen:
            continue
        seen.add(normalized)
        result.append(normalized[:100])
    return result


def _sync_preference_keywords(user, keyword_type, labels):
    normalized_labels = _normalize_keyword_labels(labels)
    UserPreferenceKeyword.objects.filter(
        user=user,
        keyword_type=keyword_type,
    ).exclude(label__in=normalized_labels).delete()

    for label in normalized_labels:
        UserPreferenceKeyword.objects.update_or_create(
            user=user,
            keyword_type=keyword_type,
            label=label,
            defaults={'source': 'onboarding'},
        )


@api_view(['POST'])
@permission_classes([AllowAny])
def register(request):
    email = request.data.get('email')
    password = request.data.get('password')
    nickname = request.data.get('nickname', '')
    if not email or not password:
        return Response({'error': '이메일과 비밀번호는 필수입니다.'}, status=status.HTTP_400_BAD_REQUEST)
    if User.objects.filter(email=email).exists():
        return Response({'error': '이미 사용 중인 이메일입니다.'}, status=status.HTTP_400_BAD_REQUEST)
    user = User.objects.create_user(email=email, password=password, nickname=nickname)
    return Response({'id': user.id, 'email': user.email}, status=status.HTTP_201_CREATED)


@api_view(['POST'])
@permission_classes([AllowAny])
def login_view(request):
    email = request.data.get('email')
    password = request.data.get('password')
    user = authenticate(request, username=email, password=password)
    if user is None:
        return Response({'error': '이메일 또는 비밀번호가 올바르지 않습니다.'}, status=status.HTTP_401_UNAUTHORIZED)
    login(request, user)
    
    # 로그인 시 백그라운드에서 대체 리포트 미리 생성
    import threading
    from mindreport.services.fallback_service import FallbackReportService
    threading.Thread(target=FallbackReportService.generate_and_save_fallback_report, args=(user,)).start()
    
    return Response({
        'id': user.id,
        'email': user.email,
        'nickname': user.nickname,
        'csrf_token': get_token(request),
    })


@api_view(['POST'])
@permission_classes([AllowAny])
def social_login_mock(request):
    provider = request.data.get('provider', 'social')
    client_id = request.headers.get('X-Binteumsai-Client-Id', '')
    provider_labels = {
        'kakao': '카카오',
        'google': 'Google',
        'naver': '네이버',
    }
    provider_label = provider_labels.get(provider, '소셜')

    user, created = User.objects.get_or_create(
        email=_get_social_demo_email(provider, client_id),
        defaults={'nickname': f'{provider_label} 사용자'},
    )
    if created:
        user.set_unusable_password()
        user.save(update_fields=['password'])

    login(request, user)
    return Response(_serialize_auth_user(request, user, provider=provider, created=created))


@api_view(['GET'])
@permission_classes([AllowAny])
def social_login_providers(request):
    return Response({'providers': get_provider_status()})


@api_view(['GET'])
@permission_classes([AllowAny])
def social_login_url(request, provider):
    try:
        authorization_url = build_authorization_url(
            request,
            provider,
            request.query_params.get('next', ''),
        )
    except SocialOAuthError as exc:
        return Response({'error': str(exc)}, status=status.HTTP_400_BAD_REQUEST)

    return Response({'provider': provider, 'authorization_url': authorization_url})


@api_view(['POST'])
@authentication_classes([CsrfExemptSessionAuthentication])
@permission_classes([AllowAny])
def social_login_callback(request, provider):
    code = request.data.get('code', '')
    state = request.data.get('state', '')
    if not code or not state:
        return Response({'error': 'OAuth code and state are required.'}, status=status.HTTP_400_BAD_REQUEST)

    try:
        pop_validated_state(request, provider, state)
        social_profile = fetch_social_profile(provider, code)
        user, created = _get_or_create_social_user(provider, social_profile)
    except SocialOAuthError as exc:
        return Response({'error': str(exc)}, status=status.HTTP_400_BAD_REQUEST)

    if not user.is_active:
        return Response({'error': 'Inactive user.'}, status=status.HTTP_403_FORBIDDEN)

    login(request, user)
    
    # 소셜 로그인 시 백그라운드에서 대체 리포트 미리 생성
    import threading
    from mindreport.services.fallback_service import FallbackReportService
    threading.Thread(target=FallbackReportService.generate_and_save_fallback_report, args=(user,)).start()
    
    return Response(_serialize_auth_user(request, user, provider=provider, created=created))


@api_view(['GET'])
@permission_classes([AllowAny])
def current_user(request):
    if not request.user.is_authenticated:
        return Response({
            'authenticated': False,
            'csrf_token': get_token(request),
            'user': None,
        })

    return Response({
        'authenticated': True,
        'user': _serialize_auth_user(
            request,
            request.user,
            provider=_get_connected_provider(request.user),
        ),
    })


@api_view(['POST'])
@authentication_classes([CsrfExemptSessionAuthentication])
@permission_classes([AllowAny])
def logout_view(request):
    logout(request)
    return Response({
        'message': '로그아웃 되었습니다.',
        'csrf_token': get_token(request),
    })


@api_view(['GET', 'PUT'])
@authentication_classes([CsrfExemptSessionAuthentication])
@permission_classes([AllowAny])
def profile(request):
    nickname = request.data.get('nickname', '').strip()
    profile_user = request.user if request.user.is_authenticated else _get_development_user(request, nickname)
    if profile_user is None:
        return Response({'error': '사용자 정보를 저장할 임시 식별자가 없습니다.'}, status=status.HTTP_400_BAD_REQUEST)

    if request.method == 'GET':
        personal_profile = UserProfile.objects.filter(user=profile_user).first()
        return Response({
            'profile': UserPersonalProfileSerializer(personal_profile).data if personal_profile else None
        })

    serializer = UserPersonalProfileSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    profile_data = dict(serializer.validated_data)
    agreements = profile_data.pop('agreements', None)

    if (
        not isinstance(agreements, dict)
        or agreements.get('termsOfService') is not True
        or agreements.get('privacyCollection') is not True
        or agreements.get('overseasTransfer') is not True
    ):
        return Response({'error': '필수 약관 동의가 필요합니다.'}, status=status.HTTP_400_BAD_REQUEST)

    existing_profile = UserProfile.objects.filter(user=profile_user).first()
    previous_birth_date = existing_profile.birth_date if existing_profile else None
    next_birth_date = profile_data.get('birth_date')

    if nickname:
        profile_user.nickname = nickname[:30]
        profile_user.save(update_fields=['nickname'])

    personal_profile, _ = UserProfile.objects.update_or_create(
        user=profile_user,
        defaults=profile_data,
    )
    agreement_versions = {
        'terms_version': str(agreements.get('termsVersion') or '')[:20],
        'privacy_version': str(agreements.get('privacyVersion') or '')[:20],
        'overseas_transfer_version': str(agreements.get('overseasTransferVersion') or '')[:20],
    }
    if all(agreement_versions.values()):
        UserAgreementRecord.objects.get_or_create(
            user=profile_user,
            **agreement_versions,
            defaults={
                'details': {
                    'terms_of_service': True,
                    'privacy_collection': True,
                    'overseas_transfer': True,
                }
            },
        )
    _sync_preference_keywords(profile_user, 'hobby', profile_data.get('hobbies', []))
    _sync_preference_keywords(profile_user, 'interest', profile_data.get('interests', []))

    if request.user.is_authenticated and not profile_user.onboarding_done:
        profile_user.onboarding_done = True
        profile_user.save(update_fields=['onboarding_done'])
        
        # 온보딩 완료 시 백그라운드에서 대체 리포트 다시 미리 생성 (취미/관심사 반영)
        import threading
        from mindreport.services.fallback_service import FallbackReportService
        threading.Thread(target=FallbackReportService.generate_and_save_fallback_report, args=(profile_user,)).start()

    if previous_birth_date != next_birth_date:
        from game.tarot_api.models import DailyTarotFortune

        DailyTarotFortune.objects.filter(
            user=profile_user,
            fortune_type='daily_major',
        ).delete()

    return Response(
        {'profile': UserPersonalProfileSerializer(personal_profile).data},
        status=status.HTTP_200_OK,
    )

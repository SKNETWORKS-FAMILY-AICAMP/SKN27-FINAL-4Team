from django.conf import settings
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response

from config.permissions import IsAuthenticatedOrDevelopment
from .models import CharacterPreference
from .serializers import CharacterPreferenceSerializer

BACKEND_CHARACTER_BY_ASSET = {
    'redpanda': 'pori',
    'cat': 'kkami',
    'otter': 'toto',
    'bird': 'yeoul',
    'pori': 'pori',
    'kkami': 'kkami',
    'toto': 'toto',
    'yeoul': 'yeoul',
}


def get_client_id(request):
    value = (
        request.headers.get('X-Binteumsai-Client-Id')
        or request.data.get('client_id')
        or request.query_params.get('client_id')
        or ''
    )
    return value.strip()[:64]


def get_owner_filter(request):
    if request.user.is_authenticated:
        return {'user': request.user}

    if not settings.DEBUG:
        return None

    client_id = get_client_id(request)
    if not client_id:
        return None

    return {'user__isnull': True, 'client_id': client_id}


@api_view(['GET', 'POST', 'PUT'])
@permission_classes([IsAuthenticatedOrDevelopment])
def character_preference(request):
    owner_filter = get_owner_filter(request)
    if owner_filter is None:
        return Response({'preference': None}, status=status.HTTP_200_OK)

    if request.method == 'GET':
        preference = CharacterPreference.objects.filter(**owner_filter).first()
        return Response({
            'preference': CharacterPreferenceSerializer(preference).data if preference else None
        })

    serializer = CharacterPreferenceSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)

    defaults = {
        'character_id': serializer.validated_data['character_id'],
        'expression_id': serializer.validated_data['expression_id'],
        'client_id': '' if request.user.is_authenticated else get_client_id(request),
    }
    preference, _ = CharacterPreference.objects.update_or_create(
        **owner_filter,
        defaults=defaults,
    )
    if request.user.is_authenticated:
        request.user.character = BACKEND_CHARACTER_BY_ASSET.get(
            serializer.validated_data['character_id'],
            serializer.validated_data['character_id'],
        )
        request.user.save(update_fields=['character'])

    return Response(
        {'preference': CharacterPreferenceSerializer(preference).data},
        status=status.HTTP_200_OK,
    )

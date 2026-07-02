from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from .models import UserProfile
from .serializers import UserProfileSerializer


def _default_profile_data(user):
    character_map = {
        'haeon': 'sol',
        'greung': 'luna',
        'dalkong': 'on',
        'sol': 'sol',
        'luna': 'luna',
        'on': 'on',
        'nari': 'nari',
    }
    selected_character = character_map.get(user.character, 'sol')

    return {
        'name': user.nickname or 'User',
        'mbti': 'INFP',
        'gender': 'unspecified',
        'age': 24,
        'birthday': '06.23',
        'job': 'Preparing a project',
        'status': 'Open to conversation',
        'keywords': 'empathy, focus, journal',
        'interests': ['daily', 'music', 'relationship'],
        'hobbies': 'Making playlists',
        'selected_character': selected_character,
    }


@api_view(['GET', 'PUT', 'PATCH'])
@permission_classes([IsAuthenticated])
def profile_detail(request):
    profile, _ = UserProfile.objects.get_or_create(
        user=request.user,
        defaults=_default_profile_data(request.user),
    )

    if request.method == 'GET':
        return Response(UserProfileSerializer(profile).data)

    serializer = UserProfileSerializer(profile, data=request.data)
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    serializer.save()
    return Response(serializer.data)

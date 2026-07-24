from rest_framework.decorators import api_view, authentication_classes, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from django.db import transaction
from django.utils import timezone
from character.models import CharacterPreference
from user.models import UserProfile
from .constants import (
    PROFILE_PREFERENCE_MINIMUM_ERROR,
    has_minimum_preferences,
    to_backend_character_id,
)
from user.views import CsrfExemptSessionAuthentication
from .serializers import MyProfileSerializer
from datetime import datetime

from .emotion_service import build_today_emotion_summary


@api_view(['GET', 'PUT'])
@authentication_classes([CsrfExemptSessionAuthentication])
@permission_classes([IsAuthenticated])
def profile_detail(request):
    user = request.user

    profile = UserProfile.objects.filter(user=user).first()
    if profile is None:
        return Response(
            {'detail': 'Onboarding profile not found.'},
            status=status.HTTP_404_NOT_FOUND,
        )

    if request.method == 'GET':
        serializer = MyProfileSerializer({'user': user, 'profile': profile})
        return Response({'profile': serializer.data})

    elif request.method == 'PUT':
        serializer = MyProfileSerializer(data=request.data.get('profile', request.data))
        if serializer.is_valid():
            data = serializer.validated_data

            if 'interests' in data or 'hobbies' in data:
                next_interests = data.get('interests', profile.interests or [])
                next_hobbies = data.get('hobbies', profile.hobbies or [])
                if not has_minimum_preferences(
                    hobbies=next_hobbies,
                    interests=next_interests,
                ):
                    return Response(
                        {'preferences': [PROFILE_PREFERENCE_MINIMUM_ERROR]},
                        status=status.HTTP_400_BAD_REQUEST,
                    )

            # Keep the existing request/response contract, but commit the user
            # and profile rows together so book recommendation never observes a
            # half-written profile.
            with transaction.atomic():
                user_update_fields = []
                if 'name' in data:
                    user.nickname = data['name'][:30]
                    user_update_fields.append('nickname')
                selected_character = data.get('selectedCharacter')
                if selected_character:
                    user.character = to_backend_character_id(selected_character)
                    user_update_fields.append('character')
                if user_update_fields:
                    user.save(update_fields=user_update_fields)

                if selected_character:
                    preference = (
                        CharacterPreference.objects.select_for_update()
                        .filter(user=user)
                        .order_by('-updated_at')
                        .first()
                    )
                    if preference:
                        preference.character_id = selected_character
                        preference.save(update_fields=['character_id', 'updated_at'])
                    else:
                        CharacterPreference.objects.create(
                            user=user,
                            character_id=selected_character,
                            expression_id='default',
                        )

                profile_update_fields = []
                if 'job' in data:
                    profile.job = data['job']
                    profile_update_fields.append('job')
                if 'gender' in data:
                    profile.gender = data['gender']
                    profile_update_fields.append('gender')
                if 'interests' in data:
                    profile.interests = data['interests']
                    profile_update_fields.append('interests')
                if 'hobbies' in data:
                    profile.hobbies = data['hobbies']
                    profile_update_fields.append('hobbies')
                if 'birthDate' in data:
                    date_str = data['birthDate'].strip()
                    if date_str:
                        try:
                            date_obj = datetime.strptime(date_str, "%Y.%m.%d").date()
                            profile.birth_date = date_obj
                            today = timezone.localdate()
                            profile.age = today.year - date_obj.year - ((today.month, today.day) < (date_obj.month, date_obj.day))
                            profile_update_fields.extend(['birth_date', 'age'])
                        except ValueError:
                            pass
                    else:
                        profile.birth_date = None
                        profile.age = None
                        profile_update_fields.extend(['birth_date', 'age'])
                if profile_update_fields:
                    profile.save(update_fields=[*dict.fromkeys(profile_update_fields), 'updated_at'])

            return Response({'profile': MyProfileSerializer({'user': user, 'profile': profile}).data})

        return Response(serializer.errors, status=400)


@api_view(['GET'])
@authentication_classes([CsrfExemptSessionAuthentication])
@permission_classes([IsAuthenticated])
def today_emotion_summary(request):
    return Response(build_today_emotion_summary(request.user))

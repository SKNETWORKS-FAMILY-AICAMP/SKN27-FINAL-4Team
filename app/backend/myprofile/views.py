from rest_framework.decorators import api_view, authentication_classes, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from django.db import transaction
from django.db.models import Count
from django.utils import timezone
from user.models import UserProfile
from user.views import CsrfExemptSessionAuthentication
from .serializers import MyProfileSerializer
from datetime import datetime


EMOTION_LABELS_KO = {
    'joy': '기쁨',
    'sadness': '슬픔',
    'anger': '분노',
    'normal': '평온',
}

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

            # Keep the existing request/response contract, but commit the user
            # and profile rows together so book recommendation never observes a
            # half-written profile.
            with transaction.atomic():
                user_update_fields = []
                if 'name' in data:
                    user.nickname = data['name'][:30]
                    user_update_fields.append('nickname')
                if 'selectedCharacter' in data:
                    user.character = data['selectedCharacter'][:10]
                    user_update_fields.append('character')
                if user_update_fields:
                    user.save(update_fields=user_update_fields)

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
    from chat.models import ChatMessage

    today = timezone.localdate()
    rows = list(
        ChatMessage.objects.filter(
            session__user=request.user,
            emotion_label__isnull=False,
            created_at__date=today,
        )
        .exclude(emotion_label='')
        .values('emotion_label')
        .annotate(count=Count('id'))
        .order_by('-count', 'emotion_label')
    )

    total_count = sum(row['count'] for row in rows)
    top_count = rows[0]['count'] if rows else 0
    dominant = [
        {
            'key': row['emotion_label'],
            'label': EMOTION_LABELS_KO.get(row['emotion_label'], row['emotion_label']),
            'count': row['count'],
        }
        for row in rows
        if row['count'] == top_count
    ]
    distribution = [
        {
            'key': row['emotion_label'],
            'label': EMOTION_LABELS_KO.get(row['emotion_label'], row['emotion_label']),
            'count': row['count'],
        }
        for row in rows
    ]

    return Response({
        'date': today.isoformat(),
        'total_count': total_count,
        'dominant': dominant,
        'distribution': distribution,
    })

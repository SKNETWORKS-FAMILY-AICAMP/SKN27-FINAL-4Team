from rest_framework.decorators import api_view, authentication_classes, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from user.models import UserProfile
from user.views import CsrfExemptSessionAuthentication
from .serializers import MyProfileSerializer
from datetime import datetime

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
            
            # Update User model
            if 'name' in data:
                user.nickname = data['name'][:30]
            if 'selectedCharacter' in data:
                user.character = data['selectedCharacter'][:10]
            user.save(update_fields=['nickname', 'character'])

            # Update UserProfile model
            if 'job' in data:
                profile.job = data['job']
            if 'gender' in data:
                profile.gender = data['gender']
            if 'interests' in data:
                profile.interests = data['interests']
            if 'hobbies' in data:
                profile.hobbies = data['hobbies']
            if 'birthDate' in data:
                date_str = data['birthDate'].strip()
                if date_str:
                    try:
                        date_obj = datetime.strptime(date_str, "%Y.%m.%d").date()
                        profile.birth_date = date_obj
                    except ValueError:
                        pass
                else:
                    profile.birth_date = None
            
            profile.save()

            return Response({'profile': MyProfileSerializer({'user': user, 'profile': profile}).data})
        
        return Response(serializer.errors, status=400)
from django.contrib.auth import authenticate, login, logout
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from .models import User


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
    return Response({'id': user.id, 'email': user.email, 'nickname': user.nickname})


@api_view(['POST'])
def logout_view(request):
    logout(request)
    return Response({'message': '로그아웃 되었습니다.'})


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def profile(request):
    user = request.user
    return Response({
        'id': user.id,
        'email': user.email,
        'nickname': user.nickname,
        'character': user.character,
        'onboarding_done': user.onboarding_done,
    })

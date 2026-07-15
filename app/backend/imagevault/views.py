from rest_framework import status
from rest_framework.decorators import api_view, authentication_classes, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from user.views import CsrfExemptSessionAuthentication

from .models import SavedCardImage
from .serializers import SavedCardImageSerializer


@api_view(["GET", "POST"])
@authentication_classes([CsrfExemptSessionAuthentication])
@permission_classes([IsAuthenticated])
def image_collection(request):
    if request.method == "GET":
        images = SavedCardImage.objects.filter(user=request.user)
        return Response({"items": SavedCardImageSerializer(images, many=True).data})

    serializer = SavedCardImageSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    image = serializer.save(user=request.user)
    return Response(SavedCardImageSerializer(image).data, status=status.HTTP_201_CREATED)


@api_view(["PATCH", "DELETE"])
@authentication_classes([CsrfExemptSessionAuthentication])
@permission_classes([IsAuthenticated])
def image_detail(request, image_id):
    image = SavedCardImage.objects.filter(user=request.user, id=image_id).first()
    if image is None:
        return Response({"detail": "이미지를 찾을 수 없습니다."}, status=status.HTTP_404_NOT_FOUND)

    if request.method == "DELETE":
        image.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

    serializer = SavedCardImageSerializer(image, data=request.data, partial=True)
    serializer.is_valid(raise_exception=True)
    serializer.save()
    return Response(serializer.data)

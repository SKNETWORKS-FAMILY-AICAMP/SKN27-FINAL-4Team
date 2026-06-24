from rest_framework.decorators import api_view
from rest_framework.response import Response


@api_view(['GET'])
def report_list(request):
    return Response([])


@api_view(['GET'])
def today_report(request):
    return Response({'message': '오늘의 리포트 준비 중입니다.'})

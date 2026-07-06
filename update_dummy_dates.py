import os
import sys
import django
from datetime import timedelta
from django.utils import timezone

sys.path.append(os.path.join(os.path.dirname(__file__), 'app', 'backend'))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from chat.models import ChatMessage

# 오늘이 월요일이라면 5일 전은 지난주가 됩니다.
# 현재 주의 월요일 ~ 일요일 사이에 들어가도록 날짜를 조정합니다.
today = timezone.now()
start_of_week = today - timedelta(days=today.weekday())

# 기존에 넣은 데이터들의 날짜를 모두 이번 주(start_of_week) 이후로 당깁니다.
# 6개의 메시지를 오늘부터 1시간 간격으로 설정합니다.
messages = ChatMessage.objects.order_by('-id')[:6]

for i, msg in enumerate(messages):
    # 오늘 자정 이후로 1시간 간격으로 배치
    new_date = start_of_week + timedelta(hours=i)
    ChatMessage.objects.filter(id=msg.id).update(created_at=new_date)

print("Updated dates to be within the current week!")

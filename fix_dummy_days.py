import os
import sys
import django
from datetime import timedelta
from django.utils import timezone

sys.path.append(os.path.join(os.path.dirname(__file__), 'app', 'backend'))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from django.contrib.auth import get_user_model
from chat.models import ChatSession, ChatMessage

User = get_user_model()
users = User.objects.all()

today = timezone.now()
start_of_week = today - timedelta(days=today.weekday())

# 기존 더미 텍스트 목록
dummy_contents = [
    "오늘 프로젝트 회의를 했는데 팀원들이랑 의견이 안 맞아서 너무 답답하고 짜증났다. 계속 긴장 상태였음.",
    "어제 일 때문에 잠을 못 잤더니 너무 피곤하다. 부모님도 잔소리하시고 대학교 친구랑도 연락 문제로 조금 다퉜어.",
    "도저히 안 되겠다 싶어서 다 내려놓고 1시간 동안 무작정 산책을 했다. 조금 숨이 트이는 기분.",
    "오늘은 따뜻한 차 마시면서 짧게 낮잠을 잤더니 피로가 많이 풀렸다. 확실히 휴식이 필요했던 것 같아.",
    "집에서 뒹굴거리면서 네이버웹툰 보고 포켓몬 게임도 하니까 스트레스가 확 풀린다! 역시 이게 내 방식의 힐링이야.",
    "절친이랑 통화하면서 그동안 쌓인 이야기 다 털어놓았다. 마음이 한결 가볍고 이제 다시 프로젝트 집중할 수 있을 듯!"
]

# 기존 더미 데이터 삭제
deleted, _ = ChatMessage.objects.filter(content__in=dummy_contents).delete()
print(f"Deleted {deleted} old dummy messages.")

dummy_data = [
    (start_of_week, dummy_contents[0], "anger"),
    (start_of_week + timedelta(days=1), dummy_contents[1], "sadness"),
    (start_of_week + timedelta(days=2), dummy_contents[2], "normal"),
    (start_of_week + timedelta(days=3), dummy_contents[3], "normal"),
    (start_of_week + timedelta(days=4), dummy_contents[4], "joy"),
    (start_of_week + timedelta(days=5), dummy_contents[5], "joy"),
]

for user in users:
    session = ChatSession.objects.filter(user=user).first()
    if not session:
        session = ChatSession.objects.create(user=user)
    
    print(f"Inserting daily dummy chats for user ID: {user.id}")
    for dt, content, emotion in dummy_data:
        msg = ChatMessage.objects.create(
            session=session,
            role='user',
            content=content,
            emotion_label=emotion
        )
        ChatMessage.objects.filter(id=msg.id).update(created_at=dt)

print("Successfully inserted daily spaced dummy chats for all users!")

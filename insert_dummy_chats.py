import os
import sys
import django
from datetime import timedelta
from django.utils import timezone

# Setup Django environment
sys.path.append(os.path.join(os.path.dirname(__file__), 'app', 'backend'))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from django.contrib.auth import get_user_model
from chat.models import ChatSession, ChatMessage

User = get_user_model()
user = User.objects.first()

if not user:
    print("No user found. Please create a user first.")
    sys.exit()

# Get or create a session for the user
session, _ = ChatSession.objects.get_or_create(user=user)

today = timezone.now()

# Define dummy data
dummy_data = [
    (today - timedelta(days=5), "오늘 프로젝트 회의를 했는데 팀원들이랑 의견이 안 맞아서 너무 답답하고 짜증났다. 계속 긴장 상태였음.", "anger"),
    (today - timedelta(days=4), "어제 일 때문에 잠을 못 잤더니 너무 피곤하다. 부모님도 잔소리하시고 대학교 친구랑도 연락 문제로 조금 다퉜어.", "sadness"),
    (today - timedelta(days=3), "도저히 안 되겠다 싶어서 다 내려놓고 1시간 동안 무작정 산책을 했다. 조금 숨이 트이는 기분.", "normal"),
    (today - timedelta(days=2), "오늘은 따뜻한 차 마시면서 짧게 낮잠을 잤더니 피로가 많이 풀렸다. 확실히 휴식이 필요했던 것 같아.", "normal"),
    (today - timedelta(days=1), "집에서 뒹굴거리면서 네이버웹툰 보고 포켓몬 게임도 하니까 스트레스가 확 풀린다! 역시 이게 내 방식의 힐링이야.", "joy"),
    (today, "절친이랑 통화하면서 그동안 쌓인 이야기 다 털어놓았다. 마음이 한결 가볍고 이제 다시 프로젝트 집중할 수 있을 듯!", "joy"),
]

print(f"Inserting dummy chats for user ID: {user.id}")

for dt, content, emotion in dummy_data:
    msg = ChatMessage.objects.create(
        session=session,
        role='user',
        content=content,
        emotion_label=emotion
    )
    # auto_now_add=True 일 경우를 대비해 update 쿼리로 날짜를 강제 수정
    ChatMessage.objects.filter(id=msg.id).update(created_at=dt)

print("Successfully inserted 6 dummy chat messages into the database!")

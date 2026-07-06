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

# 기존 더미 데이터 완전 삭제 (식별을 위해 [DUMMY] 태그가 있었던 건 아니지만, 일괄 삭제)
# 안전을 위해 모든 메시지 중 이번 주 월요일 이후 데이터만 삭제합니다.
start_datetime = timezone.make_aware(timezone.datetime.combine(start_of_week, timezone.datetime.min.time()))
ChatMessage.objects.filter(created_at__gte=start_datetime).delete()

# 리얼한 대화량 구성을 위한 다중 메시지 세팅
realistic_conversations = {
    0: [  # 월요일 (Anger)
        "오늘 진짜 최악이었어.",
        "팀 프로젝트 회의를 했는데, 의견 조율이 하나도 안 돼.",
        "다들 자기 할 말만 하고 내 의견은 묵살당하는 기분이라 너무 화가 났어.",
        "결국 결론도 못 내고 시간만 낭비했어. 내일 또 회의해야 하는데 벌써 스트레스야.",
        "집에 오니까 머리도 아프고 그냥 다 포기하고 싶어."
    ],
    1: [  # 화요일 (Sadness)
        "어제 스트레스 받아서 밤을 샜더니 너무 피곤해.",
        "학교 수업 내내 졸고 집중도 하나도 못했어.",
        "게다가 부모님이랑 취업 문제로 전화하다가 또 다퉜어.",
        "나름대로 열심히 하고 있는데 아무도 몰라주는 것 같아서 너무 우울하다.",
        "대학교 친구한테 하소연하려고 했는데 걔도 바빠 보여서 말도 못 꺼냈어."
    ],
    2: [  # 수요일 (Normal)
        "오늘은 기분 전환 좀 하려고 수업 끝나고 무작정 걸었어.",
        "학교 주변에 안 가본 공원이 있길래 한 시간 정도 산책했거든.",
        "잡생각 안 하고 노래 들으면서 걸으니까 확실히 머리가 좀 맑아지는 것 같아.",
        "저녁에는 그냥 맛있는 거 시켜 먹고 푹 쉬려고 해.",
        "조금 숨이 트이는 기분이야."
    ],
    3: [  # 목요일 (Normal)
        "오늘 공강이라 집에서 하루 종일 쉬었어.",
        "밀린 빨래도 하고 방 청소도 하니까 기분이 한결 낫더라.",
        "오후에는 따뜻한 차 마시면서 짧게 낮잠을 잤어.",
        "몸이 찌뿌둥했는데 피로가 많이 풀린 느낌이야.",
        "확실히 나한테는 이런 온전한 휴식 시간이 꼭 필요한 것 같아."
    ],
    4: [  # 금요일 (Joy)
        "드디어 금요일이야! 오늘 하루 종일 집에서 뒹굴거렸어.",
        "밀린 네이버웹툰 정주행하고 닌텐도 스위치로 포켓몬 게임도 실컷 했어.",
        "맛있는 피자도 시켜 먹으면서 게임하니까 스트레스가 확 풀린다!",
        "역시 복잡하게 생각 안 하고 좋아하는 거 하는 게 최고의 힐링이야.",
        "이번 주말에는 계속 이렇게 푹 쉬어야지."
    ],
    5: [  # 토요일 (Joy)
        "오늘 고등학교 때 제일 친했던 친구랑 오랜만에 전화했어.",
        "거의 2시간 동안 통화하면서 그동안 쌓인 이야기 다 털어놓았다!",
        "친구도 비슷한 고민을 하고 있어서 위로도 많이 받고 서로 응원해줬어.",
        "마음이 한결 가볍고 이제 다시 프로젝트에 집중할 수 있을 것 같은 에너지가 생겼어.",
        "다음 주부터는 다시 파이팅 해보려고!"
    ]
}

emotion_map = {0: "anger", 1: "sadness", 2: "normal", 3: "normal", 4: "joy", 5: "joy"}

for user in users:
    session = ChatSession.objects.filter(user=user).first()
    if not session:
        session = ChatSession.objects.create(user=user)
    
    print(f"Inserting realistic daily chats for user ID: {user.id}")
    
    for day_offset, messages in realistic_conversations.items():
        base_dt = start_of_week + timedelta(days=day_offset)
        
        for idx, content in enumerate(messages):
            # 같은 날짜 안에서도 분 단위로 시간을 조금씩 벌려줍니다. (현실감 부여)
            msg_dt = base_dt + timedelta(minutes=idx * 5)
            
            msg = ChatMessage.objects.create(
                session=session,
                role='user',
                content=content,
                emotion_label=emotion_map[day_offset]
            )
            ChatMessage.objects.filter(id=msg.id).update(created_at=msg_dt)

print("Successfully inserted REALISTIC daily dummy chats for all users!")

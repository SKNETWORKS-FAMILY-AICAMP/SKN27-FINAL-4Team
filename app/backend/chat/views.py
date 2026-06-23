import json
import os
from pathlib import Path

from django.conf import settings as django_settings
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework import status
from openai import OpenAI

from .models import ChatSession, ChatMessage
from .serializers import ChatSessionSerializer, ChatMessageSerializer

PROMPT_DIR = Path(__file__).resolve().parent.parent.parent / 'prompts'
VALID_CHARACTERS = {'haeon', 'greung', 'dalkong'}
GROQ_MODEL = 'llama-3.3-70b-versatile'


def _client() -> OpenAI:
    return OpenAI(
        api_key=os.environ.get('GROQ_API_KEY', ''),
        base_url=os.environ.get('GROQ_BASE_URL', 'https://api.groq.com/openai/v1'),
    )


_DEFAULT_PROMPTS = {
    'haeon': {
        'system_instruction': '당신은 해온이입니다. 따뜻하고 공감 능력이 뛰어난 감성 상담 캐릭터로, 사용자의 감정을 부드럽게 위로하고 공감해줍니다.',
        'model_settings': {'max_tokens': 250, 'temperature': 0.7},
    },
    'greung': {
        'system_instruction': '당신은 그릉이입니다. 현실적이고 직설적인 상담 캐릭터로, CBT 기반의 날카로운 피드백으로 사용자가 현실을 직면하도록 돕습니다.',
        'model_settings': {'max_tokens': 250, 'temperature': 0.7},
    },
    'dalkong': {
        'system_instruction': '당신은 달콩이입니다. 긍정적이고 활기찬 코칭 캐릭터로, ACT 기반의 행동 지향적 조언으로 사용자를 응원합니다.',
        'model_settings': {'max_tokens': 250, 'temperature': 0.7},
    },
}

def _load_prompt(character: str) -> dict:
    prompt_file = PROMPT_DIR / f'{character}_prompt.json'
    if prompt_file.exists():
        with open(prompt_file, encoding='utf-8') as f:
            return json.load(f)
    return _DEFAULT_PROMPTS.get(character, _DEFAULT_PROMPTS['haeon'])


def _build_system_message(prompt_data: dict) -> str:
    parts = [prompt_data['system_instruction']]
    if prompt_data.get('dialogue_rules'):
        rules = '\n'.join(f'- {r}' for r in prompt_data['dialogue_rules'])
        parts.append(f'대화 규칙:\n{rules}')
    if prompt_data.get('safety_constraints'):
        constraints = '\n'.join(f'- {c}' for c in prompt_data['safety_constraints'])
        parts.append(f'안전 규칙:\n{constraints}')
    return '\n\n'.join(parts)


def _classify_emotion(history: list[dict], user_content: str) -> str | None:
    system = (
        "다음 대화를 읽고 사용자의 주요 감정 상태를 아래 4가지 중 하나로만 출력하세요.\n"
        "출력 형식: encourage / sad / angry / plan 중 하나\n\n"
        "- encourage: 인정받고 싶거나 잘하고 있다는 확인이 필요한 상태\n"
        "- sad: 슬프거나 속상하거나 울고 싶은 상태\n"
        "- angry: 화나거나 억울하거나 분한 상태\n"
        "- plan: 해결책이나 다음 행동을 원하는 상태"
    )
    context = '\n'.join(
        f"{'사용자' if m['role'] == 'user' else '캐릭터'}: {m['content']}"
        for m in history
    )
    context += f'\n사용자: {user_content}'

    resp = _client().chat.completions.create(
        model=GROQ_MODEL,
        messages=[
            {'role': 'system', 'content': system},
            {'role': 'user', 'content': f'대화:\n{context}'},
        ],
        max_tokens=10,
        temperature=0,
    )
    label = resp.choices[0].message.content.strip().lower()
    return label if label in ('encourage', 'sad', 'angry', 'plan') else None


# ── 세션 목록 ───────────────────────────────────────────────
@api_view(['GET'])
@permission_classes([AllowAny])
def session_list(request):
    user = request.user if request.user.is_authenticated else None
    sessions = ChatSession.objects.filter(user=user, is_secret=False)
    return Response(ChatSessionSerializer(sessions, many=True).data)


# ── 세션 생성 ───────────────────────────────────────────────
@api_view(['POST'])
@permission_classes([AllowAny])
def create_session(request):
    character = request.data.get('character', 'haeon')
    is_secret = bool(request.data.get('is_secret', False))

    if character not in VALID_CHARACTERS:
        return Response({'error': '유효하지 않은 캐릭터입니다.'}, status=status.HTTP_400_BAD_REQUEST)

    user = request.user if request.user.is_authenticated else None
    session = ChatSession.objects.create(user=user, character=character, is_secret=is_secret)
    return Response(ChatSessionSerializer(session).data, status=status.HTTP_201_CREATED)


# ── 메시지 전송 ─────────────────────────────────────────────
@api_view(['POST'])
@permission_classes([AllowAny])
def send_message(request, session_id):
    try:
        session = ChatSession.objects.get(id=session_id)
    except ChatSession.DoesNotExist:
        return Response({'error': '세션을 찾을 수 없습니다.'}, status=status.HTTP_404_NOT_FOUND)

    user_content = request.data.get('content', '').strip()
    if not user_content:
        return Response({'error': '메시지 내용을 입력해주세요.'}, status=status.HTTP_400_BAD_REQUEST)
    if len(user_content) > 300:
        return Response({'error': '메시지는 300자 이내여야 합니다.'}, status=status.HTTP_400_BAD_REQUEST)

    prompt_data = _load_prompt(session.character)
    system_msg = _build_system_message(prompt_data)
    model_cfg = prompt_data.get('model_settings', {})

    recent = list(session.messages.order_by('-created_at')[:20])
    recent.reverse()
    history = [{'role': m.role, 'content': m.content} for m in recent]

    messages = [{'role': 'system', 'content': system_msg}] + history
    messages.append({'role': 'user', 'content': user_content})

    chat_resp = _client().chat.completions.create(
        model=GROQ_MODEL,
        messages=messages,
        max_tokens=model_cfg.get('max_tokens', 250),
        temperature=model_cfg.get('temperature', 0.7),
    )
    assistant_content = chat_resp.choices[0].message.content

    user_turn_count = sum(1 for m in recent if m.role == 'user') + 1
    emotion_label = None
    if user_turn_count >= 4:
        emotion_label = _classify_emotion(history, user_content)

    if not session.is_secret:
        ChatMessage.objects.create(session=session, role='user', content=user_content)
        assistant_msg = ChatMessage.objects.create(
            session=session, role='assistant',
            content=assistant_content, emotion_label=emotion_label,
        )
        return Response(ChatMessageSerializer(assistant_msg).data)

    return Response({
        'id': None, 'role': 'assistant',
        'content': assistant_content,
        'emotion_label': emotion_label,
        'created_at': None,
    })


# ── 힐링 차 추천 ────────────────────────────────────────────
@api_view(['POST'])
@permission_classes([AllowAny])
def recommend_tea(request, session_id):
    try:
        session = ChatSession.objects.get(id=session_id)
    except ChatSession.DoesNotExist:
        return Response({'error': '세션을 찾을 수 없습니다.'}, status=status.HTTP_404_NOT_FOUND)

    recent = list(session.messages.order_by('-created_at')[:10])
    recent.reverse()
    context = '\n'.join(f"{'사용자' if m.role == 'user' else '캐릭터'}: {m.content}" for m in recent)

    system = (
        "당신은 힐링 차 전문가입니다. 대화 내용을 읽고 사용자의 감정 상태에 맞는 차를 추천해주세요.\n"
        "반드시 아래 JSON 형식으로만 응답하세요:\n"
        '{"name": "차 이름", "reason": "추천 이유 (1문장)", "effect": "효능", "emoji": "☕"}'
    )

    resp = _client().chat.completions.create(
        model=GROQ_MODEL,
        messages=[
            {'role': 'system', 'content': system},
            {'role': 'user', 'content': f'대화:\n{context}\n\n위 대화에 맞는 힐링 차를 추천해주세요.'},
        ],
        max_tokens=150,
        temperature=0.7,
    )

    try:
        raw = resp.choices[0].message.content.strip()
        start, end = raw.find('{'), raw.rfind('}') + 1
        tea = json.loads(raw[start:end])
    except Exception:
        tea = {'name': '캐모마일', 'reason': '마음을 편안하게 해줘요.', 'effect': '진정 효과', 'emoji': '🌼'}

    return Response(tea)


# ── BGM 추천 ────────────────────────────────────────────────
@api_view(['POST'])
@permission_classes([AllowAny])
def recommend_bgm(request, session_id):
    try:
        session = ChatSession.objects.get(id=session_id)
    except ChatSession.DoesNotExist:
        return Response({'error': '세션을 찾을 수 없습니다.'}, status=status.HTTP_404_NOT_FOUND)

    recent = list(session.messages.order_by('-created_at')[:10])
    recent.reverse()
    context = '\n'.join(f"{'사용자' if m.role == 'user' else '캐릭터'}: {m.content}" for m in recent)

    system = (
        "당신은 음악 큐레이터입니다. 대화 내용을 읽고 사용자의 감정에 맞는 BGM을 추천해주세요.\n"
        "반드시 아래 JSON 형식으로만 응답하세요:\n"
        '{"title": "곡 제목", "artist": "아티스트", "mood": "분위기 설명 (1문장)", "youtube_query": "유튜브 검색어"}'
    )

    resp = _client().chat.completions.create(
        model=GROQ_MODEL,
        messages=[
            {'role': 'system', 'content': system},
            {'role': 'user', 'content': f'대화:\n{context}\n\n위 대화에 맞는 BGM을 추천해주세요.'},
        ],
        max_tokens=150,
        temperature=0.8,
    )

    try:
        raw = resp.choices[0].message.content.strip()
        start, end = raw.find('{'), raw.rfind('}') + 1
        bgm = json.loads(raw[start:end])
    except Exception:
        bgm = {'title': 'Rainy Day', 'artist': 'Unknown', 'mood': '차분하고 따뜻한 분위기', 'youtube_query': 'relaxing piano music'}

    return Response(bgm)


# ── 추천 질문 생성 ──────────────────────────────────────────
@api_view(['POST'])
@permission_classes([AllowAny])
def suggest_questions(request, session_id):
    try:
        session = ChatSession.objects.get(id=session_id)
    except ChatSession.DoesNotExist:
        return Response({'error': '세션을 찾을 수 없습니다.'}, status=status.HTTP_404_NOT_FOUND)

    recent = list(session.messages.order_by('-created_at')[:6])
    recent.reverse()
    context = '\n'.join(f"{'사용자' if m.role == 'user' else '캐릭터'}: {m.content}" for m in recent)

    system = (
        "당신은 공감 대화 전문가입니다. 대화 흐름을 읽고 사용자가 다음에 할 수 있는 말 3가지를 추천해주세요.\n"
        "짧고 자연스러운 구어체로, 반드시 아래 JSON 형식으로만 응답하세요:\n"
        '{"questions": ["질문1", "질문2", "질문3"]}'
    )

    resp = _client().chat.completions.create(
        model=GROQ_MODEL,
        messages=[
            {'role': 'system', 'content': system},
            {'role': 'user', 'content': f'대화:\n{context}'},
        ],
        max_tokens=150,
        temperature=0.9,
    )

    try:
        raw = resp.choices[0].message.content.strip()
        start, end = raw.find('{'), raw.rfind('}') + 1
        result = json.loads(raw[start:end])
    except Exception:
        result = {'questions': ['오늘 하루 어땠어?', '요즘 제일 힘든 게 뭐야?', '그냥 수다 떨까?']}

    return Response(result)


# ── 이너 카운슬 ─────────────────────────────────────────────
COUNCIL_PERSONAS = {
    'haeon':   ('해온', '위로형 상담사. 공감과 감정 수용 중심. 따뜻하고 포근하게 이야기한다.'),
    'greung':  ('그릉', '직면형 상담사. 현실적이고 날카로운 피드백. CBT 기반으로 이야기한다.'),
    'dalkong': ('달콩', '코칭형 상담사. 긍정적이고 행동 지향적. ACT 기반으로 이야기한다.'),
}

@api_view(['POST'])
@permission_classes([AllowAny])
def inner_council(request, session_id):
    try:
        session = ChatSession.objects.get(id=session_id)
    except ChatSession.DoesNotExist:
        return Response({'error': '세션을 찾을 수 없습니다.'}, status=status.HTTP_404_NOT_FOUND)

    user_input = request.data.get('user_input')
    turn = int(request.data.get('turn', 0))

    if turn >= 3:
        return Response({'error': '최대 3턴을 초과했습니다.'}, status=status.HTTP_400_BAD_REQUEST)

    recent = list(session.messages.order_by('-created_at')[:10])
    recent.reverse()
    context = '\n'.join(f"{'사용자' if m.role == 'user' else '캐릭터'}: {m.content}" for m in recent)
    if user_input:
        context += f'\n[사용자 개입]: {user_input}'

    agent_messages = {}
    client = _client()

    for key, (name, persona) in COUNCIL_PERSONAS.items():
        system = (
            f"당신은 '{name}'입니다. {persona}\n"
            "사용자의 대화 내용을 읽고 당신의 관점에서 2-3문장으로 이야기해주세요.\n"
            "다른 캐릭터의 말을 듣고 있다는 전제로, 자연스럽게 회의에 참여하듯 말하세요."
        )
        resp = client.chat.completions.create(
            model=GROQ_MODEL,
            messages=[
                {'role': 'system', 'content': system},
                {'role': 'user', 'content': f'대화 맥락:\n{context}'},
            ],
            max_tokens=200,
            temperature=0.8,
        )
        agent_messages[key] = resp.choices[0].message.content.strip()

    summary_resp = client.chat.completions.create(
        model=GROQ_MODEL,
        messages=[
            {'role': 'system', 'content': '세 상담사의 의견을 한 문장으로 요약해주세요.'},
            {'role': 'user', 'content': '\n'.join(f'{k}: {v}' for k, v in agent_messages.items())},
        ],
        max_tokens=100,
        temperature=0.5,
    )
    summary = summary_resp.choices[0].message.content.strip()

    return Response({
        'agent_messages': agent_messages,
        'summary': summary,
        'turn': turn + 1,
    })

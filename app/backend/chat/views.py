import json
import os
from pathlib import Path

from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework import status
from openai import OpenAI

from .models import ChatSession, ChatMessage
from .serializers import ChatSessionSerializer, ChatMessageSerializer

PROMPT_DIR = Path(__file__).resolve().parent.parent.parent / 'prompts'

VALID_CHARACTERS = {'haeon', 'greung', 'dalkong'}

# 4턴 이후 감정 분류용 프롬프트 (SCR-003 공감 4모드 자동 분기)
_EMOTION_SYSTEM = (
    "다음 대화를 읽고 사용자의 주요 감정 상태를 아래 4가지 중 하나로만 출력하세요.\n"
    "출력 형식: encourage / sad / angry / plan 중 하나\n\n"
    "- encourage: 인정받고 싶거나 잘하고 있다는 확인이 필요한 상태\n"
    "- sad: 슬프거나 속상하거나 울고 싶은 상태\n"
    "- angry: 화나거나 억울하거나 분한 상태\n"
    "- plan: 해결책이나 다음 행동을 원하는 상태"
)


def _load_prompt(character: str) -> dict:
    with open(PROMPT_DIR / f'{character}_prompt.json', encoding='utf-8') as f:
        return json.load(f)


def _build_system_message(prompt_data: dict) -> str:
    parts = [prompt_data['system_instruction']]
    if prompt_data.get('dialogue_rules'):
        rules = '\n'.join(f'- {r}' for r in prompt_data['dialogue_rules'])
        parts.append(f'대화 규칙:\n{rules}')
    if prompt_data.get('safety_constraints'):
        constraints = '\n'.join(f'- {c}' for c in prompt_data['safety_constraints'])
        parts.append(f'안전 규칙:\n{constraints}')
    return '\n\n'.join(parts)


def _classify_emotion(client: OpenAI, history: list[dict], user_content: str) -> str | None:
    context = '\n'.join(
        f"{'사용자' if m['role'] == 'user' else '캐릭터'}: {m['content']}"
        for m in history
    )
    context += f'\n사용자: {user_content}'

    resp = client.chat.completions.create(
        model='gpt-4o-mini',
        messages=[
            {'role': 'system', 'content': _EMOTION_SYSTEM},
            {'role': 'user', 'content': f'대화:\n{context}'},
        ],
        max_tokens=10,
        temperature=0,
    )
    label = resp.choices[0].message.content.strip().lower()
    return label if label in ('encourage', 'sad', 'angry', 'plan') else None


@api_view(['GET'])
@permission_classes([AllowAny])
def session_list(request):
    user = request.user if request.user.is_authenticated else None
    sessions = ChatSession.objects.filter(user=user, is_secret=False)
    return Response(ChatSessionSerializer(sessions, many=True).data)


@api_view(['POST'])
@permission_classes([AllowAny])
def create_session(request):
    character = request.data.get('character', 'haeon')
    is_secret = bool(request.data.get('is_secret', False))

    if character not in VALID_CHARACTERS:
        return Response({'error': '유효하지 않은 캐릭터입니다.'}, status=status.HTTP_400_BAD_REQUEST)

    user = request.user if request.user.is_authenticated else None
    session = ChatSession.objects.create(
        user=user,
        character=character,
        is_secret=is_secret,
    )
    return Response(ChatSessionSerializer(session).data, status=status.HTTP_201_CREATED)


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

    # 10턴 윈도우 (SCR-003 체크포인트)
    recent = list(session.messages.order_by('-created_at')[:20])
    recent.reverse()
    history = [{'role': m.role, 'content': m.content} for m in recent]

    messages = [{'role': 'system', 'content': system_msg}] + history
    messages.append({'role': 'user', 'content': user_content})

    client = OpenAI(api_key=os.environ.get('OPENAI_API_KEY', ''))

    chat_resp = client.chat.completions.create(
        model='gpt-4o-mini',
        messages=messages,
        max_tokens=model_cfg.get('max_tokens', 250),
        temperature=model_cfg.get('temperature', 0.7),
        presence_penalty=model_cfg.get('presence_penalty', 0.6),
        frequency_penalty=model_cfg.get('frequency_penalty', 0.3),
    )
    assistant_content = chat_resp.choices[0].message.content

    # 4턴 이후 공감 모드 자동 분기 (SCR-003 ⑤)
    user_turn_count = sum(1 for m in recent if m.role == 'user') + 1
    emotion_label = None
    if user_turn_count >= 4:
        emotion_label = _classify_emotion(client, history, user_content)

    # 시크릿챗이면 DB 저장 안 함 (SCR-003-S)
    if not session.is_secret:
        ChatMessage.objects.create(session=session, role='user', content=user_content)
        assistant_msg = ChatMessage.objects.create(
            session=session,
            role='assistant',
            content=assistant_content,
            emotion_label=emotion_label,
        )
        return Response(ChatMessageSerializer(assistant_msg).data, status=status.HTTP_200_OK)

    return Response({
        'id': None,
        'role': 'assistant',
        'content': assistant_content,
        'emotion_label': emotion_label,
        'created_at': None,
    }, status=status.HTTP_200_OK)

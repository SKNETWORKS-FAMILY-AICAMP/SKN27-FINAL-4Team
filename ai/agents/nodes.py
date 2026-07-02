# -*- coding: utf-8 -*-
"""LangGraph 노드 구현 — [개별] LangGraph_흐름도_김한솔.md v6.0 §2 기준.

노드 목록: mbti_check / mbti_save / analysis / load_context /
          joy·sadness·anger·normal_agent / plan_agent(스텁) / resp_prep
콜드스타트와 TTS·저장(비동기)은 그래프 밖(뷰 레이어)에서 처리한다.
"""
from ai.agents.personas import CHARACTER_PERSONAS, EMOTION_AGENT_GUIDES, COMMON_RULES
from ai.agents.state import ChatState

EMOTION_KO2EN = {'기쁨': 'joy', '슬픔': 'sadness', '분노': 'anger', '일반': 'normal'}
VALID_EMOTIONS = ('joy', 'sadness', 'anger', 'normal')


def _llm(temperature: float = 0.7, max_tokens: int = 300):
    """LLM 인스턴스 — 공급자(openai/groq)는 chat/llm.py 에서 .env로 선택."""
    from ai.agents.llm import get_llm
    return get_llm(temperature=temperature, max_tokens=max_tokens)


# ── [MBTI pending 분기] ─────────────────────────────────────

def mbti_check_node(state: ChatState) -> dict:
    """직전 MBTI 질문에 대한 답변인지 LLM으로 판별. (흐름도 MBTICHK)"""
    question = state.get('mbti_question_text', '')
    message = state.get('user_message', '')
    try:
        resp = _llm(temperature=0, max_tokens=5).invoke([
            ('system',
             "사용자에게 다음 질문을 던진 상태입니다:\n"
             f"질문: {question}\n\n"
             "사용자의 메시지가 이 질문에 대한 답변이면 yes, "
             "질문과 무관한 다른 이야기면 no 만 출력하세요."),
            ('user', message),
        ])
        is_answer = 'yes' in resp.content.strip().lower()
    except Exception:
        is_answer = False  # 판별 실패 시 일반 대화로 간주 (안전한 쪽)
    return {'is_mbti_answer': is_answer}


def mbti_save_node(state: ChatState) -> dict:
    """MBTI 답변 처리. 일반 모드: 즉시 저장 / 시크릿 모드: 동의 필요 플래그만 설정.
    (흐름도 SECCHK→ASKSAVE→MBTISAVE, 최종_통합_흐름도 §5)"""
    out = {'mbti_needs_consent': False, 'mbti_saved': False}

    if state.get('session_mode') == 'secret':
        # 저장하지 않고 프론트에 동의 버튼 표시 → POST /api/mbti/consent 에서 저장
        out['mbti_needs_consent'] = True
    elif state.get('user_id'):
        from chat.models import MbtiAnswer
        MbtiAnswer.objects.create(
            user_id=state['user_id'],
            question_code=state.get('mbti_question_code', 'unknown'),
            answer_text=state.get('user_message', ''),
        )
        out['mbti_saved'] = True

    # LLM 확인 응답 생성 (흐름도 MBTIRESP)
    persona = CHARACTER_PERSONAS.get(state.get('character_id', 'pori'), CHARACTER_PERSONAS['pori'])
    try:
        resp = _llm(temperature=0.7, max_tokens=100).invoke([
            ('system',
             f"{persona}\n\n사용자가 방금 성향 질문에 답해줬습니다. "
             "짧게(1~2문장) 고마움을 표현하고 자연스럽게 대화를 이어가는 확인 응답만 하세요."),
            ('user', state.get('user_message', '')),
        ])
        text = resp.content.strip()
    except Exception:
        text = '얘기해줘서 고마워요! 덕분에 조금 더 알아가는 기분이에요.'
    out['final_response'] = text
    return out


# ── [감성분석: KcELECTRA + XGBoost, argmax 확정 분류] ────────

def analysis_node(state: ChatState) -> dict:
    """4감정 확정 분류. 학습 모델 우선, 실패 시 LLM 폴백, 그것도 실패면
    콜드스타트 선택 감정 → normal 순으로 폴백. (흐름도 EMOTION→ROUTE)"""
    message = state.get('user_message', '')
    label = None

    # 1) KcELECTRA + XGBoost (ai/emotion/artifacts)
    try:
        from ai.emotion.emotion_model import predict_emotion
        ko = predict_emotion(message)
        if ko:
            label = EMOTION_KO2EN.get(ko, ko if ko in VALID_EMOTIONS else None)
    except Exception:
        label = None

    # 2) LLM 폴백
    if label not in VALID_EMOTIONS:
        try:
            resp = _llm(temperature=0, max_tokens=5).invoke([
                ('system',
                 "사용자 메시지의 주요 감정을 다음 중 하나로만 출력하세요: "
                 "joy / sadness / anger / normal"),
                ('user', message),
            ])
            cand = resp.content.strip().lower()
            if cand in VALID_EMOTIONS:
                label = cand
        except Exception:
            pass

    # 3) 최종 폴백: 콜드스타트 선택 감정(첫 턴 참고 컨텍스트) → normal
    if label not in VALID_EMOTIONS:
        selected = state.get('selected_emotion')
        label = selected if selected in VALID_EMOTIONS else 'normal'

    return {'emotion_label': label}


# ── [컨텍스트 조회: 라우팅 직후 1회만] ────────────────────────

def load_context_node(state: ChatState) -> dict:
    """최근 N턴 원문 + 장기 요약(user_memory) 1회 조회. 시크릿 모드는 RAM 캐시.
    (흐름도 CTX — 4개 에이전트가 각각 조회하지 않음)"""
    RECENT_N = 10
    history, summary = [], ''

    if state.get('session_mode') == 'secret':
        from chat.secret_cache import get_history
        history = get_history(state['session_id'])[-RECENT_N:]
    else:
        from chat.models import ChatMessage, UserMemory
        recent = list(
            ChatMessage.objects
            .filter(session_id=state['session_id'])
            .order_by('-created_at')[:RECENT_N]
        )
        recent.reverse()
        history = [{'role': m.role, 'content': m.content} for m in recent]
        if state.get('user_id'):
            summary = (
                UserMemory.objects
                .filter(user_id=state['user_id'])
                .values_list('summary_text', flat=True)
                .first()
            ) or ''

    return {'recent_history': history, 'memory_summary': summary}


# ── [감정별 에이전트 4종: 응답 지침 생성] ─────────────────────

def _make_emotion_agent(emotion: str):
    def agent_node(state: ChatState) -> dict:
        return {
            'agent_guide': EMOTION_AGENT_GUIDES[emotion],
            # ⚠️ need_plan 트리거 조건 미확정(최종_통합_흐름도 §3)
            #    현재는 프론트 버튼 기반(POST /api/plan-support)이라 그래프에선 항상 False
            'need_plan': False,
        }
    agent_node.__name__ = f'{emotion}_agent_node'
    return agent_node


joy_agent_node = _make_emotion_agent('joy')
sadness_agent_node = _make_emotion_agent('sadness')
anger_agent_node = _make_emotion_agent('anger')
normal_agent_node = _make_emotion_agent('normal')


# ── [Plan Agent: Tavily 외부 검색 — 스텁] ─────────────────────

def plan_agent_node(state: ChatState) -> dict:
    """need_plan == True 시 Tavily 검색. 트리거 조건 확정 전까지 그래프에선 미사용
    (버튼 기반 /api/plan-support 뷰가 동일 로직 수행)."""
    from chat.plan_service import tavily_search
    query = state.get('user_message', '')
    return {'search_context': tavily_search(query)}


# ── [최종 응답 생성] ─────────────────────────────────────────

# eleven_v3 오디오 태그 연기 지시 (공식 프롬프팅 가이드 기반)
# 태그는 TTS 전용 — 화면 표시 전에 views에서 제거된다.
TTS_ACTING_RULES = (
    "[음성 연기 지시 — 태그는 화면에 안 보이고 목소리 연기에만 쓰입니다]\n"
    "- 응답 문장 사이 자연스러운 위치에 아래 태그 중 0~2개만 삽입하세요 (과용 금지):\n"
    "  [sighs](한숨) [laughs](웃음) [whispers](속삭임) [excited](들뜸) [curious](궁금)\n"
    "- 위로할 땐 문장 앞에 [sighs], 축하할 땐 [laughs] 처럼 감정 흐름에 맞게.\n"
    "- 호흡이 필요한 곳엔 말줄임표(…)를 쓰세요. 차분한 일상 대화면 태그를 안 써도 됩니다."
)


def resp_prep_node(state: ChatState) -> dict:
    """페르소나 + 감정 지침 + 컨텍스트(요약/최근 N턴) + 검색 결과 종합 → 최종 응답.
    (흐름도 RESP)"""
    persona = CHARACTER_PERSONAS.get(state.get('character_id', 'pori'), CHARACTER_PERSONAS['pori'])
    guide = state.get('agent_guide', EMOTION_AGENT_GUIDES['normal'])

    system_parts = [persona, guide, COMMON_RULES, TTS_ACTING_RULES]
    if state.get('memory_summary'):
        system_parts.append(f"[사용자에 대한 기억 요약]\n{state['memory_summary']}")
    if state.get('search_context'):
        system_parts.append(f"[외부 검색 결과 — 필요 시 자연스럽게 반영]\n{state['search_context']}")

    messages = [('system', '\n\n'.join(system_parts))]
    for m in state.get('recent_history', []):
        role = 'assistant' if m['role'] == 'assistant' else 'user'
        messages.append((role, m['content']))
    messages.append(('user', state.get('user_message', '')))

    try:
        resp = _llm(temperature=0.7, max_tokens=300).invoke(messages)
        text = resp.content.strip()
    except Exception as e:
        print(f'[resp_prep_node] LLM 실패: {e}')
        text = '지금 잠깐 생각이 꼬였어요. 한 번만 다시 말해줄래요?'

    return {'final_response': text}

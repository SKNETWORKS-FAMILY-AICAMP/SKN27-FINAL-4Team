# -*- coding: utf-8 -*-
"""LangGraph 노드 구현 — [개별] LangGraph_흐름도_김한솔.md v6.0 §2 기준.

노드 목록: mbti_check / mbti_save / analysis / load_context /
          joy·sadness·anger·normal_agent / resp_prep
콜드스타트와 TTS·저장(비동기)은 그래프 밖(뷰 레이어)에서 처리한다.
"""
from ai.agents.personas import EMOTION_AGENT_GUIDES, COMMON_RULES
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
    """MBTI 답변 저장 — 일반 모드 전용.
    (시크릿은 완전 무저장 원칙으로 MBTI 질문 자체를 안 하므로 이 노드에 오지 않음)"""
    out = {'mbti_saved': False}

    if state.get('session_mode') != 'secret' and state.get('user_id'):
        from chat.models import MbtiAnswer
        MbtiAnswer.objects.create(
            user_id=state['user_id'],
            question_code=state.get('mbti_question_code', 'unknown'),
            answer_text=state.get('user_message', ''),
        )
        out['mbti_saved'] = True

    # LLM 확인 응답 생성 (흐름도 MBTIRESP)
    try:
        resp = _llm(temperature=0.7, max_tokens=100).invoke([
            ('system',
             f"{COMMON_RULES}\n\n사용자가 방금 성향 질문에 답해줬습니다. "
             "짧게(1~2문장) 고마움을 표현하고 자연스럽게 대화를 이어가는 확인 응답만 하세요."),
            ('user', state.get('user_message', '')),
        ])
        text = resp.content.strip()
    except Exception:
        text = '얘기해줘서 고마워! 덕분에 너를 조금 더 알아가는 기분이야 ㅎㅎ'
    out['final_response'] = text
    return out


# ── [감성분석: KcELECTRA + XGBoost + 확신도 게이트] ──────────

CONF_GATE = 0.70   # 모델 확신이 이 미만이면 '찍지 말고' 문맥 아는 LLM으로 재분류
                   # (0.55→0.70 상향, 2026-07-05 — 파인튜닝 모델 확률 보정: 채팅체 150 스윕에서
                   #  채택률 82.7%·채택분 정확도 0.831, calibrate_gate.py 근거)
SHORT_LEN = 10     # 이 미만의 초단문("응 ㅋㅋ")은 분석 스킵, 직전 감정 유지


def analysis_node(state: ChatState) -> dict:
    """4감정 분류 — 원칙: 애매할 땐 찍지 않는다.
    ① 초단문 → 직전 감정 유지 (감정은 한 턴 만에 급변하지 않음)
    ② 학습 모델 고확신 → 채택
    ③ 저확신/실패 → 최근 대화 문맥을 포함해 LLM 재분류
    ④ 그래도 실패 → 모델 저확신값 → 직전 감정 → normal
    (개선 근거: docs/감정분류_개선실험_계획서 §2-②, 실측 오분류 "김치찌개→anger")"""
    message = (state.get('user_message') or '').strip()
    prev = state.get('prev_emotion')

    # ① 초단문 바이패스
    if len(message) < SHORT_LEN and prev in VALID_EMOTIONS:
        return {'emotion_label': prev, 'emotion_source': 'short_bypass'}

    # ② 학습 모델 + 확신도
    label, conf = None, None
    try:
        from ai.emotion.emotion_model import predict_emotion_with_confidence
        ko, conf = predict_emotion_with_confidence(message)
        if ko:
            label = EMOTION_KO2EN.get(ko, ko if ko in VALID_EMOTIONS else None)
    except Exception:
        label = None

    if label in VALID_EMOTIONS and (conf is None or conf >= CONF_GATE):
        return {'emotion_label': label, 'emotion_source': 'model'}

    # ③ 문맥 포함 LLM 재분류 (load_context가 먼저 실행돼 recent_history 사용 가능)
    try:
        history = state.get('recent_history', [])[-6:]
        context = '\n'.join(
            f"{'사용자' if m['role'] == 'user' else '챗봇'}: {m['content']}" for m in history)
        resp = _llm(temperature=0, max_tokens=5).invoke([
            ('system',
             "최근 대화 흐름을 참고해, 사용자의 '마지막 메시지'에 담긴 감정을 "
             "다음 중 하나로만 출력하세요: joy / sadness / anger / normal\n"
             "메시지 자체가 중립이면 대화 흐름의 감정을 따르지 말고 normal을 고르세요."),
            ('user', f"[최근 대화]\n{context}\n\n[마지막 메시지]\n{message}"),
        ])
        cand = resp.content.strip().lower()
        if cand in VALID_EMOTIONS:
            return {'emotion_label': cand, 'emotion_source': 'llm_context'}
    except Exception:
        pass

    # ④ 최종 폴백: 모델 저확신값 → 직전 감정 → 콜드스타트 선택 → normal
    for fb in (label, prev, state.get('selected_emotion')):
        if fb in VALID_EMOTIONS:
            return {'emotion_label': fb, 'emotion_source': 'fallback'}
    return {'emotion_label': 'normal', 'emotion_source': 'fallback'}


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
        return {'agent_guide': EMOTION_AGENT_GUIDES[emotion]}
    agent_node.__name__ = f'{emotion}_agent_node'
    return agent_node


joy_agent_node = _make_emotion_agent('joy')
sadness_agent_node = _make_emotion_agent('sadness')
anger_agent_node = _make_emotion_agent('anger')
normal_agent_node = _make_emotion_agent('normal')


# (Plan Agent(Tavily 장소 추천)는 기능 폐기로 제거 — 2026-07-05)


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
    """감정 지침 + 공통 규칙 + 컨텍스트(요약/최근 N턴) + 검색 결과 종합 → 최종 응답.
    캐릭터는 이미지·목소리로만 구분 — 프롬프트는 캐릭터 무관 공통. (흐름도 RESP)"""
    guide = state.get('agent_guide', EMOTION_AGENT_GUIDES['normal'])

    system_parts = [guide, COMMON_RULES, TTS_ACTING_RULES]
    if state.get('memory_summary'):
        system_parts.append(f"[사용자에 대한 기억 요약]\n{state['memory_summary']}")

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

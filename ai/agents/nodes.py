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
        question_code = state.get('mbti_question_code', 'unknown')
        answer_text   = state.get('user_message', '')
        user_id       = state['user_id']

        # 1. 기존 chat 테이블 저장 — 챗봇 중복 질문 방지용 (유지)
        from chat.models import MbtiAnswer
        MbtiAnswer.objects.create(
            user_id=user_id,
            question_code=question_code,
            answer_text=answer_text,
        )
        out['mbti_saved'] = True

        # 2. MBTI 파이프라인 테이블 연동 저장 (월간 리포트 분석 원천)
        #    실패해도 챗봇 대화가 끊기지 않도록 예외를 잡아둔다.
        try:
            from django.utils.timezone import now as tz_now
            from mbti.models import MbtiQuestionResponse
            from ai.agents.mbti import question_text as mbti_question_text

            current_time = tz_now()
            # 코드 앞 2글자가 target_axis (예: 'IE_1' → 'IE')
            target_axis = question_code[:2] if len(question_code) >= 2 else 'unknown'

            MbtiQuestionResponse.objects.create(
                user_id=user_id,
                conversation_id=state.get('session_id'),      # 챗봇 세션 ID 매핑
                question_text=mbti_question_text(question_code),
                answer_text=answer_text,
                target_axis=target_axis,
                period_key=current_time.strftime('%Y-%m'),    # 예: '2026-07'
                answered_at=current_time,
                created_at=current_time,
            )
        except Exception as e:
            print(f'[mbti_save_node] MbtiQuestionResponse 연동 저장 실패 (무시): {e}')

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


def _describe_image(image_url: str) -> tuple:
    """사진을 '한 줄 캡션 + 4감정'으로 한 번에 분석 (비전 호출 1회).
    반환 (caption, emotion). 캡션은 저장·리포트·기억용, 감정은 표정·톤용.
    실패 시 ('', 'normal'). 감정은 뚜렷하지 않으면 normal(오독 방지)."""
    try:
        from langchain_core.messages import HumanMessage, SystemMessage
        resp = _llm(temperature=0, max_tokens=80).invoke([
            SystemMessage(content=(
                "사진을 분석해 아래 두 줄 형식으로만 출력하세요.\n"
                "caption: <장면을 사실 위주로 한국어 한 줄. 분위기는 과하게 해석하지 말 것>\n"
                "emotion: <joy | sadness | anger | normal 중 하나. 뚜렷하지 않으면 normal>")),
            HumanMessage(content=[
                {'type': 'text', 'text': '이 사진을 분석해줘.'},
                {'type': 'image_url', 'image_url': {'url': image_url, 'detail': 'low'}},
            ]),
        ])
        caption, emotion = '', 'normal'
        for line in resp.content.strip().splitlines():
            low = line.strip().lower()
            if low.startswith('caption:'):
                caption = line.split(':', 1)[1].strip()
            elif low.startswith('emotion:'):
                e = line.split(':', 1)[1].strip().lower()
                if e in VALID_EMOTIONS:
                    emotion = e
        return caption, emotion
    except Exception as e:
        print(f'[analysis_node] 사진 분석 실패(normal): {e}')
        return '', 'normal'


def _text_emotion(state: ChatState) -> dict:
    """텍스트 기반 4감정 분류 — 원칙: 애매할 땐 찍지 않는다.
    ① 초단문 → 직전 감정 유지 ② 학습 모델 고확신 → 채택
    ③ 저확신/실패 → 문맥 LLM 재분류 ④ 그래도 실패 → 저확신값 → 직전 → normal."""
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


def analysis_node(state: ChatState) -> dict:
    """4감정 분류 (흐름도 EMOTION) — 글 우선 + 사진 보완(방법 3).
    · 글이 확신 있게 '감정적'이면 글 채택 (사람이 말로 표현한 게 우선)
    · 글이 밍밍/없는데 사진이 있으면 사진 감정으로 메꿈 (애매하면 normal)
    하류(캐릭터 표정·TTS·마음리포트)는 emotion_label을 그대로 소비하므로 추가 배선 불필요."""
    image_url = state.get('image_data_url')
    if not image_url:
        return _text_emotion(state)   # 텍스트 전용 — 기존 흐름 그대로

    # ── 사진이 있는 턴 ──
    message = (state.get('user_message') or '').strip()

    # 캡션+감정을 한 번에 확보 (캡션은 글 감정이 이기든 지든 항상 저장·리포트용으로 남긴다)
    caption, img_emotion = _describe_image(image_url)
    out = {'image_caption': caption} if caption else {}

    # 1) 글이 확신 있게 '감정적(non-normal)'이면 글이 이긴다 (라벨만)
    if message:
        label, conf = None, None
        try:
            from ai.emotion.emotion_model import predict_emotion_with_confidence
            ko, conf = predict_emotion_with_confidence(message)
            if ko:
                label = EMOTION_KO2EN.get(ko, ko if ko in VALID_EMOTIONS else None)
        except Exception:
            label = None
        if label in VALID_EMOTIONS and label != 'normal' and (conf is None or conf >= CONF_GATE):
            return {**out, 'emotion_label': label, 'emotion_source': 'model'}

    # 2) 글이 밍밍/없음 → 사진 감정으로 메꿈
    if img_emotion in VALID_EMOTIONS and img_emotion != 'normal':
        return {**out, 'emotion_label': img_emotion, 'emotion_source': 'image'}
    return {**out, 'emotion_label': 'normal', 'emotion_source': 'image_normal'}


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
            # 그래프(구조화 관계) 기억 병행 회상 — Neo4j 미설정 시 '' 이라 영향 없음
            try:
                from chat.graph_memory import recall as graph_recall
                g = graph_recall(state['user_id'])
                if g:
                    summary = (summary + '\n\n[관계 기억]\n' + g).strip()
            except Exception:
                pass

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
    캐릭터는 이미지·목소리로만 구분 — 프롬프트는 캐릭터 무관 공통. (흐름도 RESP)
    사진 첨부 시 멀티모달 메시지로 전달 → 친구처럼 사진에 반응(MVP · 비전 지원 모델 필요)."""
    guide = state.get('agent_guide', EMOTION_AGENT_GUIDES['normal'])

    system_parts = [guide, COMMON_RULES, TTS_ACTING_RULES]
    if state.get('memory_summary'):
        system_parts.append(f"[사용자에 대한 기억 요약]\n{state['memory_summary']}")

    image_url = state.get('image_data_url')
    if image_url:
        system_parts.append(
            "[사진 반응] 사용자가 방금 사진을 보냈어. 사진을 직접 본 것처럼 친구답게 자연스럽게 "
            "반응해줘 — 뭐가 보이는지 가볍게 짚고 궁금한 걸 되물어도 좋아. 사진을 설명·분석하듯 "
            "딱딱하게 말하지 말고 반말로 짧게. "
            "단, 사용자의 '말'과 '사진 분위기'가 서로 다르게 느껴지면(예: 말은 신나는데 사진은 슬퍼 보임), "
            "사진을 말에 억지로 맞추지 말고 친구처럼 부드럽게 확인해줘 "
            "(예: '오 좋은 일 있었구나! 근데 사진은 좀 슬퍼 보이는데, 무슨 사진이야?').")

    messages = [('system', '\n\n'.join(system_parts))]
    for m in state.get('recent_history', []):
        role = 'assistant' if m['role'] == 'assistant' else 'user'
        messages.append((role, m['content']))

    if image_url:
        from langchain_core.messages import HumanMessage
        txt = (state.get('user_message') or '').strip()
        messages.append(HumanMessage(content=[
            {'type': 'text', 'text': txt or '(사진만 보냈어)'},
            {'type': 'image_url', 'image_url': {'url': image_url, 'detail': 'low'}},
        ]))
    else:
        messages.append(('user', state.get('user_message', '')))

    try:
        resp = _llm(temperature=0.7, max_tokens=300).invoke(messages)
        text = resp.content.strip()
    except Exception as e:
        print(f'[resp_prep_node] LLM 실패: {e}')
        text = '지금 잠깐 생각이 꼬였어요. 한 번만 다시 말해줄래요?'

    return {'final_response': text}

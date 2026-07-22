# -*- coding: utf-8 -*-
"""LangGraph 노드 구현 — [개별] LangGraph_흐름도_김한솔.md v6.0 §2 기준.

노드 목록: mbti_check / mbti_save / analysis / load_context /
          joy·sadness·anger·normal_agent / resp_prep
콜드스타트와 TTS·저장(비동기)은 그래프 밖(뷰 레이어)에서 처리한다.
"""
import os
import re

from ai.agents.personas import CRISIS_GUIDE, EMOTION_AGENT_GUIDES, COMMON_RULES
from ai.agents.state import ChatState

EMOTION_KO2EN = {'기쁨': 'joy', '슬픔': 'sadness', '분노': 'anger', '일반': 'normal'}
VALID_EMOTIONS = ('joy', 'sadness', 'anger', 'normal')

# ── 위기 감지 1차 룰 (2026-07-10 심사위원 피드백) ─────────────
# recall 우선 — 과탐지는 2차 LLM 확인이 거른다.
# '죽겠다' 단독은 관용구(힘들어 죽겠다/배고파 죽겠다)가 많아 제외, '죽고 싶다' 계열만 매칭.
_CRISIS_PATTERNS = [re.compile(p) for p in (
    r'죽\s*고\s*싶', r'죽어\s*버리', r'죽을래', r'죽어야\s*겠',
    r'자살', r'자해', r'유서',
    r'살\s*기\s*싫', r'살고\s*싶지\s*않', r'그만\s*살',
    r'사라지고\s*싶', r'없어지고\s*싶',
    r'다\s*끝내\s*(버리)?고\s*싶', r'끝내\s*버리고\s*싶',
    r'손목\s*(을|에)?\s*(긋|그어)', r'목\s*을?\s*매\s*(고|달|려)',
    r'뛰어\s*내리고\s*싶',
)]


def _crisis_check(message: str, history: list) -> bool:
    """위기 신호 2단 감지: ① 룰 매칭(빠름·recall 우선) ② LLM 맥락 확인(관용구·타인 얘기 구분).
    룰에 걸린 상태에서 LLM 확인이 실패하면 위기로 간주(안전 우선)."""
    if not message or not any(p.search(message) for p in _CRISIS_PATTERNS):
        return False
    try:
        context = '\n'.join(
            f"{'사용자' if m['role'] == 'user' else '챗봇'}: {m['content']}"
            for m in (history or [])[-4:])
        resp = _llm(temperature=0, max_tokens=5).invoke([
            ('system',
             "사용자의 마지막 메시지가 자살·자해 등 '본인의 실제 위기 신호'인지 판단하세요.\n"
             "과장·관용 표현(예: '힘들어 죽겠다', '웃겨 죽을래')이거나 "
             "영화·게임·뉴스·타인 이야기면 no, 본인의 위기 신호로 보이면 yes만 출력하세요.\n"
             "애매하면 yes를 출력하세요(안전 우선)."),
            ('user', f"[최근 대화]\n{context}\n\n[마지막 메시지]\n{message}"),
        ])
        return 'yes' in resp.content.strip().lower()
    except Exception:
        return True   # 룰에 걸렸는데 확인 불가 → 안전 우선


def _llm(temperature: float = 0.7, max_tokens: int = 300):
    """LLM 인스턴스 — 공급자(openai/groq)는 chat/llm.py 에서 .env로 선택."""
    from ai.agents.llm import get_llm
    return get_llm(temperature=temperature, max_tokens=max_tokens)


def _mbti_answer_check_llm(*, max_tokens: int):
    """MBTI 채점 계열과 같은 OpenAI 모델을 쓰는 짧은 의미 판별기.

    일반 대화용 Groq 추론 모델은 짧은 yes/no 작업에서도 reasoning 토큰을
    과도하게 쓰거나 명확한 답변을 no로 오분류한 실측 사례가 있어 분리한다.
    """
    from langchain_openai import ChatOpenAI
    from mbti.constants import DEFAULT_OPENAI_SCORING_MODEL

    model = (
        os.environ.get('MBTI_ANSWER_CHECK_MODEL')
        or os.environ.get('MBTI_OPENAI_SCORING_MODEL')
        or DEFAULT_OPENAI_SCORING_MODEL
    )
    return ChatOpenAI(
        model=model,
        temperature=0,
        max_tokens=max_tokens,
        max_retries=0,
    )


# ── [MBTI pending 분기] ─────────────────────────────────────

def mbti_check_node(state: ChatState) -> dict:
    """직전 MBTI 질문에 대한 답변인지 LLM으로 판별. (흐름도 MBTICHK)"""
    question = state.get('mbti_question_text', '')
    message = state.get('user_message', '')
    try:
        max_tokens = int(os.environ.get('MBTI_ANSWER_CHECK_MAX_TOKENS', '128'))
        resp = _mbti_answer_check_llm(max_tokens=max_tokens).invoke([
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
            from ai.agents.mbti import question_text as fallback_question_text

            current_time = tz_now()
            # 코드 앞 2글자가 target_axis (예: 'IE_1' → 'IE')
            target_axis = question_code[:2] if len(question_code) >= 2 else 'unknown'
            # 사용자가 실제로 본 동적 질문을 그대로 저장해야 채점 근거와 화면이
            # 일치한다. 과거 세션처럼 상태에 문장이 없을 때만 고정 문항을 쓴다.
            asked_question_text = (
                state.get('mbti_question_text')
                or fallback_question_text(question_code)
            )

            MbtiQuestionResponse.objects.create(
                user_id=user_id,
                conversation_id=state.get('session_id'),      # 챗봇 세션 ID 매핑
                question_text=asked_question_text,
                answer_text=answer_text,
                target_axis=target_axis,
                period_key=current_time.strftime('%Y-%m'),    # 예: '2026-07'
                answered_at=current_time,
                created_at=current_time,
            )
        except Exception as e:
            print(f'[mbti_save_node] MbtiQuestionResponse 연동 저장 실패 (무시): {e}')

    # LLM 확인 응답 생성 (흐름도 MBTIRESP)
    fallback_ack = '얘기해줘서 고마워! 덕분에 너를 조금 더 알아가는 기분이야 ㅎㅎ'
    try:
        max_tokens = int(os.environ.get('MBTI_ANSWER_ACK_MAX_TOKENS', '256'))
        resp = _llm(temperature=0.7, max_tokens=max_tokens).invoke([
            ('system',
             f"{COMMON_RULES}\n\n사용자가 방금 성향 질문에 답해줬습니다. "
             "짧게(1~2문장) 고마움을 표현하고 자연스럽게 대화를 이어가는 확인 응답만 하세요."),
            ('user', state.get('user_message', '')),
        ])
        text = resp.content.strip() or fallback_ack
    except Exception:
        text = fallback_ack
    out['final_response'] = text
    return out


# ── [감성분석: KcELECTRA + XGBoost + 확신도 게이트] ──────────

# 감정 게이트 다이얼 — env 오버라이드 가능 (일원화 2026-07-19, 기본값은 실측 채택치)
CONF_GATE = float(os.environ.get('EMO_CONF_GATE', '0.70'))
                   # 모델 확신이 이 미만이면 '찍지 말고' 문맥 아는 LLM으로 재분류
                   # (0.55→0.70 상향, 2026-07-05 — 파인튜닝 모델 확률 보정: 채팅체 150 스윕에서
                   #  채택률 82.7%·채택분 정확도 0.831, calibrate_gate.py 근거)
SHORT_LEN = int(os.environ.get('EMO_SHORT_LEN', '10'))
                   # 이 미만의 초단문("응 ㅋㅋ")은 원칙적으로 직전 감정 유지
SHORT_OVERRIDE = float(os.environ.get('EMO_SHORT_OVERRIDE', '0.90'))
                   # 단, 초단문이어도 모델 확신이 이 이상이면 감정 급변 반영
                   # ("짜증나!" 4자 → 표정 안 바뀌던 문제 보정, 2026-07-09)
# (복합 감정은 절 분할 방식으로 감지 — _split_contrast/_clause_emotions 참고.
#  분포 기반 SECONDARY_MIN 방식은 파인튜닝 모델 과확신(뒤 절 0.96~0.999) 실측으로 폐기, 2026-07-10)


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


_CONTRAST_SPLIT = re.compile(
    r',?\s*(?:그런데|근데|하지만|그렇지만|그래도)\s*'
    r'|(?<=는데)[,\s]+|(?<=은데)[,\s]+|(?<=지만)[,\s]+')


def _split_contrast(message: str):
    """대조 연결어 기준 절 분할 (2026-07-10 실측 재설계).
    파인튜닝 모델이 복합 문장에서 뒤 절 감정에 0.99로 과확신하는 문제 실측 →
    분포 기반 감지 폐기, 절을 쪼개 '모델이 잘하는 단일 감정 문제 2개'로 변환.
    유효하면 (앞절, 뒷절), 아니면 None."""
    parts = [p.strip() for p in _CONTRAST_SPLIT.split(message) if p and p.strip()]
    if len(parts) < 2:
        return None
    a, b = parts[0], parts[-1]
    if len(a) < 4 or len(b) < 4:
        return None
    return a, b


CLAUSE_CONF_MIN = float(os.environ.get('EMO_CLAUSE_CONF_MIN', '0.30'))
                   # 절 분류 확신도 하한 (실측: "팀장한테 혼나서 열받았는데" 0.38)


def _clause_emotions(a: str, b: str):
    """절 2개를 각각 분류 — (앞절 한글라벨|None, 뒷절 한글라벨|None). 로컬 추론이라 비용 미미."""
    from ai.emotion.emotion_model import predict_emotion_full
    out = []
    for clause in (a, b):
        try:
            ko, conf, _ = predict_emotion_full(clause)
            out.append(ko if ko and (conf is None or conf >= CLAUSE_CONF_MIN) else None)
        except Exception:
            out.append(None)
    return out[0], out[1]


def _llm_mixed_emotion(message: str, history: list, cand_ko: list):
    """복합 감정 LLM 판정 (2026-07-10) — '문장 전체 맥락에서 어느 감정이 더 중대한가'.
    기준: 이별·실직처럼 중대·지속적인 사건의 감정 > 음식·소소한 재미 같은 일시적 감정.
    반환 (primary_en, secondary_en|None). 실패 시 (None, None) → 모델 top1/top2 폴백."""
    try:
        context = '\n'.join(
            f"{'사용자' if m['role'] == 'user' else '챗봇'}: {m['content']}"
            for m in (history or [])[-4:])
        resp = _llm(temperature=0, max_tokens=20).invoke([
            ('system',
             "사용자의 마지막 메시지에 여러 감정이 섞여 있습니다. "
             f"후보 감정: {', '.join(cand_ko)}\n"
             "문장 전체 맥락에서 어떤 감정이 더 '중대하고 오래가는 사건'에서 나왔는지 판단해 "
             "주감정과 부감정을 고르세요.\n"
             "기준: 이별·실직·관계 갈등처럼 중대하고 지속적인 사건의 감정이 주감정입니다. "
             "음식·소소한 재미처럼 일시적인 위로·기분은 부감정입니다.\n"
             "다음 형식으로만 출력: primary: <joy|sadness|anger|normal> / "
             "secondary: <joy|sadness|anger|normal|none>"),
            ('user', f"[최근 대화]\n{context}\n\n[마지막 메시지]\n{message}"),
        ])
        text = resp.content.strip().lower()
        pm = re.search(r'primary\s*:\s*(joy|sadness|anger|normal)', text)
        sm = re.search(r'secondary\s*:\s*(joy|sadness|anger|normal|none)', text)
        p = pm.group(1) if pm else None
        s = sm.group(1) if sm else None
        if s in (p, 'none'):
            s = None
        return p, s
    except Exception:
        return None, None


def _text_emotion(state: ChatState) -> dict:
    """텍스트 기반 4감정 분류 — 원칙: 애매할 땐 찍지 않는다.
    ① 초단문 → 직전 감정 유지 ② 학습 모델 고확신 → 채택
    ③ 저확신/실패 → 문맥 LLM 재분류 ④ 그래도 실패 → 저확신값 → 직전 → normal."""
    message = (state.get('user_message') or '').strip()
    prev = state.get('prev_emotion')

    # ② 학습 모델 + 확신도 + 확률분포 (초단문도 일단 예측 — 로컬 추론이라 비용 미미)
    label, conf, probs, ko = None, None, None, None
    try:
        from ai.emotion.emotion_model import predict_emotion_full
        ko, conf, probs = predict_emotion_full(message)
        if ko:
            label = EMOTION_KO2EN.get(ko, ko if ko in VALID_EMOTIONS else None)
    except Exception:
        label = None

    # ① 초단문 처리 — 단, 모델이 매우 확신하는 감정 초단문("짜증나!" 0.97)은 반영
    #    직전 감정이 없는 첫 턴 초단문("몰라"→분노 0.84 함정)은 모델을 믿지 않고
    #    문맥 LLM 재분류(③)에 위임 — 오프너 질문까지 보고 무기력/심드렁을 구분 (2026-07-10 실측 보정)
    short_cold = False
    if len(message) < SHORT_LEN:
        if label in VALID_EMOTIONS and conf is not None and conf >= SHORT_OVERRIDE and label != 'normal':
            return {'emotion_label': label, 'emotion_source': 'short_override'}
        if prev in VALID_EMOTIONS:
            return {'emotion_label': prev, 'emotion_source': 'short_bypass'}
        short_cold = True   # 첫 턴 초단문 — 아래 모델 게이트 건너뛰고 ③으로

    # ②-1 복합 감정 감지 (2026-07-10 심사위원 피드백 — "이별+빵" · 절 분할 방식)
    #     실측: 파인튜닝 모델은 복합 문장에서 뒤 절 감정에 0.96~0.999로 과확신 →
    #     분포로는 감지 불가. 대조 연결어로 절을 쪼개 각각 분류하고,
    #     절끼리 감정이 다르면 LLM이 '문장 전체 맥락에서 더 중대한 감정'을 주감정으로 판정.
    clauses = _split_contrast(message)
    if clauses:
        ko_a, ko_b = _clause_emotions(*clauses)
        en_a, en_b = EMOTION_KO2EN.get(ko_a or ''), EMOTION_KO2EN.get(ko_b or '')
        # 두 절 모두 분류 성공 + 서로 다른 감정 + 한쪽 이상이 non-normal → 복합
        if (en_a in VALID_EMOTIONS and en_b in VALID_EMOTIONS and en_a != en_b
                and (en_a != 'normal' or en_b != 'normal')):
            p, s = _llm_mixed_emotion(
                message, state.get('recent_history', []), [ko_a, ko_b])
            if p in VALID_EMOTIONS:
                out = {'emotion_label': p, 'emotion_source': 'mixed_llm'}
                if s in VALID_EMOTIONS and s != 'normal':
                    out['emotion_secondary'] = s
                return out
            # LLM 판정 실패 → 부정 감정 우선 휴리스틱 (복합 발화는 대개 '부정 사건 + 소소한 긍정')
            neg = next((e for e in (en_a, en_b) if e in ('sadness', 'anger')), None)
            if neg:
                other = en_b if neg == en_a else en_a
                out = {'emotion_label': neg, 'emotion_source': 'mixed_model'}
                if other != 'normal':
                    out['emotion_secondary'] = other
                return out

    if not short_cold and label in VALID_EMOTIONS and (conf is None or conf >= CONF_GATE):
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
    #    (첫 턴 초단문은 모델값 폴백 제외 — "몰라" 분노 0.84로 도로 찍히는 것 방지)
    for fb in ((None if short_cold else label), prev, state.get('selected_emotion')):
        if fb in VALID_EMOTIONS:
            return {'emotion_label': fb, 'emotion_source': 'fallback'}
    return {'emotion_label': 'normal', 'emotion_source': 'fallback'}


def analysis_node(state: ChatState) -> dict:
    """4감정 분류 (흐름도 EMOTION) — 글 우선 + 사진 보완(방법 3).
    · 위기 신호가 감지되면 최우선: 감정은 슬픔으로 고정(표정·TTS 톤 일관), crisis 에이전트로 라우팅
    · 글이 확신 있게 '감정적'이면 글 채택 (사람이 말로 표현한 게 우선)
    · 글이 밍밍/없는데 사진이 있으면 사진 감정으로 메꿈 (애매하면 normal)
    하류(캐릭터 표정·TTS·마음리포트)는 emotion_label을 그대로 소비하므로 추가 배선 불필요."""
    # ── 위기 감지 (다른 모든 분류보다 우선, 2026-07-10) ──
    if _crisis_check((state.get('user_message') or '').strip(),
                     state.get('recent_history', [])):
        return {'emotion_label': 'sadness', 'emotion_source': 'crisis', 'crisis': True}

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
    """최근 N턴 원문 + 그래프 기억(recall) 1회 조회. 시크릿 모드는 RAM 캐시.
    (흐름도 CTX — 4개 에이전트가 각각 조회하지 않음)"""
    RECENT_N = 10   # 다이얼 장부: chat/memory_config.py 51행에 위치 기록됨
    history, summary = [], ''

    if state.get('session_mode') == 'secret':
        from chat.secret_cache import get_history
        history = get_history(state['session_id'])[-RECENT_N:]
    else:
        from chat.models import ChatMessage
        recent = list(
            ChatMessage.objects
            .filter(session_id=state['session_id'])
            .order_by('-created_at')[:RECENT_N]
        )
        recent.reverse()
        history = [{'role': m.role, 'content': m.content} for m in recent]
        if state.get('user_id'):
            # 장기 기억 = 그래프 단독 (2026-07-16 요약 계층 은퇴 — 주입 차단).
            # user_memory 요약은 더 이상 챗봇에 주입하지 않음. 생성은 유지(마음리포트·opener 사용).
            # 근거: 27종 평가 96%는 그래프 recall 단독 수치 + 요약 주입발 사고 이력(위기 재인용 등).
            # Neo4j 미설정/장애 시 '' — 최근 N턴 원문만으로 동작 (무중단).
            try:
                from chat.memory_backend import recall as graph_recall   # v1/v2 스위치 경유
                g = graph_recall(state['user_id'],
                                 message=state.get('user_message'))   # 재강화: 언급된 기억만 강화
                if g:
                    summary = '[관계 기억]\n' + g
            except Exception as e:
                # 2026-07-21: 여기가 조용히 pass였다. 그래프 recall이 깨져도 예외가 삼켜져
                # '기억 못 하는 정상 대화'로 보였고, 로그도 안 남아 발견이 불가능했다.
                # 제품의 핵심 기능이 무증상으로 죽는 상태 → 대화는 계속하되 반드시 남긴다.
                print(f'[load_context] 그래프 recall 실패(기억 없이 진행): '
                      f'{type(e).__name__}: {e}')

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


def crisis_agent_node(state: ChatState) -> dict:
    """위기 대응 에이전트 (2026-07-10) — 슬픔 톤 위에 위기 지침을 최우선으로 얹는다.
    이번 턴은 깊은 위로에만 집중. (기관 안내·플래그 저장·이력 기록은 범위 제외 — 팀 결정)"""
    return {'agent_guide': CRISIS_GUIDE + '\n\n' + EMOTION_AGENT_GUIDES['sadness']}


# (Plan Agent(Tavily 장소 추천)는 기능 폐기로 제거 — 2026-07-05)


# ── [최종 응답 생성] ─────────────────────────────────────────

# eleven_v3 오디오 태그 연기 지시 (공식 프롬프팅 가이드 기반)
# 태그는 TTS 전용 — 화면 표시 전에 views에서 제거된다.
TTS_ACTING_RULES = (
    "[음성 연기 지시 — 태그는 화면에 안 보이고 목소리 연기에만 쓰입니다]\n"
    "- 기쁨/슬픔/분노가 실린 응답이면 문장 사이 자연스러운 위치에 태그를 반드시 1~2개 넣으세요:\n"
    "  기쁨: [excited] [laughs] · 슬픔: [sighs] [sad] · 화나는 얘기에 공감: [frustrated] [sighs]\n"
    "  그 외: [whispers](비밀 얘기) [curious](궁금할 때)\n"
    "- 위로할 땐 문장 앞에 [sighs], 축하할 땐 [excited] 처럼 감정 흐름에 맞게.\n"
    "- 호흡이 필요한 곳엔 말줄임표(…)를 쓰세요. 담담한 일상 대화만 태그 없이 갑니다."
)


def resp_prep_node(state: ChatState) -> dict:
    """감정 지침 + 공통 규칙 + 컨텍스트(요약/최근 N턴) + 검색 결과 종합 → 최종 응답.
    캐릭터는 이미지·목소리로만 구분 — 프롬프트는 캐릭터 무관 공통. (흐름도 RESP)
    사진 첨부 시 멀티모달 메시지로 전달 → 친구처럼 사진에 반응(MVP · 비전 지원 모델 필요)."""
    guide = state.get('agent_guide', EMOTION_AGENT_GUIDES['normal'])

    system_parts = [guide, COMMON_RULES, TTS_ACTING_RULES]
    if state.get('memory_summary'):
        system_parts.append(f"[사용자에 대한 기억 요약]\n{state['memory_summary']}")

    # 복합 감정 (2026-07-10): 주감정 먼저 충분히, 부감정도 한 문장 인정, 무거운 것 → 가벼운 것 순서
    secondary = state.get('emotion_secondary')
    if secondary:
        _ko = {'joy': '기쁨', 'sadness': '슬픔', 'anger': '분노', 'normal': '일반'}
        system_parts.append(
            f"[감정 분석] 주감정: {_ko.get(state.get('emotion_label'), '일반')} / "
            f"부감정: {_ko.get(secondary, secondary)}\n"
            "- 지금 친구 마음엔 두 감정이 섞여 있어. 주감정을 먼저 충분히 공감해주고, "
            "부감정도 꼭 한 문장으로 인정해줘 (무시하면 서운해함).\n"
            "- 순서는 무거운 감정 먼저, 가벼운·긍정 쪽으로 마무리해서 회복 방향으로 닫아줘.")

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
        # 접지 검증 (2026-07-14): 근거 없는 '전에 말했잖아' 단정 차단 — R02·F02 실측 결함.
        # 게이트 통과(대부분) 시 비용 0, 위반 시에만 1회 재생성.
        from ai.agents.answer_guard import check_grounded, retry_instruction
        evidence_parts = []
        if state.get('memory_summary'):
            evidence_parts.append(state['memory_summary'])
        for m in state.get('recent_history', [])[-6:]:
            evidence_parts.append(f"{m['role']}: {m['content']}")
        evidence = '\n'.join(evidence_parts)
        for attempt in (1, 2):   # 재생성도 재검사 — 1차가 또 어기면 2차는 초강수 (2026-07-14)
            ok, offending = check_grounded(text, evidence, state.get('user_message', ''),
                                           crisis_turn=bool(state.get('crisis')))
            if ok:
                break
            retry_messages = [('system', '\n\n'.join(system_parts)
                               + '\n\n' + retry_instruction(offending, attempt))] + messages[1:]
            resp = _llm(temperature=0.3 if attempt >= 2 else 0.5, max_tokens=300).invoke(retry_messages)
            text = resp.content.strip() or text
    except Exception as e:
        print(f'[resp_prep_node] LLM 실패: {e}')
        text = '지금 잠깐 생각이 꼬였어요. 한 번만 다시 말해줄래요?'

    return {'final_response': text}

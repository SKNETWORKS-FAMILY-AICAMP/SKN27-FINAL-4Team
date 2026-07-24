from __future__ import annotations

from dataclasses import dataclass
import json
import os
from typing import Any, Mapping, Protocol, Sequence

from mindreport.constants import (
    MINDREPORT_LLM_TEMPERATURE,
    MINDREPORT_NARRATIVE_MAX_TOKENS,
    MINDREPORT_NARRATIVE_MODEL,
)
from mindreport.services.alternatives import AlternativePlanResult
from mindreport.services.cause_keywords import CauseKeywordResult, LabelDisplayResult
from mindreport.services.emotion_flow import EmotionFlowResult
from mindreport.services.scoring import (
    EmotionScore,
    ReportSourceMessage,
    _extract_json_object,
)


@dataclass(frozen=True)
class SuggestionCard:
    title: str
    reason: str
    how: str
    source_candidate: str
    related_cause: str = ''
    timing: str = 'routine'


@dataclass(frozen=True)
class MindReportNarrative:
    analysis_sentences: tuple[str, ...]
    action_recommendations: tuple[str, ...]
    suggestion_cards: tuple[SuggestionCard, ...] = ()
    title: str = '이번 기록에서 발견한 작은 단서'
    summary: str = ''


@dataclass(frozen=True)
class MindReportNarrativeResult:
    status: str
    narrative: MindReportNarrative | None
    message: str


class NarrativeClient(Protocol):
    def generate_narrative(self, *, payload: Mapping[str, Any]) -> Mapping[str, Any]:
        ...


def build_narrative_payload(
    *,
    source_messages: Sequence[ReportSourceMessage],
    emotion_scores: Sequence[EmotionScore],
    emotion_flow: EmotionFlowResult,
    alternative_plan: AlternativePlanResult,
    cause_result: CauseKeywordResult,
    label_result: LabelDisplayResult,
    recipient_name: str,
    ltm_context: str | None = None,
    report_context: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    # Internal scores select useful context, but are never exposed to the writer.
    dominant_emotion_state = None
    if emotion_flow.daily_summaries:
        highest_count = max(emotion_flow.state_counts.values(), default=0)
        dominant_candidates = {
            state
            for state, count in emotion_flow.state_counts.items()
            if count == highest_count
        }
        dominant_emotion_state = next(
            (
                summary.emotion_state
                for summary in reversed(emotion_flow.daily_summaries)
                if summary.emotion_state in dominant_candidates
            ),
            None,
        )
    support_directions = {
        'negative': '힘들었던 감정을 가볍게 넘기지 말고 인정하며 차분한 위로와 지지를 건넨다.',
        'neutral': '이어온 노력과 버틴 시간을 알아주며 부담스럽지 않은 격려를 건넨다.',
        'positive': '따뜻하거나 기뻤던 흐름을 함께 기뻐하며 그 힘을 이어갈 수 있도록 응원한다.',
    }
    payload = {
        'task': 'mind_report_analysis_and_action_generation',
        'report_context': dict(report_context or {}),
        'editorial_guidance': {
            'action_direction': emotion_flow.action_direction,
            'suggestions': list(emotion_flow.suggestions),
            'support_message': {
                'recipient_name': recipient_name,
                'dominant_emotion_state': dominant_emotion_state,
                'writing_direction': support_directions.get(
                    dominant_emotion_state,
                    '기록의 주된 감정 맥락을 살펴 위로, 격려, 응원 중 가장 자연스러운 말을 건넨다.',
                ),
                'use_as_private_writing_context_only': True,
            },
            'use_as_private_writing_context_only': True,
        },
        'alternative_plan': {
            'action_direction': alternative_plan.action_direction,
            'candidates': [
                {
                    'title': candidate.title,
                    'category': candidate.category,
                    'priority': candidate.priority,
                    'rationale': candidate.rationale,
                }
                for candidate in alternative_plan.candidates
            ],
        },
        'cause_keywords': [
            {
                'keyword': keyword.keyword,
                'cause_type': keyword.cause_type,
                'evidence_message_ids': list(keyword.evidence_message_ids),
                'evidence_dates': list(keyword.evidence_dates),
                'rationale': keyword.rationale,
                'moment_description': keyword.moment_description,
            }
            for keyword in cause_result.cause_keywords
        ],
        'cause_context': {
            'stress_report': cause_result.stress_report,
            'relief_report': cause_result.relief_report,
            'role': 'validated context from the cause agent; use it to personalize actions without making new cause claims',
        },
        'cause_evidence_status': (
            'supported_causes_found'
            if cause_result.cause_keywords
            else 'no_supported_causes'
        ),
        'display_keywords': list(label_result.labels),
        'evidence_messages': [
            {
                'message_id': message.message_id,
                'source_date': message.source_date.isoformat(),
                'content': message.content,
            }
            for message in source_messages
        ],
        'constraints': [
            '의학적 진단, 위험도, 성격 판정을 하지 않는다.',
            '입력된 분석 결과와 근거 메시지 밖의 사실을 만들지 않는다.',
            '점수, 백분율, 긍정·부정·중립 상태, 상승·하락·유지·변동 같은 내부 분류를 절대 언급하지 않는다.',
            '현재 상태를 확정하거나 예단하지 않고, 기록에서 관찰된 말과 상황을 가능성의 언어로 연결한다.',
            '당신은 또는 현재 상태는 같은 판정형 문장을 사용하지 않는다.',
            '대화 원문을 따옴표로 직접 인용하거나 그대로 복사하지 않고, 맥락을 훼손하지 않는 간접화법으로 요약한다.',
            '기록에서 보인 표현을 언급할 때는 ~에 관한 이야기가 이어졌어요, ~이 부담으로 작용했을 수 있어요처럼 관찰과 가능성을 구분한다.',
            '제목과 요약은 내부 분석 용어 없이 기록의 구체적인 주제를 자연스럽게 담는다.',
            '상단 요약은 핵심 맥락만 담은 35~80자 한 문장으로 작성하고 자세한 설명은 분석 문단으로 보낸다.',
            '분석은 실제 대화의 주제, 반복 맥락, 부담 또는 도움이 된 장면, 서로 연결되는 이유를 충분히 설명한다.',
            '마지막 분석 문단의 두 번째 문장은 화면의 "당신에게 한마디"로 사용된다. 반드시 이번 기록의 구체적인 맥락과 editorial_guidance.support_message의 주된 감정 방향을 반영한다.',
            '당신에게 한마디는 editorial_guidance.support_message.recipient_name을 문장에 정확히 한 번 넣어 사용자를 직접 부르고, "당신"이라는 표현은 사용하지 않는다.',
            '호명 뒤에는 주된 감정에 따라 위로·격려·응원 중 가장 자연스러운 역할을 선택한다.',
            '당신에게 한마디는 20~60자의 따뜻한 해요체 한 문장으로 쓰며 행동을 지시하거나 근거 없이 잘될 것이라고 낙관하지 않는다.',
            'cause_evidence_status가 no_supported_causes이면 원인을 새로 만들거나 특정 소재를 원인으로 단정하지 않는다.',
            '분석 문단은 2~3개 작성하고 각 문단은 2문장으로 구성한다. 전체 글 분량이 너무 길어지지 않게 간결하고 핵심적인 사실 위주로 작성한다.',
            '치료나 심리상담 형태의 지시적 조언을 철저히 배제하고, 사용자가 스스로 자신의 생각과 장기 기억을 되돌아보며 스스로를 발견하고 이해할 수 있도록 돕는 "자기 이해(Self-Understanding)"의 다정한 안내자 톤앤매너를 유지한다.',
            '실천 대안은 일상에서 쉽게, 부담 없이 시작할 수 있는 매우 가벼운 활동(Micro-action)으로 제안한다. 장황하게 설명하지 않고 간결하게 제안한다.',
            '제공되는 ltm_context(장기 기억 사건 및 관련 인물/감정 정보)는 사용자의 삶의 흐름에 관한 중요한 맥락 정보(GraphRAG)이다. ltm_context가 있는 경우 대화 내용과 연계하여 감정 변화의 맥락과 원인을 해석하는 데 중요하게 참고하고, 비어 있는 경우에는 대화 로그의 내용에만 근거하여 자연스럽게 글을 작성한다. 또한 PostgreSQL상의 실시간 기분 점수와 LTM상의 감정이 다를 경우, 이를 인지 부조화나 입체적인 복합 감정(예: 겉으로는 덤덤해 보였지만 내면에는 은근한 부담감이 공존하는 상태)으로 자연스럽게 해석하여 서술한다.',
            '마치 다정한 친구나 친절한 가이드가 말을 건네는 것처럼 친근하고 따뜻한 해요체로 작성한다.',
            '이모지는 문단 전체에서 최대 2개만 사용하고 내용 대신 장식으로 남발하지 않는다.',
            '실천 대안은 무엇을, 언제, 어느 정도로 시작할지 포함해 구체적으로 제안한다.',
            'report_context의 analysis_period_start와 analysis_period_end는 제안의 근거가 된 분석 기간이고, generated_on은 리포트가 실제로 만들어진 날짜다.',
            '작은 제안은 조회한 날짜가 아니라 generated_on에 확정된 내용이며, action_window_start부터 action_window_end까지 이어지는 생활에서 실천하는 것을 전제로 한다.',
            '주간 리포트는 생성 후 7일 안에 한두 번 바로 시도할 수 있는 행동으로, 월간 리포트는 생성 후 4주 동안 무리 없이 반복하거나 단계적으로 이어갈 수 있는 행동으로 조정한다.',
            '실천 대안은 ltm_context에 표시된 사건의 시점을 고려한다. 이미 지나간 과거 사건인 경우, 그 사건을 겪은 나 자신을 되돌아보고 감정을 가볍게 소화하는 "회고(Reflection)"나 좋았던 정서를 음미하는 "여운 음미(Savoring)", 혹은 고생한 나를 돌보는 "자기 위로(Self-Compassion)" 활동으로 제안한다. 다가올 미래 사건인 경우, 가벼운 주의 환기 및 정서적 대비(Soft Distraction) 활동으로 제안한다.',
            '각 실천 대안의 reason과 how는 필요한 경우 두 문장까지 사용할 수 있지만 같은 설명을 반복하거나 배경을 장황하게 늘이지 않는다.',
            '실천 대안은 감정 흐름으로 선정된 alternative_plan.candidates 안의 후보를 반드시 source_candidate로 선택하고 그 방향을 유지한다.',
            '후보를 그대로 복사하지 말고 cause_keywords와 ltm_context를 이용해 현재 기록에 맞는 title, reason, how로 구체화한다.',
            'related_cause는 실제 cause_keywords.keyword 중 직접 관련된 하나만 사용하고 관련 근거가 없으면 빈 문자열로 둔다.',
            'reason은 cause_keywords와 ltm_context에서 확인된 구체적인 상황이나 감정에 영향을 준 맥락을 먼저 드러내고, 그 맥락에 이 활동이 왜 맞는지를 자연스럽게 연결한다. 내부 점수·흐름 분류명은 노출하지 않는다.',
            'how는 cause_keywords의 moment_description, evidence_dates와 cause_context를 참고해 실제 장면 다음에 이어 할 수 있는 행동으로 쓴다.',
            'how의 첫 문장은 "다음 퇴근 후", "다음 회의 10분 전", "잠들기 15분 전"처럼 반복 가능한 실행 계기를 먼저 정하고, 필요한 장소나 준비물이 있으면 하나만 짚은 뒤 첫 동작을 분명한 동사로 안내한다.',
            '과거 리포트를 나중에 다시 읽어도 조회 시점의 지시로 오해되지 않도록 how에 "오늘", "내일", "모레", "이번 주말", "이번 달"처럼 조회 날짜에 따라 의미가 달라지는 표현을 사용하지 않는다.',
            'how에는 몇 분·몇 회·몇 줄처럼 부담 없는 실행량과 어디에서 멈추면 되는지 포함한다. 필요하면 다음 행동을 한 문장 더 덧붙일 수 있지만 여러 선택지를 나열하거나 효과를 반복 설명하지 않는다.',
            '"시간을 내보세요", "가볍게 시작해보세요", "앱을 활용해보세요"처럼 첫 동작을 알 수 없는 추상적인 시작 문구만 쓰지 않는다.',
            'reason과 how는 각각 대체로 30~120자 안에서 작성하고, 구체성에 필요하지 않은 배경 설명은 덜어낸다.',
            'timing은 routine, past_reflection, future_preparation 중 하나만 사용한다. 새로 생성하는 제안에 today는 사용하지 않는다.',
            '서로 비슷한 제안을 반복하지 않고 우선순위가 높은 후보를 중심으로 2~3개만 작성한다.',
            '반드시 유효한 JSON 객체만 반환한다.',
        ],
        'output_schema': {
            'title': '구체적이지만 상태를 판정하지 않는 한국어 제목 1개',
            'summary': '기록의 핵심 맥락만 담은 35~80자 한국어 한 문장',
            'analysis_sentences': ['2 to 3 concise Korean paragraphs, each containing precisely 2 sentences; the final sentence of the final paragraph must be a 20-to-60-character, context-grounded message of comfort, encouragement, or cheering that includes editorial_guidance.support_message.recipient_name exactly once and never uses 당신'],
            'suggestion_cards': [{
                'title': 'short personalized activity title',
                'reason': 'one or two concise Korean sentences connecting a concrete conversation or GraphDB context to why the activity fits, about 30 to 120 characters',
                'how': 'one or two practical Korean sentences beginning with a concrete cue, followed by one clear first action, a small duration or amount, and a stopping point, about 30 to 150 characters',
                'source_candidate': 'exact title from alternative_plan.candidates',
                'related_cause': 'exact keyword from cause_keywords or empty string',
                'timing': 'routine | past_reflection | future_preparation',
            }],
        },
    }
    if ltm_context:
        payload['ltm_context'] = ltm_context
    return payload


class LangChainNarrativeClient:
    def generate_narrative(self, *, payload: Mapping[str, Any]) -> Mapping[str, Any]:
        from langchain_core.messages import SystemMessage
        from langchain_core.prompts import ChatPromptTemplate, HumanMessagePromptTemplate
        from langchain_openai import ChatOpenAI

        prompt = ChatPromptTemplate(
            messages=[
                SystemMessage(
                    content=(
                        '너는 마음리포트의 분석 문장과 실천 대안을 전달하는 다정하고 친절한 가이드다. '
                        '입력된 대화 근거, 원인 후보, 행동 방향만 바탕으로 사용자에게 읽기 쉬운 '
                        '제목, 요약, 충분한 분석 문장과 부담 낮은 실천 대안을 만든다. '
                        '내부 점수나 상태 분류를 드러내지 말고, 사용자의 현재 상태를 확정하지 않는다. '
                        '대화 원문은 직접 인용하지 않고 관찰된 맥락을 간접화법으로 풀어 쓴다. '
                        '분석 문장에서는 맥락과 연결 이유를 충분히 설명하고, 실천 대안은 원인 에이전트가 정리한 날짜와 장면을 받아 '
                        '실행 시점, 첫 동작, 작은 실행량, 멈출 기준이 실제로 보이게 쓴다. 다만 같은 설명을 반복하거나 선택지를 길게 나열하지 않는다. '
                        '새 원인 판단이나 진단을 하지 말고 JSON 객체만 반환한다.'
                    )
                ),
                HumanMessagePromptTemplate.from_template('{narrative_payload}'),
            ]
        )
        llm = ChatOpenAI(
            model=MINDREPORT_NARRATIVE_MODEL,
            temperature=MINDREPORT_LLM_TEMPERATURE,
            max_tokens=MINDREPORT_NARRATIVE_MAX_TOKENS,
        )
        message = (prompt | llm).invoke(
            {'narrative_payload': json.dumps(payload, ensure_ascii=False)}
        )
        content = message.content
        if isinstance(content, list):
            content = ''.join(
                str(item.get('text', item)) if isinstance(item, dict) else str(item)
                for item in content
            )
        return _extract_json_object(str(content))


def _parse_string_list(value: Any, *, limit: int) -> tuple[str, ...]:
    if not isinstance(value, list):
        return ()

    parsed = []
    for item in value:
        text = str(item or '').strip()
        if text:
            parsed.append(text)
        if len(parsed) >= limit:
            break
    return tuple(parsed)


def _parse_suggestion_cards(
    value: Any,
    *,
    allowed_candidates: set[str],
    allowed_causes: set[str],
) -> tuple[SuggestionCard, ...]:
    if not isinstance(value, list):
        return ()

    cards = []
    seen_titles = set()
    allowed_timings = {'today', 'routine', 'past_reflection', 'future_preparation'}
    for item in value:
        if not isinstance(item, Mapping):
            continue
        title = ' '.join(str(item.get('title') or '').split()).strip()
        reason = ' '.join(str(item.get('reason') or '').split()).strip()
        how = ' '.join(str(item.get('how') or '').split()).strip()
        source_candidate = str(item.get('source_candidate') or '').strip()
        related_cause = str(item.get('related_cause') or '').strip()
        timing = str(item.get('timing') or 'routine').strip()
        normalized_title = ''.join(title.split())
        if (
            not 2 <= len(title) <= 40
            or not 25 <= len(reason) <= 130
            or not 25 <= len(how) <= 150
            or source_candidate not in allowed_candidates
            or (related_cause and related_cause not in allowed_causes)
            or timing not in allowed_timings
            or normalized_title in seen_titles
        ):
            continue
        seen_titles.add(normalized_title)
        cards.append(SuggestionCard(
            title=title,
            reason=reason,
            how=how,
            source_candidate=source_candidate,
            related_cause=related_cause,
            timing=timing,
        ))
        if len(cards) >= 3:
            break
    return tuple(cards)


def parse_narrative(
    payload: Mapping[str, Any],
    *,
    alternative_plan: AlternativePlanResult | None = None,
    cause_result: CauseKeywordResult | None = None,
) -> MindReportNarrative:
    analysis_sentences = _parse_string_list(
        payload.get('analysis_sentences'),
        limit=4,
    )
    title = str(payload.get('title') or '').strip()
    summary = str(payload.get('summary') or '').strip()
    resolved_summary = summary or (
        analysis_sentences[0] if analysis_sentences else ''
    )
    suggestion_cards = _parse_suggestion_cards(
        payload.get('suggestion_cards'),
        allowed_candidates={
            candidate.title for candidate in alternative_plan.candidates
        } if alternative_plan else set(),
        allowed_causes={
            keyword.keyword for keyword in cause_result.cause_keywords
        } if cause_result else set(),
    )
    legacy_recommendations = _parse_string_list(
        payload.get('action_recommendations'),
        limit=4,
    )
    recommendations = (
        tuple(f'{card.reason} {card.how}'.strip() for card in suggestion_cards)
        or legacy_recommendations
    )
    return MindReportNarrative(
        analysis_sentences=analysis_sentences,
        action_recommendations=recommendations,
        suggestion_cards=suggestion_cards,
        title=title or '이번 기록에서 발견한 작은 단서',
        summary=resolved_summary,
    )


class MindReportNarrativeGenerator:
    def __init__(self, narrative_client: NarrativeClient | None = None):
        self.narrative_client = narrative_client

    def run(
        self,
        *,
        source_messages: Sequence[ReportSourceMessage],
        emotion_scores: Sequence[EmotionScore],
        emotion_flow: EmotionFlowResult,
        alternative_plan: AlternativePlanResult,
        cause_result: CauseKeywordResult,
        label_result: LabelDisplayResult,
        recipient_name: str,
        revision_instructions: Sequence[str] = (),
        ltm_context: str | None = None,
        report_context: Mapping[str, Any] | None = None,
    ) -> MindReportNarrativeResult:
        if not source_messages or not emotion_scores:
            return MindReportNarrativeResult(
                status='insufficient_data',
                narrative=None,
                message='분석 근거 문장과 실천 대안을 생성할 근거가 부족합니다.',
            )

        client = self.narrative_client
        if client is None and os.getenv('OPENAI_API_KEY'):
            client = LangChainNarrativeClient()

        if client is None:
            return MindReportNarrativeResult(
                status='narrative_client_unavailable',
                narrative=None,
                message='분석 근거 문장화와 실천 대안 생성 클라이언트가 설정되지 않았습니다.',
            )

        narrative_payload = build_narrative_payload(
            source_messages=source_messages,
            emotion_scores=emotion_scores,
            emotion_flow=emotion_flow,
            alternative_plan=alternative_plan,
            cause_result=cause_result,
            label_result=label_result,
            recipient_name=recipient_name,
            ltm_context=ltm_context,
            report_context=report_context,
        )
        if revision_instructions:
            narrative_payload['revision_instructions'] = list(revision_instructions)
        narrative = parse_narrative(
            client.generate_narrative(payload=narrative_payload),
            alternative_plan=alternative_plan,
            cause_result=cause_result,
        )
        if not narrative.analysis_sentences or not narrative.action_recommendations:
            return MindReportNarrativeResult(
                status='invalid_output',
                narrative=None,
                message='분석 근거 문장 또는 실천 대안 생성 결과가 비어 있습니다.',
            )

        return MindReportNarrativeResult(
            status='generated',
            narrative=narrative,
            message='분석 근거 문장화와 실천 대안 생성을 완료했습니다.',
        )

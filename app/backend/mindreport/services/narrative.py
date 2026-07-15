from __future__ import annotations

from dataclasses import dataclass
import json
import os
from typing import Any, Mapping, Protocol, Sequence

from mindreport.services.alternatives import AlternativePlanResult
from mindreport.services.cause_keywords import CauseKeywordResult, LabelDisplayResult
from mindreport.services.emotion_flow import EmotionFlowResult
from mindreport.services.scoring import (
    EmotionScore,
    ReportSourceMessage,
    _extract_json_object,
)


@dataclass(frozen=True)
class MindReportNarrative:
    analysis_sentences: tuple[str, ...]
    action_recommendations: tuple[str, ...]
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
) -> dict[str, Any]:
    # Internal scores select useful context, but are never exposed to the writer.
    return {
        'task': 'mind_report_analysis_and_action_generation',
        'editorial_guidance': {
            'action_direction': emotion_flow.action_direction,
            'suggestions': list(emotion_flow.suggestions),
            'use_as_private_writing_context_only': True,
        },
        'alternative_plan': {
            'action_direction': alternative_plan.action_direction,
            'candidates': [
                {
                    'title': candidate.title,
                    'category': candidate.category,
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
            }
            for keyword in cause_result.cause_keywords
        ],
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
            'cause_evidence_status가 no_supported_causes이면 원인을 새로 만들거나 특정 소재를 원인으로 단정하지 않는다.',
            '분석 문단은 3개 이상 작성하고 각 문단은 2~3문장으로 구성한다.',
            '첫 문단은 주요 맥락, 둘째 문단은 부담과 도움이 된 요소의 관계, 셋째 문단은 일상에서 살펴볼 단서를 다룬다.',
            '마치 다정한 친구나 친절한 가이드가 말을 건네는 것처럼 친근하고 따뜻한 해요체로 작성한다.',
            '이모지는 문단 전체에서 최대 2개만 사용하고 내용 대신 장식으로 남발하지 않는다.',
            '실천 대안은 무엇을, 언제, 어느 정도로 시작할지 포함해 구체적으로 제안한다.',
            '각 실천 대안은 추천 이유와 바로 시작할 수 있는 작은 방법을 2문장 이상으로 설명한다.',
            '실천 대안은 alternative_plan.candidates 안의 후보를 우선 사용한다.',
            '반드시 유효한 JSON 객체만 반환한다.',
        ],
        'output_schema': {
            'title': '구체적이지만 상태를 판정하지 않는 한국어 제목 1개',
            'summary': '기록의 핵심 맥락만 담은 35~80자 한국어 한 문장',
            'analysis_sentences': ['3 to 4 substantial Korean paragraphs, each containing 2 to 3 sentences'],
            'action_recommendations': ['2 to 3 concrete Korean action paragraphs, each containing a reason and a small starting method'],
        },
    }


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
                        '짧은 조언으로 끝내지 말고 맥락, 연결 이유, 살펴볼 단서와 구체적인 시작 방법까지 충분히 설명한다. '
                        '새 원인 판단이나 진단을 하지 말고 JSON 객체만 반환한다.'
                    )
                ),
                HumanMessagePromptTemplate.from_template('{narrative_payload}'),
            ]
        )
        llm = ChatOpenAI(
            model=os.getenv('MINDREPORT_NARRATIVE_MODEL', 'gpt-5.4-mini'),
            temperature=0,
            max_tokens=1200,
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


def parse_narrative(payload: Mapping[str, Any]) -> MindReportNarrative:
    analysis_sentences = _parse_string_list(
        payload.get('analysis_sentences'),
        limit=4,
    )
    title = str(payload.get('title') or '').strip()
    summary = str(payload.get('summary') or '').strip()
    return MindReportNarrative(
        analysis_sentences=analysis_sentences,
        action_recommendations=_parse_string_list(
            payload.get('action_recommendations'),
            limit=4,
        ),
        title=title or '이번 기록에서 발견한 작은 단서',
        summary=summary or (analysis_sentences[0] if analysis_sentences else ''),
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
        revision_instructions: Sequence[str] = (),
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
        )
        if revision_instructions:
            narrative_payload['revision_instructions'] = list(revision_instructions)
        narrative = parse_narrative(
            client.generate_narrative(payload=narrative_payload)
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

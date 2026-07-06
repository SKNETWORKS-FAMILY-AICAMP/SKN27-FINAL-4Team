from __future__ import annotations

from dataclasses import dataclass
import json
import os
from typing import Any, Mapping, Protocol, Sequence

from mindreport.services.alternatives import AlternativePlanResult, alternative_plan_to_payload
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
    score_by_date = {score.source_date.isoformat(): score for score in emotion_scores}
    # LLM is responsible only for wording; upstream analysis decides causes and labels.
    return {
        'task': 'mind_report_analysis_and_action_generation',
        'emotion_flow': {
            'flow_type': emotion_flow.flow_type,
            'maintenance_type': emotion_flow.maintenance_type,
            'tone_color': emotion_flow.tone_color,
            'title': emotion_flow.title,
            'interpretation': emotion_flow.interpretation,
            'action_direction': emotion_flow.action_direction,
            'suggestions': list(emotion_flow.suggestions),
        },
        'alternative_plan': alternative_plan_to_payload(alternative_plan),
        'cause_keywords': [
            {
                'keyword': keyword.keyword,
                'cause_type': keyword.cause_type,
                'confidence': keyword.confidence,
                'evidence_message_ids': list(keyword.evidence_message_ids),
                'evidence_dates': list(keyword.evidence_dates),
                'rationale': keyword.rationale,
            }
            for keyword in cause_result.cause_keywords
        ],
        'label_display': {
            'emotion_flow_type': label_result.policy.emotion_flow_type,
            'stress_label_size': label_result.policy.stress_label_size,
            'relief_label_size': label_result.policy.relief_label_size,
            'labels': list(label_result.labels),
        },
        'daily_scores': [
            {
                'source_date': score.source_date.isoformat(),
                'emotion_label': score.emotion_label,
                'emotion_state': score.emotion_state,
                'emotion_score': score.emotion_score,
                'confidence': score.confidence,
                'emotional_evidence_count': score.emotional_evidence_count,
                'total_message_count': score.total_message_count,
                'evidence_message_ids': list(score.evidence_message_ids),
                'rationale': score.rationale,
            }
            for score in emotion_scores
        ],
        'evidence_messages': [
            {
                'message_id': message.message_id,
                'source_date': message.source_date.isoformat(),
                'content': message.content,
                'daily_emotion_state': score_by_date.get(
                    message.source_date.isoformat()
                ).emotion_state
                if score_by_date.get(message.source_date.isoformat())
                else None,
                'daily_emotion_score': score_by_date.get(
                    message.source_date.isoformat()
                ).emotion_score
                if score_by_date.get(message.source_date.isoformat())
                else None,
            }
            for message in source_messages
        ],
        'constraints': [
            '의학적 진단, 위험도, 성격 판정을 하지 않는다.',
            '입력된 분석 결과와 근거 메시지 밖의 사실을 만들지 않는다.',
            '마치 다정한 친구나 친절한 가이드가 말을 건네는 것처럼 이모지(✨, 🎁, 🥺, 📝 등)를 적극 사용하여 친근하고 따뜻한 대화체(해요체)로 작성한다.',
            '실천 대안은 사용자가 바로 해볼 수 있는 짧은 행동으로 다정하게 제안한다.',
            '실천 대안은 alternative_plan.candidates 안의 후보를 우선 사용한다.',
            '반드시 유효한 JSON 객체만 반환한다.',
        ],
        'output_schema': {
            'analysis_sentences': ['2 to 4 concise Korean sentences'],
            'action_recommendations': ['2 to 4 short Korean action suggestions'],
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
                        '입력된 감정 흐름, 원인 키워드, 라벨 정책, 근거 메시지만 바탕으로 '
                        '사용자에게 따뜻하게 공감하며 읽기 쉬운 분석 문장과 부담 낮은 실천 대안을 다정한 말투로 만든다. '
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
    return MindReportNarrative(
        analysis_sentences=_parse_string_list(
            payload.get('analysis_sentences'),
            limit=4,
        ),
        action_recommendations=_parse_string_list(
            payload.get('action_recommendations'),
            limit=4,
        ),
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
    ) -> MindReportNarrativeResult:
        if not source_messages or not emotion_scores or not cause_result.cause_keywords:
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

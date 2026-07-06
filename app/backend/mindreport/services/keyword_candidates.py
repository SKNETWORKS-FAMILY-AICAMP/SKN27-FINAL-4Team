from __future__ import annotations

from dataclasses import dataclass
import json
import os
from typing import Any, Mapping, Protocol, Sequence

from mindreport.services.alternatives import AlternativePlanResult, alternative_plan_to_payload
from mindreport.services.emotion_flow import EmotionFlowResult
from mindreport.services.scoring import EmotionScore, ReportSourceMessage, _extract_json_object


@dataclass(frozen=True)
class KeywordCandidate:
    keyword: str
    confidence: float
    evidence_message_ids: tuple[int, ...]
    evidence_dates: tuple[str, ...]
    rationale: str


@dataclass(frozen=True)
class KeywordCandidateResult:
    status: str
    candidates: tuple[KeywordCandidate, ...]
    message: str


class KeywordCandidateClient(Protocol):
    def extract_candidates(self, *, payload: Mapping[str, Any]) -> Mapping[str, Any]:
        ...


def build_keyword_candidate_payload(
    *,
    source_messages: Sequence[ReportSourceMessage],
    emotion_scores: Sequence[EmotionScore],
    emotion_flow: EmotionFlowResult,
    alternative_plan: AlternativePlanResult,
) -> dict[str, Any]:
    score_by_date = {score.source_date.isoformat(): score for score in emotion_scores}
    # Temporary implementation: LLM extraction stands in for the future embedding model.
    return {
        'task': 'mind_report_keyword_candidate_extraction',
        'emotion_flow': {
            'flow_type': emotion_flow.flow_type,
            'maintenance_type': emotion_flow.maintenance_type,
            'tone_color': emotion_flow.tone_color,
            'title': emotion_flow.title,
            'action_direction': emotion_flow.action_direction,
        },
        'alternative_plan': alternative_plan_to_payload(alternative_plan),
        'daily_scores': [
            {
                'source_date': score.source_date.isoformat(),
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
        'messages': [
            {
                'message_id': message.message_id,
                'source_date': message.source_date.isoformat(),
                'content': message.content,
                'current_emotion_label': message.emotion_label,
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
            '입력 메시지에 없는 사실이나 생활 맥락을 만들지 않는다.',
            '진단, 위험도, 성격 판정을 하지 않는다.',
            '후보 키워드는 짧은 명사구로 작성한다.',
            '반드시 유효한 JSON 객체만 반환한다.',
        ],
        'output_schema': {
            'candidates': [
                {
                    'keyword': 'short Korean noun phrase',
                    'confidence': '0.0 to 1.0',
                    'evidence_message_ids': ['message ids used as evidence'],
                    'rationale': 'short Korean reason',
                }
            ]
        },
    }


class LangChainKeywordCandidateClient:
    def extract_candidates(self, *, payload: Mapping[str, Any]) -> Mapping[str, Any]:
        from langchain_core.messages import SystemMessage
        from langchain_core.prompts import ChatPromptTemplate, HumanMessagePromptTemplate
        from langchain_openai import ChatOpenAI

        prompt = ChatPromptTemplate(
            messages=[
                SystemMessage(
                    content=(
                        '너는 마음리포트의 원인 키워드 후보 추출기다. '
                        '사용자 대화와 감정 점수 근거에서 반복되거나 감정 변화와 가까운 소재를 짧은 키워드 후보로 뽑는다. '
                        '스트레스 원인/이완 원인 분류는 하지 말고 후보만 반환한다. '
                        '입력 근거 밖의 사실을 만들지 말고 JSON 객체만 반환한다.'
                    )
                ),
                HumanMessagePromptTemplate.from_template('{keyword_payload}'),
            ]
        )
        llm = ChatOpenAI(
            model=os.getenv('MINDREPORT_KEYWORD_MODEL', 'gpt-5.4-mini'),
            temperature=0,
            max_tokens=1200,
        )
        message = (prompt | llm).invoke(
            {'keyword_payload': json.dumps(payload, ensure_ascii=False)}
        )
        content = message.content
        if isinstance(content, list):
            content = ''.join(
                str(item.get('text', item)) if isinstance(item, dict) else str(item)
                for item in content
            )
        return _extract_json_object(str(content))


def parse_keyword_candidates(
    *,
    payload: Mapping[str, Any],
    source_messages: Sequence[ReportSourceMessage],
) -> tuple[KeywordCandidate, ...]:
    source_by_id = {message.message_id: message for message in source_messages}
    parsed: list[KeywordCandidate] = []
    seen_keywords: set[str] = set()

    rows = payload.get('candidates', [])
    if not isinstance(rows, list):
        rows = []

    for row in rows:
        if not isinstance(row, Mapping):
            continue

        keyword = str(row.get('keyword') or '').strip()
        if not keyword or keyword in seen_keywords:
            continue

        raw_message_ids = row.get('evidence_message_ids', [])
        if not isinstance(raw_message_ids, list):
            raw_message_ids = []

        evidence_ids = []
        for raw_id in raw_message_ids:
            try:
                message_id = int(raw_id)
            except (TypeError, ValueError):
                continue
            if message_id in source_by_id and message_id not in evidence_ids:
                evidence_ids.append(message_id)

        try:
            confidence = float(row.get('confidence'))
        except (TypeError, ValueError):
            confidence = 0.0
        confidence = max(0.0, min(1.0, confidence))

        seen_keywords.add(keyword)
        parsed.append(
            KeywordCandidate(
                keyword=keyword,
                confidence=confidence,
                evidence_message_ids=tuple(evidence_ids),
                evidence_dates=tuple(
                    source_by_id[message_id].source_date.isoformat()
                    for message_id in evidence_ids
                ),
                rationale=str(row.get('rationale') or ''),
            )
        )

    return tuple(parsed)


class MindReportKeywordExtractor:
    def __init__(self, keyword_client: KeywordCandidateClient | None = None):
        self.keyword_client = keyword_client

    def run(
        self,
        *,
        source_messages: Sequence[ReportSourceMessage],
        emotion_scores: Sequence[EmotionScore],
        emotion_flow: EmotionFlowResult,
        alternative_plan: AlternativePlanResult,
    ) -> KeywordCandidateResult:
        if not source_messages or not emotion_scores:
            return KeywordCandidateResult(
                status='insufficient_data',
                candidates=(),
                message='키워드 후보를 도출할 감정 점수화 결과가 부족합니다.',
            )

        client = self.keyword_client
        if client is None and os.getenv('OPENAI_API_KEY'):
            client = LangChainKeywordCandidateClient()

        if client is None:
            return KeywordCandidateResult(
                status='keyword_client_unavailable',
                candidates=(),
                message='키워드 후보 도출 클라이언트가 설정되지 않았습니다.',
            )

        candidate_payload = build_keyword_candidate_payload(
            source_messages=source_messages,
            emotion_scores=emotion_scores,
            emotion_flow=emotion_flow,
            alternative_plan=alternative_plan,
        )
        candidates = parse_keyword_candidates(
            payload=client.extract_candidates(payload=candidate_payload),
            source_messages=source_messages,
        )
        return KeywordCandidateResult(
            status='extracted',
            candidates=candidates,
            message='LLM을 통해 키워드 후보를 도출했습니다.',
        )

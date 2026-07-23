from __future__ import annotations

from dataclasses import dataclass
import json
import os
from typing import Any, Mapping, Protocol, Sequence

from mindreport.constants import (
    MINDREPORT_KEYWORD_MAX_TOKENS,
    MINDREPORT_KEYWORD_MODEL,
    MINDREPORT_LLM_TEMPERATURE,
)
from mindreport.services.alternatives import AlternativePlanResult
from mindreport.services.collection import LtmEvent, ltm_event_to_payload
from mindreport.services.emotion_flow import EmotionFlowResult
from mindreport.services.scoring import EmotionScore, ReportSourceMessage, _extract_json_object


@dataclass(frozen=True)
class KeywordCandidate:
    keyword: str
    confidence: float
    evidence_message_ids: tuple[int, ...]
    evidence_dates: tuple[str, ...]
    rationale: str
    evidence_type: str = 'unspecified'
    relationship: str = ''
    counter_evidence: tuple[str, ...] = ()
    graph_event_ids: tuple[str, ...] = ()


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
    graph_events: Sequence[LtmEvent] = (),
) -> dict[str, Any]:
    score_by_date = {
        score.source_date: score
        for score in emotion_scores
    }
    return {
        'task': 'mind_report_keyword_candidate_extraction',
        'graph_events': [ltm_event_to_payload(event) for event in graph_events],
        'scoring_context': {
            'role': 'supporting affect context only; never causal evidence by itself',
            'daily_results': [
                {
                    'source_date': score.source_date.isoformat(),
                    'emotion_label': score.emotion_label,
                    'emotion_state': score.emotion_state,
                    'confidence': score.confidence,
                    'scoring_method': score.scoring_method,
                    'evidence_message_ids': list(score.evidence_message_ids),
                }
                for score in emotion_scores
            ],
            'flow_type': emotion_flow.flow_type,
            'trend_eligible': emotion_flow.metrics.get('trend_eligible', False),
        },
        'messages': [
            {
                'message_id': message.message_id,
                'source_date': message.source_date.isoformat(),
                'content': message.content,
                'current_emotion_label': message.emotion_label,
                'model_emotion': (
                    {
                        'label': score_by_date[message.source_date].emotion_label,
                        'state': score_by_date[message.source_date].emotion_state,
                        'confidence': score_by_date[message.source_date].confidence,
                        'scoring_method': score_by_date[
                            message.source_date
                        ].scoring_method,
                    }
                    if message.source_date in score_by_date
                    else None
                ),
            }
            for message in source_messages
        ],
        'constraints': [
            '입력 메시지에 없는 사실이나 생활 맥락을 만들지 않는다.',
            '진단, 위험도, 성격 판정을 하지 않는다.',
            '후보 키워드는 짧은 명사구로 작성한다.',
            '사용자가 해당 소재 때문에 부담 또는 편안함을 느꼈다고 표현했거나, 같은 소재가 여러 메시지에서 비슷한 감정 맥락과 함께 반복된 경우에만 후보로 인정한다.',
            '같은 날짜에 등장했다는 사실만으로 감정 원인 후보로 판단하지 않는다.',
            'KcELECTRA의 일별 감정 라벨과 상태는 후보 탐색을 돕는 보조 정보이며, 원인 관계의 단독 근거로 사용하지 않는다.',
            'graph_events는 대화에서 이미 구조화된 사건 맥락이다. 원문 메시지와 연결이 확인될 때만 후보를 보강하고 일치하는 event_id를 graph_event_ids에 넣는다.',
            'GraphDB에 사건이 존재한다는 사실만으로 감정 원인 후보로 채택하지 않는다.',
            '단순 일정, 장소, 인물, 사물의 언급은 원인 후보가 아니다.',
            '후보 개수를 채우지 말고 충분한 근거가 없으면 candidates를 빈 배열로 반환한다.',
            '반드시 유효한 JSON 객체만 반환한다.',
        ],
        'output_schema': {
            'candidates': [
                {
                    'keyword': 'short Korean noun phrase',
                    'confidence': '0.0 to 1.0',
                    'evidence_message_ids': ['message ids used as evidence'],
                    'evidence_type': 'explicit_causal | repeated_association | before_after_change | insufficient',
                    'relationship': 'how the topic and the user-described affect are connected',
                    'counter_evidence': ['conflicting or weakening context, if any'],
                    'graph_event_ids': ['matching graph event ids; empty when no event matches'],
                    'rationale': 'short Korean reason explaining why this is more than a simple mention',
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
                        '사용자 대화에서 감정에 영향을 주었다고 대화 자체로 뒷받침되는 소재만 짧은 키워드 후보로 뽑는다. '
                        '명시적 인과 표현, 반복된 감정 연관, 행동 전후 변화 중 하나가 있어야 한다. '
                        '같은 날짜에 함께 등장한 것과 단순 언급은 원인 근거가 아니다. '
                        '근거가 없으면 빈 배열을 반환하며 후보 수를 억지로 채우지 않는다. '
                        '스트레스 원인/이완 원인 분류는 하지 말고 후보만 반환한다. '
                        'GraphDB 사건은 대화 원문과 연결되는 경우에만 후보를 구체화하는 보조 근거로 사용하고, '
                        '일치하는 사건 ID를 함께 반환한다. '
                        '입력 근거 밖의 사실을 만들지 말고 JSON 객체만 반환한다.'
                    )
                ),
                HumanMessagePromptTemplate.from_template('{keyword_payload}'),
            ]
        )
        llm = ChatOpenAI(
            model=MINDREPORT_KEYWORD_MODEL,
            temperature=MINDREPORT_LLM_TEMPERATURE,
            max_tokens=MINDREPORT_KEYWORD_MAX_TOKENS,
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
    graph_events: Sequence[LtmEvent] = (),
) -> tuple[KeywordCandidate, ...]:
    source_by_id = {message.message_id: message for message in source_messages}
    parsed: list[KeywordCandidate] = []
    seen_keywords: set[str] = set()
    valid_graph_event_ids = {event.event_id for event in graph_events if event.event_id}

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

        evidence_type = str(row.get('evidence_type') or '').strip().lower()
        if evidence_type not in {
            'explicit_causal',
            'repeated_association',
            'before_after_change',
        } or not evidence_ids:
            continue

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
                evidence_dates=tuple(dict.fromkeys(
                    source_by_id[message_id].source_date.isoformat()
                    for message_id in evidence_ids
                )),
                rationale=str(row.get('rationale') or ''),
                evidence_type=evidence_type,
                relationship=str(row.get('relationship') or ''),
                counter_evidence=tuple(
                    str(item).strip()
                    for item in row.get('counter_evidence', [])
                    if str(item).strip()
                )
                if isinstance(row.get('counter_evidence', []), list)
                else (),
                graph_event_ids=tuple(dict.fromkeys(
                    str(event_id).strip()
                    for event_id in row.get('graph_event_ids', [])
                    if str(event_id).strip() in valid_graph_event_ids
                ))
                if isinstance(row.get('graph_event_ids', []), list)
                else (),
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
        graph_events: Sequence[LtmEvent] = (),
        revision_instructions: Sequence[str] = (),
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
            graph_events=graph_events,
        )
        if revision_instructions:
            candidate_payload['revision_instructions'] = list(revision_instructions)
        candidates = parse_keyword_candidates(
            payload=client.extract_candidates(payload=candidate_payload),
            source_messages=source_messages,
            graph_events=graph_events,
        )
        return KeywordCandidateResult(
            status='extracted' if candidates else 'no_supported_candidates',
            candidates=candidates,
            message='LLM을 통해 근거가 있는 키워드 후보를 도출했습니다.'
            if candidates
            else '대화에서 충분히 뒷받침되는 원인 키워드 후보를 찾지 못했습니다.',
        )

from __future__ import annotations

from dataclasses import dataclass
import json
import os
from typing import Any, Mapping, Protocol, Sequence

from mindreport.constants import (
    FLOW_SCORE_DOWNWARD,
    FLOW_SCORE_MAINTENANCE,
    FLOW_SCORE_UPWARD,
    FLOW_SCORE_VOLATILE,
    MINDREPORT_CAUSE_KEYWORD_MODEL,
    MINDREPORT_CAUSE_MAX_TOKENS,
    MINDREPORT_LLM_TEMPERATURE,
)
from mindreport.services.keyword_candidates import KeywordCandidate
from mindreport.services.emotion_flow import EmotionFlowResult
from mindreport.services.scoring import EmotionScore, ReportSourceMessage, _extract_json_object


CAUSE_STRESS = 'stress'
CAUSE_RELIEF = 'relief'
LABEL_EMPHASIS_PRIMARY = 'primary'
LABEL_EMPHASIS_SECONDARY = 'secondary'


@dataclass(frozen=True)
class CauseKeyword:
    keyword: str
    cause_type: str
    confidence: float
    evidence_message_ids: tuple[int, ...]
    evidence_dates: tuple[str, ...]
    rationale: str
    classified_by: str


@dataclass(frozen=True)
class CauseKeywordResult:
    status: str
    cause_keywords: tuple[CauseKeyword, ...]
    unresolved_candidates: tuple[KeywordCandidate, ...]
    message: str


@dataclass(frozen=True)
class LabelDisplayPolicy:
    emotion_flow_type: str
    stress_emphasis: str
    relief_emphasis: str
    stress_display_weight: float
    relief_display_weight: float
    rationale: str


@dataclass(frozen=True)
class LabelDisplayResult:
    status: str
    policy: LabelDisplayPolicy
    labels: tuple[dict[str, Any], ...]
    message: str


class CauseKeywordClient(Protocol):
    def classify_keywords(self, *, payload: Mapping[str, Any]) -> Mapping[str, Any]:
        ...


def build_cause_keyword_payload(
    *,
    candidates: Sequence[KeywordCandidate],
    emotion_scores: Sequence[EmotionScore],
    emotion_flow: EmotionFlowResult,
    source_messages: Sequence[ReportSourceMessage] = (),
) -> dict[str, Any]:
    source_by_id = {message.message_id: message for message in source_messages}
    return {
        'task': 'mind_report_cause_keyword_classification',
        'scoring_context': {
            'role': 'supporting affect direction only; source text remains primary',
            'flow_type': emotion_flow.flow_type,
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
        },
        'candidates': [
            {
                'keyword': candidate.keyword,
                'candidate_confidence': candidate.confidence,
                'evidence_type': candidate.evidence_type,
                'relationship': candidate.relationship,
                'counter_evidence': list(candidate.counter_evidence),
                'evidence_message_ids': list(candidate.evidence_message_ids),
                'evidence_dates': list(candidate.evidence_dates),
                'evidence_messages': [
                    {
                        'message_id': message_id,
                        'source_date': source_by_id[message_id].source_date.isoformat(),
                        'content': source_by_id[message_id].content,
                    }
                    for message_id in candidate.evidence_message_ids
                    if message_id in source_by_id
                ],
            }
            for candidate in candidates
        ],
        'constraints': [
            '입력 후보 키워드 외의 새 키워드를 만들지 않는다.',
            '진단, 위험도, 성격 판정을 하지 않는다.',
            '후보별 근거 메시지를 직접 다시 읽고 후보 추출 결과에 동조하지 말고 독립적으로 판단한다.',
            '일별 감정 점수나 같은 날짜에 등장했다는 사실을 원인 판정 근거로 사용하지 않는다.',
            'KcELECTRA 감정 결과는 근거 메시지를 해석하는 보조 정보일 뿐이며, stress/relief 판정은 원문에 드러난 방향과 인과 표현으로 결정한다.',
            'stress는 소재가 부담, 긴장, 불편 또는 소진과 연결된 경우에만 사용한다.',
            'relief는 소재가 편안함, 즐거움, 안정 또는 회복과 연결된 경우에만 사용한다.',
            '단순 언급, 혼합된 방향, 불명확한 인과관계는 unresolved로 분류하고 publishable을 false로 반환한다.',
            '모든 후보가 unresolved여도 정상이며 분류 개수를 채우지 않는다.',
            '반드시 유효한 JSON 객체만 반환한다.',
        ],
        'output_schema': {
            'cause_keywords': [
                {
                    'keyword': 'same as input candidate',
                    'cause_type': 'stress | relief | unresolved',
                    'publishable': 'true only when the evidence supports showing this as a cause',
                    'confidence': '0.0 to 1.0',
                    'rationale': 'short Korean evidence-based reason',
                }
            ]
        },
    }


class LangChainCauseKeywordClient:
    def classify_keywords(self, *, payload: Mapping[str, Any]) -> Mapping[str, Any]:
        from langchain_core.messages import SystemMessage
        from langchain_core.prompts import ChatPromptTemplate, HumanMessagePromptTemplate
        from langchain_openai import ChatOpenAI

        prompt = ChatPromptTemplate(
            messages=[
                SystemMessage(
                    content=(
                        '너는 마음리포트의 원인 키워드 분류기다. '
                        '입력된 각 후보의 원본 근거 메시지를 독립적으로 다시 읽고 '
                        '스트레스 원인(stress), 이완 원인(relief), 판단 보류(unresolved) 중 하나로 분류한다. '
                        '단순 동시 등장이나 날짜 단위 점수를 인과 근거로 사용하지 않는다. '
                        '불명확하면 unresolved를 선택하고 publishable을 false로 반환한다. '
                        '모든 후보를 보류하거나 빈 결과를 반환해도 정상이다. '
                        '새 키워드를 만들지 말고 JSON 객체만 반환한다.'
                    )
                ),
                HumanMessagePromptTemplate.from_template('{cause_keyword_payload}'),
            ]
        )
        llm = ChatOpenAI(
            model=MINDREPORT_CAUSE_KEYWORD_MODEL,
            temperature=MINDREPORT_LLM_TEMPERATURE,
            max_tokens=MINDREPORT_CAUSE_MAX_TOKENS,
        )
        message = (prompt | llm).invoke(
            {'cause_keyword_payload': json.dumps(payload, ensure_ascii=False)}
        )
        content = message.content
        if isinstance(content, list):
            content = ''.join(
                str(item.get('text', item)) if isinstance(item, dict) else str(item)
                for item in content
            )
        return _extract_json_object(str(content))


def parse_cause_keywords(
    *,
    payload: Mapping[str, Any],
    candidates: Sequence[KeywordCandidate],
) -> tuple[CauseKeyword, ...]:
    candidate_by_keyword = {candidate.keyword: candidate for candidate in candidates}
    parsed: list[CauseKeyword] = []
    seen_keywords: set[str] = set()

    rows = payload.get('cause_keywords', [])
    if not isinstance(rows, list):
        rows = []

    for row in rows:
        if not isinstance(row, Mapping):
            continue

        keyword = str(row.get('keyword') or '').strip()
        candidate = candidate_by_keyword.get(keyword)
        if candidate is None or keyword in seen_keywords:
            continue

        cause_type = str(row.get('cause_type') or '').strip().lower()
        if cause_type not in {CAUSE_STRESS, CAUSE_RELIEF}:
            continue
        if row.get('publishable') is not True:
            continue

        try:
            confidence = float(row.get('confidence'))
        except (TypeError, ValueError):
            confidence = candidate.confidence
        confidence = round(max(0.0, min(1.0, confidence)), 3)

        seen_keywords.add(keyword)
        parsed.append(
            CauseKeyword(
                keyword=keyword,
                cause_type=cause_type,
                confidence=confidence,
                evidence_message_ids=candidate.evidence_message_ids,
                evidence_dates=candidate.evidence_dates,
                rationale=str(row.get('rationale') or ''),
                classified_by='llm',
            )
        )

    return tuple(parsed)


class MindReportCauseClassifier:
    def __init__(self, cause_client: CauseKeywordClient | None = None):
        self.cause_client = cause_client

    def run(
        self,
        *,
        candidates: Sequence[KeywordCandidate],
        emotion_scores: Sequence[EmotionScore],
        emotion_flow: EmotionFlowResult,
        source_messages: Sequence[ReportSourceMessage] = (),
        revision_instructions: Sequence[str] = (),
    ) -> CauseKeywordResult:
        if not candidates:
            return CauseKeywordResult(
                status='no_supported_causes',
                cause_keywords=(),
                unresolved_candidates=(),
                message='표시할 만큼 충분히 뒷받침되는 원인 키워드가 없습니다.',
            )

        client = self.cause_client
        if client is None and os.getenv('OPENAI_API_KEY'):
            client = LangChainCauseKeywordClient()

        if client is None:
            return CauseKeywordResult(
                status='no_supported_causes',
                cause_keywords=(),
                unresolved_candidates=tuple(candidates),
                message='원인 분류 LLM을 사용할 수 없어 원인 키워드를 표시하지 않습니다.',
            )

        cause_payload = build_cause_keyword_payload(
            candidates=candidates,
            emotion_scores=emotion_scores,
            emotion_flow=emotion_flow,
            source_messages=source_messages,
        )
        if revision_instructions:
            cause_payload['revision_instructions'] = list(revision_instructions)
        llm_keywords = parse_cause_keywords(
            payload=client.classify_keywords(payload=cause_payload),
            candidates=candidates,
        )
        classified_keywords = llm_keywords
        unresolved_by_keyword = {
            keyword.keyword for keyword in candidates
        } - {keyword.keyword for keyword in llm_keywords}
        still_unresolved = tuple(
            candidate for candidate in candidates if candidate.keyword in unresolved_by_keyword
        )

        if not classified_keywords:
            return CauseKeywordResult(
                status='no_supported_causes',
                cause_keywords=(),
                unresolved_candidates=still_unresolved,
                message='LLM 독립 검토에서 표시 가능한 원인 키워드가 확인되지 않았습니다.',
            )

        return CauseKeywordResult(
            status='classified' if not still_unresolved else 'partially_classified',
            cause_keywords=classified_keywords,
            unresolved_candidates=still_unresolved,
            message='원인 키워드 분류를 완료했습니다.',
        )


def determine_label_display_policy(
    *,
    emotion_flow_type: str,
) -> LabelDisplayPolicy:
    if emotion_flow_type == FLOW_SCORE_UPWARD:
        return LabelDisplayPolicy(
            emotion_flow_type=emotion_flow_type,
            stress_emphasis=LABEL_EMPHASIS_SECONDARY,
            relief_emphasis=LABEL_EMPHASIS_PRIMARY,
            stress_display_weight=0.7,
            relief_display_weight=1.0,
            rationale=(
                '점수 상향 흐름은 회복 구간이 있으므로 모든 라벨의 읽기 크기는 '
                '유지하되 이완 원인을 우선 강조하고 스트레스 원인은 보조 강조합니다.'
            ),
        )

    return LabelDisplayPolicy(
        emotion_flow_type=emotion_flow_type,
        stress_emphasis=LABEL_EMPHASIS_PRIMARY,
        relief_emphasis=LABEL_EMPHASIS_PRIMARY,
        stress_display_weight=1.0,
        relief_display_weight=1.0,
        rationale=(
            '점수 유지, 감정 변동성, 점수 하향 흐름은 스트레스 원인과 '
            '이완 원인을 같은 읽기 크기와 강조도로 표시합니다.'
        ),
    )


def apply_label_display_policy(
    *,
    cause_keywords: Sequence[CauseKeyword],
    emotion_flow_type: str,
) -> LabelDisplayResult:
    policy = determine_label_display_policy(emotion_flow_type=emotion_flow_type)
    labels = []

    for keyword in cause_keywords:
        if keyword.cause_type == CAUSE_STRESS:
            emphasis = policy.stress_emphasis
            display_weight = policy.stress_display_weight
        elif keyword.cause_type == CAUSE_RELIEF:
            emphasis = policy.relief_emphasis
            display_weight = policy.relief_display_weight
        else:
            emphasis = LABEL_EMPHASIS_PRIMARY
            display_weight = 1.0

        labels.append(
            {
                'keyword': keyword.keyword,
                'cause_type': keyword.cause_type,
                'emphasis': emphasis,
                'display_weight': display_weight,
                'confidence': keyword.confidence,
                'evidence_message_ids': list(keyword.evidence_message_ids),
                'evidence_dates': list(keyword.evidence_dates),
            }
        )

    return LabelDisplayResult(
        status='applied',
        policy=policy,
        labels=tuple(labels),
        message='감정 흐름 기준으로 라벨 표시 비중을 결정했습니다.',
    )

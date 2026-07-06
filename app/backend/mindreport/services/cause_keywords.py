from __future__ import annotations

from dataclasses import dataclass
import json
import os
from typing import Any, Mapping, Protocol, Sequence

from mindreport.services.keyword_candidates import KeywordCandidate
from mindreport.services.emotion_flow import EmotionFlowResult
from mindreport.services.scoring import EmotionScore, _extract_json_object


CAUSE_STRESS = 'stress'
CAUSE_RELIEF = 'relief'
RULE_THRESHOLD = 10.0

FLOW_SCORE_UPWARD = 'score_upward'
FLOW_SCORE_MAINTENANCE = 'score_maintenance'
FLOW_SCORE_VOLATILE = 'score_volatile'
FLOW_SCORE_DOWNWARD = 'score_downward'

LABEL_SIZE_DEFAULT = 'default'
LABEL_SIZE_COMPACT = 'compact'


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
    stress_label_size: str
    relief_label_size: str
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


def _score_average_for_candidate(
    *,
    candidate: KeywordCandidate,
    score_by_date: Mapping[str, EmotionScore],
) -> float | None:
    scores = [
        score_by_date[evidence_date].emotion_score
        for evidence_date in candidate.evidence_dates
        if evidence_date in score_by_date
    ]
    if not scores:
        return None
    return sum(scores) / len(scores)


def _confidence(candidate_confidence: float, average_score: float) -> float:
    score_weight = min(1.0, abs(average_score - 50.0) / 50.0)
    return round(max(0.0, min(1.0, (candidate_confidence * 0.6) + (score_weight * 0.4))), 3)


def classify_by_score_rule(
    *,
    candidates: Sequence[KeywordCandidate],
    emotion_scores: Sequence[EmotionScore],
) -> tuple[tuple[CauseKeyword, ...], tuple[KeywordCandidate, ...]]:
    score_by_date = {score.source_date.isoformat(): score for score in emotion_scores}
    classified: list[CauseKeyword] = []
    unresolved: list[KeywordCandidate] = []

    for candidate in candidates:
        average_score = _score_average_for_candidate(
            candidate=candidate,
            score_by_date=score_by_date,
        )
        if average_score is None or abs(average_score - 50.0) < RULE_THRESHOLD:
            unresolved.append(candidate)
            continue

        if average_score < 50:
            cause_type = CAUSE_STRESS
            rationale = '근거 메시지의 평균 감정 점수가 부정 구간이라 스트레스 원인으로 분류했습니다.'
        else:
            cause_type = CAUSE_RELIEF
            rationale = '근거 메시지의 평균 감정 점수가 긍정 구간이라 이완 원인으로 분류했습니다.'

        classified.append(
            CauseKeyword(
                keyword=candidate.keyword,
                cause_type=cause_type,
                confidence=_confidence(candidate.confidence, average_score),
                evidence_message_ids=candidate.evidence_message_ids,
                evidence_dates=candidate.evidence_dates,
                rationale=rationale,
                classified_by='score_rule',
            )
        )

    return tuple(classified), tuple(unresolved)


def build_cause_keyword_payload(
    *,
    candidates: Sequence[KeywordCandidate],
    emotion_scores: Sequence[EmotionScore],
    emotion_flow: EmotionFlowResult,
) -> dict[str, Any]:
    score_by_date = {score.source_date.isoformat(): score for score in emotion_scores}
    # Ambiguous candidates fall back to LLM until the future flow model is available.
    return {
        'task': 'mind_report_cause_keyword_classification',
        'emotion_flow': {
            'flow_type': emotion_flow.flow_type,
            'maintenance_type': emotion_flow.maintenance_type,
            'tone_color': emotion_flow.tone_color,
            'title': emotion_flow.title,
            'action_direction': emotion_flow.action_direction,
        },
        'candidates': [
            {
                'keyword': candidate.keyword,
                'candidate_confidence': candidate.confidence,
                'evidence_message_ids': list(candidate.evidence_message_ids),
                'evidence_dates': list(candidate.evidence_dates),
                'evidence_daily_scores': [
                    {
                        'source_date': evidence_date,
                        'emotion_state': score_by_date[evidence_date].emotion_state,
                        'emotion_score': score_by_date[evidence_date].emotion_score,
                        'confidence': score_by_date[evidence_date].confidence,
                    }
                    for evidence_date in candidate.evidence_dates
                    if evidence_date in score_by_date
                ],
            }
            for candidate in candidates
        ],
        'constraints': [
            '입력 후보 키워드 외의 새 키워드를 만들지 않는다.',
            '진단, 위험도, 성격 판정을 하지 않는다.',
            'cause_type은 stress 또는 relief 중 하나만 사용한다.',
            '반드시 유효한 JSON 객체만 반환한다.',
        ],
        'output_schema': {
            'cause_keywords': [
                {
                    'keyword': 'same as input candidate',
                    'cause_type': 'stress | relief',
                    'confidence': '0.0 to 1.0',
                    'rationale': 'short Korean reason',
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
                        '입력된 후보 키워드를 근거 메시지의 감정 점수와 날짜 맥락에 따라 '
                        '스트레스 원인(stress) 또는 이완 원인(relief)으로만 분류한다. '
                        '새 키워드를 만들지 말고 JSON 객체만 반환한다.'
                    )
                ),
                HumanMessagePromptTemplate.from_template('{cause_keyword_payload}'),
            ]
        )
        llm = ChatOpenAI(
            model=os.getenv('MINDREPORT_CAUSE_KEYWORD_MODEL', 'gpt-5.4-mini'),
            temperature=0,
            max_tokens=1000,
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
    ) -> CauseKeywordResult:
        if not candidates or not emotion_scores:
            return CauseKeywordResult(
                status='insufficient_data',
                cause_keywords=(),
                unresolved_candidates=tuple(candidates),
                message='원인 키워드를 분류할 후보 또는 감정 점수 결과가 부족합니다.',
            )

        rule_keywords, unresolved = classify_by_score_rule(
            candidates=candidates,
            emotion_scores=emotion_scores,
        )
        if not unresolved:
            return CauseKeywordResult(
                status='classified',
                cause_keywords=rule_keywords,
                unresolved_candidates=(),
                message='감정 점수 Rule로 원인 키워드를 분류했습니다.',
            )

        client = self.cause_client
        if client is None and os.getenv('OPENAI_API_KEY'):
            client = LangChainCauseKeywordClient()

        if client is None:
            return CauseKeywordResult(
                status='partially_classified' if rule_keywords else 'cause_client_unavailable',
                cause_keywords=rule_keywords,
                unresolved_candidates=unresolved,
                message='Rule로 확정하기 어려운 원인 키워드가 남았지만 LLM 분류 클라이언트가 설정되지 않았습니다.',
            )

        cause_payload = build_cause_keyword_payload(
            candidates=unresolved,
            emotion_scores=emotion_scores,
            emotion_flow=emotion_flow,
        )
        llm_keywords = parse_cause_keywords(
            payload=client.classify_keywords(payload=cause_payload),
            candidates=unresolved,
        )
        classified_keywords = rule_keywords + llm_keywords
        unresolved_by_keyword = {
            keyword.keyword for keyword in unresolved
        } - {keyword.keyword for keyword in llm_keywords}
        still_unresolved = tuple(
            candidate for candidate in unresolved if candidate.keyword in unresolved_by_keyword
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
            stress_label_size=LABEL_SIZE_COMPACT,
            relief_label_size=LABEL_SIZE_DEFAULT,
            stress_display_weight=0.7,
            relief_display_weight=1.0,
            rationale='점수 상향 흐름은 회복 구간이 있으므로 이완 원인 라벨을 기본 크기로 유지하고 스트레스 원인 라벨은 작게 표시합니다.',
        )

    return LabelDisplayPolicy(
        emotion_flow_type=emotion_flow_type,
        stress_label_size=LABEL_SIZE_DEFAULT,
        relief_label_size=LABEL_SIZE_DEFAULT,
        stress_display_weight=1.0,
        relief_display_weight=1.0,
        rationale='점수 유지, 감정 변동성, 점수 하향 흐름은 스트레스 원인과 이완 원인 라벨을 같은 크기로 표시합니다.',
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
            label_size = policy.stress_label_size
            display_weight = policy.stress_display_weight
        elif keyword.cause_type == CAUSE_RELIEF:
            label_size = policy.relief_label_size
            display_weight = policy.relief_display_weight
        else:
            label_size = LABEL_SIZE_DEFAULT
            display_weight = 1.0

        labels.append(
            {
                'keyword': keyword.keyword,
                'cause_type': keyword.cause_type,
                'label_size': label_size,
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

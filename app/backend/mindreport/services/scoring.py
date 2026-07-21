from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timedelta
import json
import os
from typing import Any, Mapping, Protocol, Sequence

from django.db.models import OuterRef, Q, Subquery
from django.utils import timezone

from chat.models import ChatMessage
from mindreport.services.criteria_service import ReportCriteriaService


PERIOD_WEEK = 'week'
PERIOD_MONTH = 'month'
SUPPORTED_PERIODS = {PERIOD_WEEK, PERIOD_MONTH}
AFFECT_SCORING_METHOD = 'independent-affect-balance-v2'
LABEL_GROUNDED_AFFECT_SCORING_METHOD = 'persisted-label-grounded-affect-balance-v1'
SCORING_ROUTE_LABEL_GROUNDED = 'persisted_emotion_labels_primary'
SCORING_ROUTE_LLM_FALLBACK = 'raw_text_llm_fallback'
AFFECT_DIMENSION_MIN = 0
AFFECT_DIMENSION_MAX = 4
AFFECT_BALANCE_POINT_VALUE = 12.5
CONFIDENCE_LEVELS = (0.0, 0.25, 0.5, 0.75, 1.0)


@dataclass(frozen=True)
class ReportSourceMessage:
    message_id: int
    source_date: date
    content: str
    emotion_label: str | None
    persisted_emotion_label: str | None = None


@dataclass(frozen=True)
class EmotionScore:
    source_date: date
    emotion_label: str
    emotion_state: str
    emotion_score: float
    confidence: float
    emotional_evidence_count: int
    total_message_count: int
    evidence_message_ids: tuple[int, ...]
    rationale: str
    positive_affect: float | None = None
    negative_affect: float | None = None
    activation: float | None = None
    scoring_method: str = 'legacy-llm-direct'


@dataclass(frozen=True)
class MindReportScoringResult:
    status: str
    period_type: str
    eligibility: dict[str, Any]
    source_messages: tuple[ReportSourceMessage, ...]
    emotion_scores: tuple[EmotionScore, ...]
    message: str
    scoring_route: str = ''


class EmotionScoreClient(Protocol):
    def score_messages(self, *, payload: Mapping[str, Any]) -> Mapping[str, Any]:
        ...


def _week_range(target_date: date) -> tuple[datetime, datetime]:
    start_date = target_date - timedelta(days=target_date.weekday())
    end_date = start_date + timedelta(days=6)
    return (
        timezone.make_aware(datetime.combine(start_date, datetime.min.time())),
        timezone.make_aware(datetime.combine(end_date, datetime.max.time())),
    )


def _month_range(year: int, month: int) -> tuple[datetime, datetime]:
    start = timezone.make_aware(datetime(year, month, 1))
    if month == 12:
        end = timezone.make_aware(datetime(year + 1, 1, 1)) - timedelta(microseconds=1)
    else:
        end = timezone.make_aware(datetime(year, month + 1, 1)) - timedelta(microseconds=1)
    return start, end


def load_source_messages(
    *,
    user,
    period_type: str,
    target_date: date | None = None,
    year: int | None = None,
    month: int | None = None,
) -> tuple[ReportSourceMessage, ...]:
    if period_type == PERIOD_WEEK:
        start, end = _week_range(target_date or timezone.now().date())
    elif period_type == PERIOD_MONTH:
        now = timezone.now()
        resolved_year = year or now.year
        resolved_month = month or now.month
        start, end = _month_range(resolved_year, resolved_month)
    else:
        raise ValueError(f'Unsupported mindreport period_type: {period_type}')

    next_message = ChatMessage.objects.filter(
        session_id=OuterRef('session_id'),
    ).filter(
        Q(created_at__gt=OuterRef('created_at'))
        | Q(created_at=OuterRef('created_at'), id__gt=OuterRef('id'))
    ).order_by('created_at', 'id')

    queryset = ChatMessage.objects.filter(
        session__user=user,
        role='user',
        created_at__gte=start,
        created_at__lte=end,
    ).annotate(
        next_message_role=Subquery(next_message.values('role')[:1]),
        next_message_emotion_label=Subquery(
            next_message.values('emotion_label')[:1]
        ),
    )
    return tuple(
        ReportSourceMessage(
            message_id=message.id,
            source_date=timezone.localtime(message.created_at).date(),
            content=message.content,
            emotion_label=message.emotion_label,
            persisted_emotion_label=(
                message.next_message_emotion_label
                if message.next_message_role == 'assistant'
                else None
            ),
        )
        for message in queryset.order_by('created_at', 'id')
    )


def check_report_eligibility(
    *,
    user,
    period_type: str,
    target_date: date | None = None,
    year: int | None = None,
    month: int | None = None,
) -> dict[str, Any]:
    if period_type == PERIOD_WEEK:
        return ReportCriteriaService.check_weekly_report_eligibility(
            user,
            target_date=target_date,
        )
    if period_type == PERIOD_MONTH:
        return ReportCriteriaService.check_monthly_report_eligibility(
            user,
            year=year,
            month=month,
        )
    raise ValueError(f'Unsupported mindreport period_type: {period_type}')


def _group_messages_by_date(
    messages: Sequence[ReportSourceMessage],
) -> dict[str, list[ReportSourceMessage]]:
    grouped: dict[str, list[ReportSourceMessage]] = {}
    for message in messages:
        grouped.setdefault(message.source_date.isoformat(), []).append(message)
    return grouped


def build_emotion_scoring_payload(
    *,
    period_type: str,
    messages: Sequence[ReportSourceMessage],
    use_persisted_emotion_labels: bool = False,
) -> dict[str, Any]:
    grouped = _group_messages_by_date(messages)
    scoring_method = (
        LABEL_GROUNDED_AFFECT_SCORING_METHOD
        if use_persisted_emotion_labels
        else AFFECT_SCORING_METHOD
    )
    scoring_route = (
        SCORING_ROUTE_LABEL_GROUNDED
        if use_persisted_emotion_labels
        else SCORING_ROUTE_LLM_FALLBACK
    )
    payload = {
        'task': 'mind_report_daily_emotion_score_analysis',
        'period_type': period_type,
        'scoring_method': scoring_method,
        'scoring_route': scoring_route,
        'method_scope': (
            'Non-diagnostic internal affect index. The dimensions are informed by '
            'PANAS and the valence/arousal model, but this is not a validated '
            'clinical or patient-reported outcome scale.'
        ),
        'affect_dimension_contract': {
            'positive_affect': {
                '0': 'no positive affect evidence',
                '1': 'weak or indirect positive affect evidence',
                '2': 'clear positive affect evidence',
                '3': 'strong positive affect evidence',
                '4': 'repeated or dominant strong positive affect evidence',
            },
            'negative_affect': {
                '0': 'no negative affect evidence',
                '1': 'weak or indirect negative affect evidence',
                '2': 'clear negative affect evidence',
                '3': 'strong negative affect evidence',
                '4': 'repeated or dominant strong negative affect evidence',
            },
            'activation': {
                '0': 'no activation evidence or calm',
                '1': 'low activation',
                '2': 'moderate activation',
                '3': 'high activation',
                '4': 'very high activation',
            },
        },
        'score_formula': {
            'expression': '50 + 12.5 * (positive_affect - negative_affect)',
            'range': 'clamped to 0..100 by server code',
            'important': 'Do not return or calculate emotion_score.',
        },
        'confidence_contract': {
            '0.00': 'no usable emotional evidence',
            '0.25': 'weak, ambiguous, or mostly inferred evidence',
            '0.50': 'one clear item of evidence',
            '0.75': 'multiple consistent items of evidence',
            '1.00': 'repeated, explicit, and consistent evidence',
        },
        'allowed_emotion_states': ['positive', 'neutral', 'negative'],
        'constraints': [
            'Do not make medical diagnoses, risk ratings, or personality judgments.',
            'Do not assume every message contains emotional evidence.',
            'Use only messages with emotional evidence in evidence_message_ids.',
            'Rate positive and negative affect independently; both may be high.',
            'Use only integer dimension values from 0 through 4.',
            'Use only the confidence values defined in confidence_contract.',
            'If there is no emotional evidence, return zero for all dimensions and confidence.',
            'Return one dimension assessment per source_date.',
            'Return only a valid JSON object.',
        ],
        'daily_groups': [
            {
                'source_date': source_date,
                'total_message_count': len(grouped_messages),
                'messages': [
                    {
                        'message_id': message.message_id,
                        'content': message.content,
                        **(
                            {
                                'persisted_emotion_label': (
                                    message.persisted_emotion_label
                                ),
                            }
                            if use_persisted_emotion_labels
                            else {
                                'current_emotion_label': message.emotion_label,
                            }
                        ),
                    }
                    for message in grouped_messages
                ],
            }
            for source_date, grouped_messages in sorted(grouped.items())
        ],
        'output_schema': {
            'daily_scores': [
                {
                    'source_date': 'YYYY-MM-DD',
                    'emotion_label': 'joy | normal | sadness | anger | anxiety | hurt | panic | etc',
                    'positive_affect': 'integer 0 to 4',
                    'negative_affect': 'integer 0 to 4',
                    'activation': 'integer 0 to 4',
                    'confidence': '0.00 | 0.25 | 0.50 | 0.75 | 1.00',
                    'emotional_evidence_count': 'number of messages used as emotional evidence',
                    'evidence_message_ids': ['message ids used as evidence'],
                    'rationale': 'short Korean reason for the daily score',
                }
            ]
        },
    }

    if use_persisted_emotion_labels:
        payload['persisted_emotion_label_contract'] = {
            'source': (
                'The label saved on the assistant message immediately following '
                'each user message. It represents the chat pipeline first-pass '
                'assessment of that user message.'
            ),
            'labels': {
                'joy': 'first-pass positive affect evidence',
                'sadness': 'first-pass negative affect evidence',
                'anger': 'first-pass negative and potentially activated affect evidence',
                'normal': 'first-pass evidence of no dominant joy, sadness, or anger',
            },
            'usage': [
                'Use the persisted label as the primary first-pass anchor, then read the user text to assess affect dimensions and intensity.',
                'The persisted label is supporting evidence, not an unquestionable diagnosis; resolve obvious text-label conflicts cautiously and explain them in rationale.',
                'Do not replace a valid persisted label with an unrelated emotion without explicit textual evidence.',
            ],
        }
        payload['constraints'].extend([
            'Base the daily assessment first on persisted_emotion_label and refine it using the corresponding user text.',
            'Mention any material conflict between a persisted label and the text in the private rationale.',
        ])

    return payload


def has_complete_persisted_emotion_labels(
    messages: Sequence[ReportSourceMessage],
) -> bool:
    allowed_labels = {'joy', 'sadness', 'anger', 'normal'}
    return bool(messages) and all(
        message.persisted_emotion_label in allowed_labels
        for message in messages
    )


def _extract_json_object(text: str) -> Mapping[str, Any]:
    stripped = text.strip()
    if stripped.startswith('```'):
        stripped = stripped.strip('`')
        if stripped.lower().startswith('json'):
            stripped = stripped[4:].strip()

    try:
        parsed = json.loads(stripped)
    except json.JSONDecodeError:
        start = stripped.find('{')
        end = stripped.rfind('}') + 1
        if start < 0 or end <= start:
            raise
        parsed = json.loads(stripped[start:end])

    if not isinstance(parsed, Mapping):
        raise ValueError('Mind report emotion scoring output must be a JSON object.')
    return parsed


class LangChainEmotionScoreClient:
    def score_messages(self, *, payload: Mapping[str, Any]) -> Mapping[str, Any]:
        from langchain_core.messages import SystemMessage
        from langchain_core.prompts import ChatPromptTemplate, HumanMessagePromptTemplate
        from langchain_openai import ChatOpenAI

        prompt = ChatPromptTemplate(
            messages=[
                SystemMessage(
                    content=(
                        '너는 마음리포트의 일 단위 감정 근거 분류기다. '
                        '하루의 사용자 발화에서 긍정 정서, 부정 정서, 각성도를 각각 독립적으로 분류한다. '
                        '모든 발화에 감정이 있다고 보지 말고, 감정 근거가 있는 발화만 근거로 삼는다. '
                        '긍정과 부정이 함께 드러나면 둘 다 점수를 부여한다. '
                        '0~100 최종 점수는 서버가 계산하므로 직접 생성하지 않는다. '
                        '이 결과는 진단이나 평가가 아니라 날짜별 감정 흐름 분석의 입력값이다. '
                        '입력 근거 밖의 사실을 만들지 말고 JSON 객체만 반환한다.'
                    )
                ),
                HumanMessagePromptTemplate.from_template('{scoring_payload}'),
            ]
        )
        llm = ChatOpenAI(
            model=os.getenv('MINDREPORT_SCORING_MODEL', 'gpt-5.4-mini'),
            temperature=0,
            max_tokens=1400,
        )
        message = (prompt | llm).invoke(
            {'scoring_payload': json.dumps(payload, ensure_ascii=False)}
        )
        content = message.content
        if isinstance(content, list):
            content = ''.join(
                str(item.get('text', item)) if isinstance(item, dict) else str(item)
                for item in content
            )
        return _extract_json_object(str(content))


def _state_from_score(score: float) -> str:
    if score > 55:
        return 'positive'
    if score < 45:
        return 'negative'
    return 'neutral'


def _parse_affect_dimension(row: Mapping[str, Any], key: str) -> float | None:
    if key not in row:
        return None
    try:
        value = round(float(row[key]))
    except (TypeError, ValueError):
        return 0.0
    return float(max(AFFECT_DIMENSION_MIN, min(AFFECT_DIMENSION_MAX, value)))


def _nearest_confidence_level(value: Any) -> float:
    try:
        parsed = max(0.0, min(1.0, float(value)))
    except (TypeError, ValueError):
        return 0.0
    return min(CONFIDENCE_LEVELS, key=lambda level: abs(level - parsed))


def _score_from_affect_dimensions(
    positive_affect: float,
    negative_affect: float,
) -> float:
    score = 50.0 + AFFECT_BALANCE_POINT_VALUE * (
        positive_affect - negative_affect
    )
    return round(max(0.0, min(100.0, score)), 1)


def parse_emotion_scores(
    *,
    payload: Mapping[str, Any],
    source_messages: Sequence[ReportSourceMessage],
    affect_scoring_method: str = AFFECT_SCORING_METHOD,
) -> tuple[EmotionScore, ...]:
    source_by_id = {message.message_id: message for message in source_messages}
    total_by_date: dict[date, int] = {}
    labels_by_date: dict[date, list[str]] = {}
    use_persisted_emotion_labels = (
        affect_scoring_method == LABEL_GROUNDED_AFFECT_SCORING_METHOD
    )
    for message in source_messages:
        total_by_date[message.source_date] = total_by_date.get(message.source_date, 0) + 1
        fallback_label = (
            message.persisted_emotion_label
            if use_persisted_emotion_labels
            else message.emotion_label
        )
        if fallback_label:
            labels_by_date.setdefault(message.source_date, []).append(
                fallback_label
            )

    parsed: list[EmotionScore] = []
    rows = payload.get('daily_scores', payload.get('scores', []))
    if not isinstance(rows, list):
        rows = []

    for row in rows:
        if not isinstance(row, Mapping):
            continue

        source_date = _parse_score_date(row=row, source_by_id=source_by_id)
        if source_date is None or source_date not in total_by_date:
            continue

        evidence_ids = _parse_evidence_ids(
            row=row,
            source_date=source_date,
            source_by_id=source_by_id,
        )
        positive_affect = _parse_affect_dimension(row, 'positive_affect')
        negative_affect = _parse_affect_dimension(row, 'negative_affect')
        activation = _parse_affect_dimension(row, 'activation')
        uses_affect_dimensions = (
            positive_affect is not None and negative_affect is not None
        )

        if uses_affect_dimensions:
            if not evidence_ids:
                positive_affect = 0.0
                negative_affect = 0.0
                activation = 0.0
            emotion_score = _score_from_affect_dimensions(
                positive_affect,
                negative_affect,
            )
            emotion_state = _state_from_score(emotion_score)
            confidence = (
                _nearest_confidence_level(row.get('confidence'))
                if evidence_ids
                else 0.0
            )
            scoring_method = affect_scoring_method
        else:
            try:
                emotion_score = float(row.get('emotion_score'))
            except (TypeError, ValueError):
                emotion_score = 50.0
            emotion_score = max(0.0, min(100.0, emotion_score))
            emotion_state = str(row.get('emotion_state') or '').strip().lower()
            if emotion_state not in {'positive', 'neutral', 'negative'}:
                emotion_state = _state_from_score(emotion_score)
            try:
                confidence = float(row.get('confidence'))
            except (TypeError, ValueError):
                confidence = 0.0
            confidence = max(0.0, min(1.0, confidence))
            scoring_method = 'legacy-llm-direct'
        try:
            emotional_evidence_count = int(row.get('emotional_evidence_count'))
        except (TypeError, ValueError):
            emotional_evidence_count = len(evidence_ids)
        emotional_evidence_count = max(
            0,
            min(total_by_date[source_date], emotional_evidence_count),
        )

        parsed.append(
            EmotionScore(
                source_date=source_date,
                emotion_label=str(
                    row.get('emotion_label')
                    or _fallback_label(labels_by_date.get(source_date, []))
                    or 'normal'
                ),
                emotion_state=emotion_state,
                emotion_score=emotion_score,
                confidence=confidence,
                emotional_evidence_count=emotional_evidence_count,
                total_message_count=total_by_date[source_date],
                evidence_message_ids=evidence_ids,
                rationale=str(row.get('rationale') or ''),
                positive_affect=positive_affect,
                negative_affect=negative_affect,
                activation=activation,
                scoring_method=scoring_method,
            )
        )

    return tuple(sorted(parsed, key=lambda score: score.source_date))


def _parse_score_date(
    *,
    row: Mapping[str, Any],
    source_by_id: Mapping[int, ReportSourceMessage],
) -> date | None:
    raw_source_date = row.get('source_date')
    if raw_source_date:
        try:
            return date.fromisoformat(str(raw_source_date))
        except ValueError:
            return None

    try:
        message_id = int(row.get('message_id'))
    except (TypeError, ValueError):
        return None

    source = source_by_id.get(message_id)
    return source.source_date if source else None


def _parse_evidence_ids(
    *,
    row: Mapping[str, Any],
    source_date: date,
    source_by_id: Mapping[int, ReportSourceMessage],
) -> tuple[int, ...]:
    raw_evidence_ids = row.get('evidence_message_ids', [])
    if not isinstance(raw_evidence_ids, list):
        raw_evidence_ids = []

    if not raw_evidence_ids and row.get('message_id') is not None:
        raw_evidence_ids = [row.get('message_id')]

    evidence_ids = []
    for raw_id in raw_evidence_ids:
        try:
            message_id = int(raw_id)
        except (TypeError, ValueError):
            continue
        source = source_by_id.get(message_id)
        if (
            source is not None
            and source.source_date == source_date
            and message_id not in evidence_ids
        ):
            evidence_ids.append(message_id)
    return tuple(evidence_ids)


def _fallback_label(labels: Sequence[str]) -> str | None:
    for label in labels:
        if label and label != 'normal':
            return label
    return labels[0] if labels else None


class MindReportScoringService:
    def __init__(self, score_client: EmotionScoreClient | None = None):
        self.score_client = score_client

    def run(
        self,
        *,
        user,
        period_type: str,
        target_date: date | None = None,
        year: int | None = None,
        month: int | None = None,
        collection_result=None,
        revision_instructions: Sequence[str] = (),
    ) -> MindReportScoringResult:
        if period_type not in SUPPORTED_PERIODS:
            raise ValueError(f'Unsupported mindreport period_type: {period_type}')

        if collection_result is not None:
            eligibility = collection_result.eligibility
            source_messages = collection_result.source_messages
        else:
            eligibility = check_report_eligibility(
                user=user,
                period_type=period_type,
                target_date=target_date,
                year=year,
                month=month,
            )
            source_messages = (
                load_source_messages(
                    user=user,
                    period_type=period_type,
                    target_date=target_date,
                    year=year,
                    month=month,
                )
                if eligibility['is_eligible']
                else ()
            )

        if not eligibility['is_eligible']:
            return MindReportScoringResult(
                status='insufficient_data',
                period_type=period_type,
                eligibility=eligibility,
                source_messages=source_messages,
                emotion_scores=(),
                message='리포트 생성 기준을 충족하지 않아 LLM 점수 분석을 시작하지 않습니다.',
                scoring_route='criteria_not_met',
            )

        client = self.score_client
        if client is None and os.getenv('OPENAI_API_KEY'):
            client = LangChainEmotionScoreClient()

        if client is None:
            return MindReportScoringResult(
                status='scoring_client_unavailable',
                period_type=period_type,
                eligibility=eligibility,
                source_messages=source_messages,
                emotion_scores=(),
                message='리포트 생성 기준은 충족했지만 LLM 점수 분석 클라이언트가 설정되지 않았습니다.',
                scoring_route='scoring_client_unavailable',
            )

        use_persisted_emotion_labels = has_complete_persisted_emotion_labels(
            source_messages
        )
        scoring_route = (
            SCORING_ROUTE_LABEL_GROUNDED
            if use_persisted_emotion_labels
            else SCORING_ROUTE_LLM_FALLBACK
        )
        affect_scoring_method = (
            LABEL_GROUNDED_AFFECT_SCORING_METHOD
            if use_persisted_emotion_labels
            else AFFECT_SCORING_METHOD
        )
        scoring_payload = build_emotion_scoring_payload(
            period_type=period_type,
            messages=source_messages,
            use_persisted_emotion_labels=use_persisted_emotion_labels,
        )
        if revision_instructions:
            scoring_payload['revision_instructions'] = list(revision_instructions)
        scores = parse_emotion_scores(
            payload=client.score_messages(payload=scoring_payload),
            source_messages=source_messages,
            affect_scoring_method=affect_scoring_method,
        )
        return MindReportScoringResult(
            status='scored',
            period_type=period_type,
            eligibility=eligibility,
            source_messages=source_messages,
            emotion_scores=scores,
            message=(
                '저장된 채팅 감정 라벨을 1차 근거로 사용해 LLM 일 단위 감정 점수 분석을 완료했습니다.'
                if use_persisted_emotion_labels
                else '저장된 채팅 감정 라벨을 완전하게 가져오지 못해 기존 원문 기반 LLM 감정 점수 분석을 완료했습니다.'
            ),
            scoring_route=scoring_route,
        )

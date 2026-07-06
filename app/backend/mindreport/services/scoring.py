from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timedelta
import json
import os
from typing import Any, Mapping, Protocol, Sequence

from django.utils import timezone

from chat.models import ChatMessage
from mindreport.services.criteria_service import ReportCriteriaService


PERIOD_WEEK = 'week'
PERIOD_MONTH = 'month'
SUPPORTED_PERIODS = {PERIOD_WEEK, PERIOD_MONTH}


@dataclass(frozen=True)
class ReportSourceMessage:
    message_id: int
    source_date: date
    content: str
    emotion_label: str | None


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


@dataclass(frozen=True)
class MindReportScoringResult:
    status: str
    period_type: str
    eligibility: dict[str, Any]
    source_messages: tuple[ReportSourceMessage, ...]
    emotion_scores: tuple[EmotionScore, ...]
    message: str


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

    queryset = ChatMessage.objects.filter(
        session__user=user,
        role='user',
        created_at__gte=start,
        created_at__lte=end,
    )
    return tuple(
        ReportSourceMessage(
            message_id=message.id,
            source_date=timezone.localtime(message.created_at).date(),
            content=message.content,
            emotion_label=message.emotion_label,
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
) -> dict[str, Any]:
    grouped = _group_messages_by_date(messages)
    # Temporary implementation: LLM daily scoring stands in for the planned emotion scorer.
    return {
        'task': 'mind_report_daily_emotion_score_analysis',
        'period_type': period_type,
        'score_contract': {
            '0-24': 'strong negative emotion',
            '25-44': 'mild negative emotion',
            '45-55': 'neutral or weak emotional evidence',
            '56-75': 'mild positive emotion',
            '76-100': 'strong positive emotion',
        },
        'allowed_emotion_states': ['positive', 'neutral', 'negative'],
        'constraints': [
            'Do not make medical diagnoses, risk ratings, or personality judgments.',
            'Do not assume every message contains emotional evidence.',
            'Use only messages with emotional evidence in evidence_message_ids.',
            'Return one daily score per source_date on a 0 to 100 scale.',
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
                        'current_emotion_label': message.emotion_label,
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
                    'emotion_state': 'positive | neutral | negative',
                    'emotion_score': '0 to 100 integer',
                    'confidence': '0.0 to 1.0',
                    'emotional_evidence_count': 'number of messages used as emotional evidence',
                    'evidence_message_ids': ['message ids used as evidence'],
                    'rationale': 'short Korean reason for the daily score',
                }
            ]
        },
    }


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
                        '너는 마음리포트의 일 단위 감정 점수 분석기다. '
                        '하루의 사용자 발화를 묶어서 마음리포트 내부 분석용 대표 감정 상태와 0~100점 점수로 변환한다. '
                        '모든 발화에 감정이 있다고 보지 말고, 감정 근거가 있는 발화만 근거로 삼는다. '
                        '점수는 진단이나 평가가 아니라 이후 날짜별 감정 흐름 분석의 입력값이다. '
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


def parse_emotion_scores(
    *,
    payload: Mapping[str, Any],
    source_messages: Sequence[ReportSourceMessage],
) -> tuple[EmotionScore, ...]:
    source_by_id = {message.message_id: message for message in source_messages}
    total_by_date: dict[date, int] = {}
    labels_by_date: dict[date, list[str]] = {}
    for message in source_messages:
        total_by_date[message.source_date] = total_by_date.get(message.source_date, 0) + 1
        if message.emotion_label:
            labels_by_date.setdefault(message.source_date, []).append(message.emotion_label)

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

        evidence_ids = _parse_evidence_ids(
            row=row,
            source_date=source_date,
            source_by_id=source_by_id,
        )
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
            )

        scoring_payload = build_emotion_scoring_payload(
            period_type=period_type,
            messages=source_messages,
        )
        scores = parse_emotion_scores(
            payload=client.score_messages(payload=scoring_payload),
            source_messages=source_messages,
        )
        return MindReportScoringResult(
            status='scored',
            period_type=period_type,
            eligibility=eligibility,
            source_messages=source_messages,
            emotion_scores=scores,
            message='리포트 생성 기준을 충족해 LLM 일 단위 감정 점수 분석을 완료했습니다.',
        )

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timedelta
from typing import Any

from django.utils import timezone

from chat.models import ChatMessage
from mindreport.services.criteria_service import ReportCriteriaService
from mindreport.services.scoring import PERIOD_MONTH, PERIOD_WEEK, SUPPORTED_PERIODS, ReportSourceMessage


@dataclass(frozen=True)
class MindReportCollectionResult:
    status: str
    period_type: str
    eligibility: dict[str, Any]
    source_messages: tuple[ReportSourceMessage, ...]
    message: str
    ltm_context: str = ""


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


def _get_period_range(
    period_type: str,
    target_date: date | None = None,
    year: int | None = None,
    month: int | None = None,
) -> tuple[datetime, datetime]:
    if period_type == PERIOD_WEEK:
        return _week_range(target_date or timezone.now().date())
    elif period_type == PERIOD_MONTH:
        now = timezone.now()
        resolved_year = year or now.year
        resolved_month = month or now.month
        return _month_range(resolved_year, resolved_month)
    else:
        raise ValueError(f'Unsupported mindreport period_type: {period_type}')


def collect_source_messages(
    *,
    user,
    period_type: str,
    target_date: date | None = None,
    year: int | None = None,
    month: int | None = None,
) -> tuple[ReportSourceMessage, ...]:
    start, end = _get_period_range(period_type, target_date, year, month)
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


def collect_ltm_context(
    *,
    user,
    period_type: str,
    target_date: date | None = None,
    year: int | None = None,
    month: int | None = None,
) -> str:
    """
    해당 기간 동안 발생한 사건(Event) 노드와 연동된 인물(Person) 및 감정(Emotion) 데이터를
    Neo4j 그래프DB에서 조회하여 직렬화된 텍스트 컨텍스트로 반환합니다.
    """
    from chat.graph_memory import _get_driver
    drv = _get_driver()
    if drv is None:
        return "조회 가능한 장기 기억(LTM)이 없습니다."

    try:
        start, end = _get_period_range(period_type, target_date, year, month)
        start_date_str = start.strftime('%Y-%m-%d')
        end_date_str = end.strftime('%Y-%m-%d')
        uid = user.id

        query = """
        MATCH (u:User {uid: $uid})-[:HAS_EVENT]->(e:Event)
        WHERE e.valid_until IS NULL AND e.date >= $start_date AND e.date <= $end_date
        OPTIONAL MATCH (e)-[:INVOLVES]->(p:Person)
        WHERE p.valid_until IS NULL AND (u)-[:KNOWS]->(p)
        OPTIONAL MATCH (e)-[:FELT]->(em:Emotion)
        RETURN e.name as name, e.date as date, 
               collect(distinct {name: p.name, relation: p.relation}) as people,
               collect(distinct em.type) as emotions
        ORDER BY e.date ASC
        """

        EMOTION_MAP_SHORT = {
            'joy': '기쁨',
            'sadness': '슬픔',
            'anger': '화남/분노',
            'flutter': '설렘',
            'worry': '걱정/불안',
            'anxiety': '불안',
            'hurt': '상처',
            'surprise': '당황'
        }

        lines = []
        with drv.session() as session:
            records = session.run(query, uid=uid, start_date=start_date_str, end_date=end_date_str).data()
            if not records:
                return "조회 가능한 장기 기억(LTM)이 없습니다."

            for idx, r in enumerate(records):
                name = r.get('name')
                date_val = r.get('date') or ""
                people = r.get('people') or []
                people_clean = [f"{p.get('name')}({p.get('relation') or '인물'})" for p in people if p.get('name')]

                emotions = r.get('emotions') or []
                emotions_clean = [EMOTION_MAP_SHORT.get(em.lower(), em) for em in emotions if em]

                line = f"- 사건 {idx+1}: '{name}' (날짜: {date_val})"
                if people_clean:
                    line += f", 연관 인물: {', '.join(people_clean)}"
                if emotions_clean:
                    line += f", 관련 정서: {', '.join(emotions_clean)}"
                lines.append(line)

        return "\n".join(lines)
    except Exception as e:
        return f"장기 기억(LTM) 조회 과정에서 오류가 발생했습니다: {str(e)}"


def check_generation_criteria(
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


class MindReportDataCollector:
    def run(
        self,
        *,
        user,
        period_type: str,
        target_date: date | None = None,
        year: int | None = None,
        month: int | None = None,
    ) -> MindReportCollectionResult:
        if period_type not in SUPPORTED_PERIODS:
            raise ValueError(f'Unsupported mindreport period_type: {period_type}')

        source_messages = collect_source_messages(
            user=user,
            period_type=period_type,
            target_date=target_date,
            year=year,
            month=month,
        )
        eligibility = check_generation_criteria(
            user=user,
            period_type=period_type,
            target_date=target_date,
            year=year,
            month=month,
        )
        # Neo4j LTM 데이터 수집 (예외 차단막 작동)
        ltm_context = collect_ltm_context(
            user=user,
            period_type=period_type,
            target_date=target_date,
            year=year,
            month=month,
        )

        if not eligibility['is_eligible']:
            return MindReportCollectionResult(
                status='insufficient_data',
                period_type=period_type,
                eligibility=eligibility,
                source_messages=source_messages,
                message='리포트 생성 기준을 충족하지 않았습니다.',
                ltm_context=ltm_context,
            )

        return MindReportCollectionResult(
            status='eligible',
            period_type=period_type,
            eligibility=eligibility,
            source_messages=source_messages,
            message='리포트 생성 기준을 충족했습니다.',
            ltm_context=ltm_context,
        )

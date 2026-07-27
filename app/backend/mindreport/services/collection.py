from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
import logging
from typing import Any

from mindreport.constants import PERIOD_MONTH, PERIOD_WEEK, SUPPORTED_PERIODS
from mindreport.services.criteria_service import ReportCriteriaService
from mindreport.services.periods import resolve_period_window
from mindreport.services.scoring import (
    ReportSourceMessage,
    load_source_messages,
)


logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class MindReportCollectionResult:
    status: str
    period_type: str
    eligibility: dict[str, Any]
    source_messages: tuple[ReportSourceMessage, ...]
    message: str
    ltm_context: str = ""
    ltm_events: tuple['LtmEvent', ...] = ()


@dataclass(frozen=True)
class LtmEvent:
    event_id: str
    episode_id: str
    episode_date: str
    name: str
    occurs_start: str
    occurs_end: str
    cause: str
    people: tuple[dict[str, str], ...]
    places: tuple[str, ...]
    topics: tuple[str, ...]
    emotions: tuple[dict[str, Any], ...]


def ltm_event_to_payload(event: LtmEvent) -> dict[str, Any]:
    return {
        'event_id': event.event_id,
        'episode_id': event.episode_id,
        'episode_date': event.episode_date,
        'name': event.name,
        'occurs_start': event.occurs_start,
        'occurs_end': event.occurs_end,
        'cause': event.cause,
        'people': [dict(person) for person in event.people],
        'places': list(event.places),
        'topics': list(event.topics),
        'emotions': [dict(emotion) for emotion in event.emotions],
    }


def _get_period_range(
    period_type: str,
    target_date: date | None = None,
    year: int | None = None,
    month: int | None = None,
) -> tuple[datetime, datetime]:
    window = resolve_period_window(
        period_type=period_type,
        target_date=target_date,
        year=year,
        month=month,
    )
    return window.start, window.end_inclusive


def collect_source_messages(
    *,
    user,
    period_type: str,
    target_date: date | None = None,
    year: int | None = None,
    month: int | None = None,
) -> tuple[ReportSourceMessage, ...]:
    return load_source_messages(
        user=user,
        period_type=period_type,
        target_date=target_date,
        year=year,
        month=month,
    )


def collect_ltm_events(
    *,
    user,
    period_type: str,
    target_date: date | None = None,
    year: int | None = None,
    month: int | None = None,
) -> tuple[LtmEvent, ...]:
    """
    리포트 기간에 사용자가 이야기한 Episode와 연결된 Event를 구조화해 반환합니다.

    감정을 이야기한 시점은 Episode.created_at으로 제한하고, Event의 occurs_start/end는
    이야기 속 사건 시점으로 별도 보존합니다. 나중에 종료된 사건도 당시의 순간에는
    유효할 수 있으므로 active HAS_EVENT만으로 제한하지 않고, 명시적으로 suppressed 된
    기억만 제외합니다.
    """
    from chat.graph_memory_v2_base import _get_driver

    drv = _get_driver()
    if drv is None:
        logger.warning(
            'GraphDB driver is unavailable for mind report user=%s period=%s.',
            getattr(user, 'pk', getattr(user, 'id', None)),
            period_type,
        )
        return ()

    try:
        start, end = _get_period_range(period_type, target_date, year, month)
        start_date_str = start.strftime('%Y-%m-%d')
        end_date_str = end.strftime('%Y-%m-%d')
        uid = user.id

        query = """
        MATCH (ep:Episode {uid: $uid})-[:RECORDS]->(e:Event {uid: $uid})
        MATCH (u:User {uid: $uid})-[event_rel:HAS_EVENT]->(e)
        WHERE coalesce(e.suppressed, false) = false
          AND substring(toString(ep.created_at), 0, 10) >= $start_date
          AND substring(toString(ep.created_at), 0, 10) <= $end_date
        WITH DISTINCT ep, u, e
        OPTIONAL MATCH (e)-[on_rel:ON]->(d:Date)
        WHERE on_rel.valid_to IS NULL
        WITH ep,
             u,
             e,
             coalesce(
                 e.occurs_start,
                 min(CASE
                     WHEN on_rel.role IN ['on', 'start'] THEN d.date
                 END)
             ) AS event_start,
             coalesce(
                 e.occurs_end,
                 max(CASE WHEN on_rel.role = 'end' THEN d.date END),
                 e.occurs_start,
                 max(d.date)
             ) AS event_end
        OPTIONAL MATCH (e)-[involves:INVOLVES]->(p:Person)
        WHERE involves.valid_to IS NULL
        OPTIONAL MATCH (u)-[person_rel:RELATES_TO]->(p)
        WHERE person_rel.valid_to IS NULL
        OPTIONAL MATCH (e)-[evoked:EVOKED]->(em:Emotion)
        WHERE e.top_emotion IS NULL OR em.type = e.top_emotion
        OPTIONAL MATCH (e)-[:AT]->(place:Place)
        OPTIONAL MATCH (e)-[:ABOUT]->(topic:Topic)
        RETURN coalesce(e.id, e.key) AS event_id,
               ep.id AS episode_id,
               ep.created_at AS episode_created_at,
               e.name AS name,
               e.cause AS cause,
               event_start AS date,
               event_end AS end_date,
               collect(DISTINCT {
                   name: p.name,
                   relation: person_rel.relation
               }) AS people,
               collect(DISTINCT place.name) AS places,
               collect(DISTINCT topic.name) AS topics,
               collect(DISTINCT {type: em.type, score: evoked.score}) AS emotions
        ORDER BY episode_created_at ASC, name ASC
        LIMIT 40
        """
        with drv.session() as session:
            records = session.run(
                query,
                uid=uid,
                start_date=start_date_str,
                end_date=end_date_str,
            ).data()
            if not records:
                return ()

        events = []
        for record in records:
            raw_emotions = record.get('emotions') or []
            emotions = []
            for item in raw_emotions:
                if isinstance(item, dict) and item.get('type'):
                    emotions.append({
                        'type': str(item['type']),
                        'score': item.get('score'),
                    })
                elif item:
                    emotions.append({'type': str(item), 'score': None})

            people = tuple(
                {
                    'name': str(item.get('name')),
                    'relation': str(item.get('relation') or ''),
                }
                for item in (record.get('people') or [])
                if isinstance(item, dict) and item.get('name')
            )
            episode_created_at = str(record.get('episode_created_at') or '')
            events.append(LtmEvent(
                event_id=str(record.get('event_id') or ''),
                episode_id=str(record.get('episode_id') or ''),
                episode_date=episode_created_at[:10],
                name=str(record.get('name') or '').strip(),
                occurs_start=str(record.get('date') or ''),
                occurs_end=str(record.get('end_date') or ''),
                cause=str(record.get('cause') or '').strip(),
                people=people,
                places=tuple(str(item) for item in (record.get('places') or []) if item),
                topics=tuple(str(item) for item in (record.get('topics') or []) if item),
                emotions=tuple(emotions),
            ))
        return tuple(event for event in events if event.name)
    except Exception:
        logger.exception(
            'Failed to collect GraphDB events for mind report user=%s period=%s.',
            getattr(user, 'pk', getattr(user, 'id', None)),
            period_type,
        )
        return ()


def format_ltm_context(events: tuple[LtmEvent, ...]) -> str:
    if not events:
        return "조회 가능한 장기 기억(LTM)이 없습니다."

    emotion_map = {
        'joy': '기쁨', 'sadness': '슬픔', 'anger': '화남/분노', 'normal': '일반',
        'flutter': '설렘', 'worry': '걱정/불안', 'anxiety': '불안', 'hurt': '상처',
        'surprise': '당황', '기쁨': '기쁨', '슬픔': '슬픔', '분노': '화남/분노',
        '일반': '일반',
    }
    lines = []
    for index, event in enumerate(events):
        date_text = event.occurs_start or event.episode_date
        if event.occurs_end and event.occurs_end != date_text:
            date_text = f'{date_text} ~ {event.occurs_end}'
        line = f"- 사건 {index + 1}: '{event.name}' (날짜: {date_text})"
        people = [
            f"{person['name']}({person.get('relation') or '인물'})"
            for person in event.people
        ]
        emotions = [
            emotion_map.get(str(item['type']).lower(), str(item['type']))
            for item in event.emotions
        ]
        if people:
            line += f", 연관 인물: {', '.join(people)}"
        if emotions:
            line += f", 관련 정서: {', '.join(emotions)}"
        lines.append(line)
    return '\n'.join(lines)


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
        ltm_events = collect_ltm_events(
            user=user,
            period_type=period_type,
            target_date=target_date,
            year=year,
            month=month,
        )
        ltm_context = format_ltm_context(ltm_events)

        if not eligibility['is_eligible']:
            return MindReportCollectionResult(
                status='insufficient_data',
                period_type=period_type,
                eligibility=eligibility,
                source_messages=source_messages,
                message='리포트 생성 기준을 충족하지 않았습니다.',
                ltm_context=ltm_context,
                ltm_events=ltm_events,
            )

        return MindReportCollectionResult(
            status='eligible',
            period_type=period_type,
            eligibility=eligibility,
            source_messages=source_messages,
            message='리포트 생성 기준을 충족했습니다.',
            ltm_context=ltm_context,
            ltm_events=ltm_events,
        )

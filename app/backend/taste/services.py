import json
from dataclasses import dataclass, replace
from typing import Callable, Iterable

from django.db.models import Count, Max
from django.db import transaction
from django.utils import timezone
from langchain_core.output_parsers import JsonOutputParser
from langchain_core.prompts import ChatPromptTemplate

from .models import ConversationLog, PreferenceEvidence, PreferenceKeywordSummary


@dataclass(frozen=True)
class PreferenceCandidate:
    message_id: int
    keyword: str
    preference_type: str
    evidence_text: str
    conversation_context: str


@dataclass(frozen=True)
class PreferenceAnalysisResult:
    source_message_count: int
    extracted_candidate_count: int
    saved_evidence_count: int
    excluded_candidate_count: int


@dataclass(frozen=True)
class PreferenceKeywordAggregate:
    keyword: str
    preference_type: str
    count: int
    last_seen: object
    conversation_context: str
    is_displayable: bool


@dataclass(frozen=True)
class PreferenceKeywordSelectionResult:
    total_keyword_count: int
    display_keyword_count: int
    hidden_keyword_count: int
    display_keywords: list[PreferenceKeywordAggregate]


@dataclass(frozen=True)
class PreferenceDashboardPayload:
    status: str
    period_type: str
    period_key: str
    period_label: str
    reflected_conversation_count: int
    reflected_message_count: int
    display_threshold: int
    updated_at: object
    summary: dict
    keywords: list[dict]


PreferenceExtractor = Callable[[list[dict]], Iterable[dict]]
PreferenceKeywordNormalizer = Callable[[str], str]

DEFAULT_KEYWORD_ALIASES = {
    "감정 기록하기": "감정 기록",
    "감정일기": "감정 기록",
    "감정 일기": "감정 기록",
    "노래 듣기": "음악",
    "음악 감상": "음악",
    "산책하기": "산책",
    "짧은 산책": "산책",
}

REDUNDANT_KEYWORD_PREFIXES = (
    "최근 ",
    "요즘 ",
    "자주 ",
    "좋아하는 ",
    "관심 있는 ",
)

REDUNDANT_KEYWORD_SUFFIXES = (
    " 관련",
    " 취향",
    " 선호",
    "하기",
    "하는 것",
)

DISPLAY_CATEGORY_LABELS = {
    "recent_interest": "최근 관심사",
    "indirect_preference_signal": "간접 취향 신호",
    "conversation_preference": "대화 선호",
}


PREFERENCE_EXTRACTION_PROMPT = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            "너는 사용자의 일반 대화 로그에서 취향 분석 후보를 구조화하는 분석기다. "
            "관심사, 취미, 취향, 대화 선호만 추출하고 근거가 부족한 추론은 제외한다. "
            "반드시 JSON만 반환한다.",
        ),
        (
            "human",
            """
최근 30일 사용자 발화 목록을 보고 취향 후보를 추출하라.

추출 조건:
- 각 후보는 keyword, type, evidence, context, message_id를 반드시 가진다.
- keyword는 화면에 표시 가능한 짧은 명사구로 정규화한다.
- type은 "최근 관심사", "취미", "직접 취향", "간접 취향 신호", "대화 선호" 중 하나로 분류한다.
- evidence는 해당 후보를 뒷받침하는 실제 발화 일부다.
- context는 왜 취향 후보로 볼 수 있는지에 대한 짧은 맥락 설명이다.
- 근거 발화와 맥락이 모두 없는 후보는 반환하지 않는다.

반환 형식:
[
  {{
    "message_id": 123,
    "keyword": "감정 기록",
    "type": "간접 취향 신호",
    "evidence": "오늘도 감정 기록을 남겼어",
    "context": "감정 기록 관련 언급이 취향 또는 반복 관심 신호로 나타남"
  }}
]

사용자 발화:
{messages_json}
""",
        ),
    ]
)


def analyze_and_save_preference_evidence(
    *,
    user_id: int,
    period_key: str,
    extractor: PreferenceExtractor | None = None,
    keyword_normalizer: PreferenceKeywordNormalizer | None = None,
    days: int = 30,
    reference_at=None,
) -> PreferenceAnalysisResult:
    messages = list(
        ConversationLog.objects.recent_user_messages(
            user_id=user_id,
            days=days,
            reference_at=reference_at,
        )
    )
    analysis_input = [
        {
            "id": message.id,
            "conversation_id": message.conversation_id,
            "message_text": message.message_text,
            "created_at": message.created_at,
        }
        for message in messages
    ]
    message_by_id = {message.id: message for message in messages}

    extractor = extractor or extract_preference_candidates_with_langchain
    raw_candidates = list(extractor(analysis_input))
    valid_candidates = [
        candidate
        for candidate in (
            _build_candidate(raw_candidate, message_by_id)
            for raw_candidate in raw_candidates
        )
        if candidate is not None
    ]
    normalized_candidates = normalize_and_merge_preference_candidates(
        valid_candidates,
        keyword_normalizer=keyword_normalizer,
    )

    evidence_rows = [
        PreferenceEvidence(
            user_id=user_id,
            message_id=candidate.message_id,
            period_key=period_key,
            normalized_keyword=candidate.keyword,
            preference_type=candidate.preference_type,
            evidence_text=candidate.evidence_text,
            conversation_context=candidate.conversation_context,
            source_created_at=message_by_id[candidate.message_id].created_at,
        )
        for candidate in normalized_candidates
    ]

    with transaction.atomic():
        PreferenceEvidence.objects.bulk_create(evidence_rows)

    return PreferenceAnalysisResult(
        source_message_count=len(messages),
        extracted_candidate_count=len(raw_candidates),
        saved_evidence_count=len(evidence_rows),
        excluded_candidate_count=len(raw_candidates) - len(evidence_rows),
    )


def select_displayable_preference_keywords(
    *,
    user_id: int,
    period_key: str,
    display_threshold: int = 5,
) -> PreferenceKeywordSelectionResult:
    aggregates = calculate_preference_keyword_aggregates(
        user_id=user_id,
        period_key=period_key,
        display_threshold=display_threshold,
    )
    display_keywords = [
        aggregate
        for aggregate in aggregates
        if aggregate.is_displayable
    ]

    return PreferenceKeywordSelectionResult(
        total_keyword_count=len(aggregates),
        display_keyword_count=len(display_keywords),
        hidden_keyword_count=len(aggregates) - len(display_keywords),
        display_keywords=display_keywords,
    )


def calculate_preference_keyword_aggregates(
    *,
    user_id: int,
    period_key: str,
    display_threshold: int = 5,
):
    grouped_rows = (
        PreferenceEvidence.objects
        .filter(user_id=user_id, period_key=period_key)
        .values("normalized_keyword", "preference_type")
        .annotate(
            count=Count("id"),
            last_seen=Max("source_created_at"),
        )
        .order_by("-count", "-last_seen", "normalized_keyword")
    )

    aggregates = []
    for row in grouped_rows:
        context = _latest_context_for_keyword(
            user_id=user_id,
            period_key=period_key,
            normalized_keyword=row["normalized_keyword"],
            preference_type=row["preference_type"],
        )
        aggregates.append(
            PreferenceKeywordAggregate(
                keyword=row["normalized_keyword"],
                preference_type=row["preference_type"],
                count=row["count"],
                last_seen=row["last_seen"],
                conversation_context=context,
                is_displayable=row["count"] >= display_threshold,
            )
        )

    return aggregates


def save_preference_keyword_summary(
    *,
    user_id: int,
    period_key: str,
    period_type: str = "recent_30d",
    display_threshold: int = 5,
    analyzed_at=None,
):
    analyzed_at = analyzed_at or timezone.now()
    selection = select_displayable_preference_keywords(
        user_id=user_id,
        period_key=period_key,
        display_threshold=display_threshold,
    )
    reflected_counts = _calculate_reflected_counts(
        user_id=user_id,
        period_key=period_key,
    )

    return PreferenceKeywordSummary.objects.create(
        user_id=user_id,
        period_type=period_type,
        period_key=period_key,
        reflected_conversation_count=reflected_counts["conversation_count"],
        reflected_message_count=reflected_counts["message_count"],
        display_threshold=display_threshold,
        keywords_json=_to_keywords_json(selection.display_keywords),
        analyzed_at=analyzed_at,
    )


def get_latest_preference_dashboard_payload(
    *,
    user_id: int,
    period_type: str = "recent_30d",
):
    summary = (
        PreferenceKeywordSummary.objects
        .filter(user_id=user_id, period_type=period_type)
        .order_by("-analyzed_at", "-id")
        .first()
    )
    if summary is None:
        return PreferenceDashboardPayload(
            status="empty",
            period_type=period_type,
            period_key="",
            period_label=_period_label(period_type),
            reflected_conversation_count=0,
            reflected_message_count=0,
            display_threshold=5,
            updated_at=None,
            summary={
                "total_keyword_count": 0,
                "display_keyword_count": 0,
                "categories": [],
            },
            keywords=[],
        )

    return build_preference_dashboard_payload(summary)


def build_preference_dashboard_payload(summary):
    parsed = _parse_keywords_json(summary.keywords_json)
    keyword_items = parsed.get("keywords", [])
    summary_payload = parsed.get("summary") or _summarize_keyword_items(keyword_items)

    return PreferenceDashboardPayload(
        status="ready",
        period_type=summary.period_type,
        period_key=summary.period_key,
        period_label=_period_label(summary.period_type),
        reflected_conversation_count=summary.reflected_conversation_count,
        reflected_message_count=summary.reflected_message_count,
        display_threshold=summary.display_threshold,
        updated_at=summary.analyzed_at,
        summary=summary_payload,
        keywords=keyword_items,
    )


def normalize_and_merge_preference_candidates(
    candidates,
    *,
    keyword_normalizer: PreferenceKeywordNormalizer | None = None,
):
    normalizer = keyword_normalizer or normalize_preference_keyword
    merged_candidates = []
    seen_keys = set()

    for candidate in candidates:
        normalized_keyword = normalizer(candidate.keyword)
        if not normalized_keyword:
            continue

        normalized_candidate = replace(candidate, keyword=normalized_keyword)
        merge_key = (
            normalized_candidate.message_id,
            normalized_candidate.keyword,
            normalized_candidate.preference_type,
            normalized_candidate.evidence_text,
            normalized_candidate.conversation_context,
        )
        if merge_key in seen_keys:
            continue

        seen_keys.add(merge_key)
        merged_candidates.append(normalized_candidate)

    return merged_candidates


def normalize_preference_keyword(keyword, aliases=None):
    normalized = _clean_required_text(keyword)
    if not normalized:
        return ""

    normalized = normalized.strip("\"'`“”‘’[](){}")
    normalized = " ".join(normalized.replace("\u3000", " ").split())

    for prefix in REDUNDANT_KEYWORD_PREFIXES:
        if normalized.startswith(prefix):
            normalized = normalized[len(prefix):].strip()

    for suffix in REDUNDANT_KEYWORD_SUFFIXES:
        if normalized.endswith(suffix):
            normalized = normalized[:-len(suffix)].strip()

    alias_map = aliases or DEFAULT_KEYWORD_ALIASES
    return alias_map.get(normalized, normalized)


def _latest_context_for_keyword(
    *,
    user_id: int,
    period_key: str,
    normalized_keyword: str,
    preference_type: str,
):
    latest_evidence = (
        PreferenceEvidence.objects
        .filter(
            user_id=user_id,
            period_key=period_key,
            normalized_keyword=normalized_keyword,
            preference_type=preference_type,
        )
        .order_by("-source_created_at", "-id")
        .first()
    )
    if latest_evidence is None:
        return ""
    return latest_evidence.conversation_context


def _calculate_reflected_counts(*, user_id: int, period_key: str):
    evidence = PreferenceEvidence.objects.filter(user_id=user_id, period_key=period_key)
    return {
        "conversation_count": evidence.values("message__conversation_id").distinct().count(),
        "message_count": evidence.values("message_id").distinct().count(),
    }


def _to_keywords_json(display_keywords):
    keyword_items = _build_keyword_dashboard_items(display_keywords)

    return json.dumps(
        {
            "summary": _summarize_keyword_items(keyword_items),
            "keywords": keyword_items,
        },
        ensure_ascii=False,
    )


def _build_keyword_dashboard_items(display_keywords):
    return [
        {
            "keyword": keyword.keyword,
            "type": keyword.preference_type,
            "display_category": _display_category(keyword.preference_type),
            "display_category_label": DISPLAY_CATEGORY_LABELS[
                _display_category(keyword.preference_type)
            ],
            "count": keyword.count,
            "conversation_context": keyword.conversation_context,
            "last_seen": keyword.last_seen.isoformat() if keyword.last_seen else None,
        }
        for keyword in display_keywords
    ]


def _summarize_keyword_items(keyword_items):
    category_counts = {
        "recent_interest": 0,
        "indirect_preference_signal": 0,
        "conversation_preference": 0,
    }
    for item in keyword_items:
        category = item.get("display_category") or "recent_interest"
        category_counts[category] = category_counts.get(category, 0) + 1

    return {
        "total_keyword_count": len(keyword_items),
        "display_keyword_count": len(keyword_items),
        "categories": [
            {
                "key": key,
                "label": DISPLAY_CATEGORY_LABELS.get(key, key),
                "count": count,
            }
            for key, count in category_counts.items()
            if count > 0
        ],
    }


def _display_category(preference_type):
    text = _clean_required_text(preference_type).lower()
    if "대화" in text or "conversation" in text:
        return "conversation_preference"
    if "간접" in text or "signal" in text:
        return "indirect_preference_signal"
    return "recent_interest"


def _parse_keywords_json(value):
    if not value:
        return {"summary": None, "keywords": []}

    parsed = json.loads(value)
    if isinstance(parsed, list):
        keyword_items = [
            _ensure_dashboard_keyword_item(item)
            for item in parsed
            if isinstance(item, dict)
        ]
        return {
            "summary": _summarize_keyword_items(keyword_items),
            "keywords": keyword_items,
        }
    if isinstance(parsed, dict):
        keyword_items = [
            _ensure_dashboard_keyword_item(item)
            for item in parsed.get("keywords", [])
            if isinstance(item, dict)
        ]
        return {
            "summary": parsed.get("summary") or _summarize_keyword_items(keyword_items),
            "keywords": keyword_items,
        }
    return {"summary": None, "keywords": []}


def _ensure_dashboard_keyword_item(item):
    preference_type = item.get("type") or item.get("preference_type") or ""
    category = item.get("display_category") or _display_category(preference_type)
    return {
        "keyword": item.get("keyword") or "",
        "type": preference_type,
        "display_category": category,
        "display_category_label": item.get("display_category_label")
        or DISPLAY_CATEGORY_LABELS.get(category, category),
        "count": item.get("count") or 0,
        "conversation_context": item.get("conversation_context") or "",
        "last_seen": item.get("last_seen"),
    }


def _period_label(period_type):
    if period_type == "recent_30d":
        return "최근 30일"
    return period_type


def extract_preference_candidates_with_langchain(analysis_input, llm=None):
    if not analysis_input:
        return []

    chain = build_preference_extraction_chain(llm=llm)
    parsed = chain.invoke({"messages_json": _to_prompt_json(analysis_input)})
    if isinstance(parsed, list):
        return parsed
    if isinstance(parsed, dict):
        return parsed.get("candidates", [])
    return []


def build_preference_extraction_chain(llm=None):
    if llm is None:
        from langchain_openai import ChatOpenAI

        llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)

    return PREFERENCE_EXTRACTION_PROMPT | llm | JsonOutputParser()


def _build_candidate(raw_candidate, message_by_id):
    if not isinstance(raw_candidate, dict):
        return None

    message_id = raw_candidate.get("message_id")
    keyword = _clean_required_text(raw_candidate.get("keyword"))
    preference_type = _clean_required_text(raw_candidate.get("type") or raw_candidate.get("preference_type"))
    evidence_text = _clean_required_text(raw_candidate.get("evidence") or raw_candidate.get("evidence_text"))
    conversation_context = _clean_required_text(
        raw_candidate.get("context") or raw_candidate.get("conversation_context")
    )

    if (
        message_id not in message_by_id
        or not keyword
        or not preference_type
        or not evidence_text
        or not conversation_context
    ):
        return None

    return PreferenceCandidate(
        message_id=message_id,
        keyword=keyword,
        preference_type=preference_type,
        evidence_text=evidence_text,
        conversation_context=conversation_context,
    )


def _clean_required_text(value):
    if value is None:
        return ""
    return str(value).strip()


def _to_prompt_json(analysis_input):
    import json

    return json.dumps(
        [
            {
                "message_id": item["id"],
                "conversation_id": item["conversation_id"],
                "message_text": item["message_text"],
                "created_at": item["created_at"].isoformat(),
            }
            for item in analysis_input
        ],
        ensure_ascii=False,
    )

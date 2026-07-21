import json
import logging
import os
import re
import sys

from django.conf import settings

from .models import CatalogEntry, FeatureCode, RuleEntry


logger = logging.getLogger("emotion_cards")

ANALYSIS_PROMPT_VERSION = "emotion-facts-v2.1-timeline"
EMOTION_KO_TO_CODE = {
    "기쁨": "JOY",
    "슬픔": "SADNESS",
    "분노": "ANGER",
    "불안": "ANXIETY",
}

PRIMARY_EMOTIONS = {"JOY", "SADNESS", "ANGER", "ANXIETY"}
VALENCES = {"POSITIVE", "NEGATIVE", "MIXED", "NEUTRAL", "UNKNOWN"}
OUTCOMES = {
    "OUT_SUCCESS",
    "OUT_POSITIVE",
    "OUT_RELIEF",
    "OUT_NEUTRAL",
    "OUT_MIXED",
    "OUT_DIFFICULT",
    "OUT_LOSS",
    "OUT_UNCERTAIN",
    "OUT_UNKNOWN",
}
STAGES = {"STARTED", "ONGOING", "COMPLETED", "WAITING", "CANCELLED", "UNSPECIFIED"}
SOCIAL_CONTEXTS = {
    "ALONE",
    "FRIENDS",
    "PARTNER",
    "FAMILY",
    "COLLEAGUES",
    "CLASSMATES",
    "GROUP",
    "CROWD",
    "ONLINE",
    "PET",
    "NOT_DISCLOSED",
}
CAUSE_TYPES = {
    "WEATHER",
    "WORK_STUDY",
    "RELATIONSHIP",
    "FAMILY",
    "HEALTH",
    "FINANCE",
    "DAILY_LIFE",
    "SELF_EVALUATION",
    "UNEXPECTED",
    "UNKNOWN",
}
EXPLICIT_WEATHER = {"RAIN", "SNOW", "CLEAR", "CLOUDY", "FOG", "WIND", "AFTER_RAIN", "UNKNOWN"}
EXPLICIT_TIMES = {"TODAY", "MORNING", "DAYTIME", "SUNSET", "EVENING", "NIGHT", "DAWN", "UNKNOWN"}
TIME_BUCKETS = {"MORNING", "DAYTIME", "SUNSET", "EVENING", "NIGHT", "DAWN"}
TIME_ANCHORS = {
    "TODAY",
    "MORNING",
    "DAYTIME",
    "SUNSET",
    "EVENING",
    "NIGHT",
    "DAWN",
    "AFTER_WORK",
    "AFTER_SCHOOL",
    "COMMUTE_TO_WORK",
    "COMMUTE_TO_SCHOOL",
    "LEAVING_HOME",
    "RETURNING_HOME",
    "UNKNOWN",
}
WEATHER_TRANSITIONS = {
    "RAIN_TO_CLEAR",
    "RAIN_TO_CLOUDY",
    "CLOUDY_TO_CLEAR",
    "SNOW_TO_CLEAR",
    "NONE",
    "UNKNOWN",
}
ENVIRONMENTS = {"INDOOR", "OUTDOOR", "UNKNOWN"}
FIELD_SOURCES = {
    "EXPLICIT",
    "HIGH_CONFIDENCE_INFERRED",
    "LOW_CONFIDENCE_INFERRED",
    "DEFAULT",
    "NOT_PROVIDED",
}

ANALYSIS_OUTPUT_SCHEMA = {
    "raw_text": "string",
    "primary_emotion": "JOY|SADNESS|ANGER|ANXIETY|null",
    "secondary_emotion": "JOY|SADNESS|ANGER|ANXIETY|null",
    "initial_emotion": "JOY|SADNESS|ANGER|ANXIETY|null",
    "final_emotion": "JOY|SADNESS|ANGER|ANXIETY|null",
    "emotion_transition": "INITIAL_TO_FINAL or NONE|UNKNOWN",
    "emotion_intensity": "LOW|MEDIUM|HIGH",
    "valence": "POSITIVE|NEGATIVE|MIXED|NEUTRAL|UNKNOWN",
    "emotion_cause_type": "|".join(sorted(CAUSE_TYPES)),
    "emotion_cause_summary": "privacy-safe short phrase",
    "event_type_id": "catalog event id or EVT_UNSPECIFIED",
    "event_summary": "privacy-safe short phrase",
    "event_outcome": "|".join(sorted(OUTCOMES)),
    "event_stage": "|".join(sorted(STAGES)),
    "social_context": "|".join(sorted(SOCIAL_CONTEXTS)),
    "energy_code": "ENERGY code|null",
    "need_code": "NEED code|null",
    "explicit_weather": "RAIN|SNOW|CLEAR|CLOUDY|FOG|WIND|AFTER_RAIN|UNKNOWN|null",
    "initial_weather": "RAIN|SNOW|CLEAR|CLOUDY|FOG|WIND|AFTER_RAIN|UNKNOWN|null",
    "final_weather": "RAIN|SNOW|CLEAR|CLOUDY|FOG|WIND|AFTER_RAIN|UNKNOWN|null",
    "weather_transition": "|".join(sorted(WEATHER_TRANSITIONS)),
    "scene_weather": "RAIN|SNOW|CLEAR|CLOUDY|FOG|WIND|AFTER_RAIN|UNKNOWN|null",
    "explicit_time": "TODAY|MORNING|DAYTIME|SUNSET|EVENING|NIGHT|DAWN|UNKNOWN|null",
    "scene_time": {
        "anchor": "|".join(sorted(TIME_ANCHORS)),
        "anchor_expression": "verbatim expression|null",
        "anchor_source": "|".join(sorted(FIELD_SOURCES)),
        "anchor_confidence": "0..1",
        "range": ["MORNING|DAYTIME|SUNSET|EVENING|NIGHT|DAWN"],
        "range_source": "|".join(sorted(FIELD_SOURCES)),
        "range_confidence": "0..1",
    },
    "timeline": [{
        "sequence": "positive integer",
        "clause_text": "verbatim clause from raw_text",
        "time_anchor": "|".join(sorted(TIME_ANCHORS)) + "|null",
        "time_anchor_expression": "verbatim expression|null",
        "time_anchor_source": "|".join(sorted(FIELD_SOURCES)),
        "time_anchor_confidence": "0..1",
        "time_range": ["MORNING|DAYTIME|SUNSET|EVENING|NIGHT|DAWN"],
        "time_range_source": "|".join(sorted(FIELD_SOURCES)),
        "time_range_confidence": "0..1",
        "emotion": "JOY|SADNESS|ANGER|ANXIETY|null",
        "emotion_evidence": "verbatim expression|null",
        "weather": "RAIN|SNOW|CLEAR|CLOUDY|FOG|WIND|AFTER_RAIN|UNKNOWN|null",
        "weather_evidence": "verbatim expression|null",
    }],
    "explicit_environment": "INDOOR|OUTDOOR|UNKNOWN|null",
    "explicit_place": "string|null",
    "explicit_action": "string|null",
    "explicit_objects": ["string"],
    "negated_elements": ["string"],
    "evidence_map": {"field": "verbatim evidence from raw_text"},
    "field_sources": {"field": "|".join(sorted(FIELD_SOURCES))},
    "field_confidences": {"field": "0..1"},
    "analysis_warnings": ["string"],
    "analysis_status": "CLEAR|MIXED|AMBIGUOUS|NOT_DISCLOSED",
}

ANALYSIS_SYSTEM_PROMPT = """
You structure a user's daily emotional record. You are not a therapist and must not diagnose.
Extract facts only. Do not create a scene and do not invent a place, action, object, companion,
need, energy state, or clock time that the user did not provide. Split multi-stage records into
chronologically ordered timeline clauses. The last explicitly stated emotion is final_emotion
and primary_emotion; earlier distinct emotions remain as initial_emotion/secondary_emotion.
Separate weather at each stage and preserve weather transitions.

Treat routine expressions as event anchors, not exact clock facts. For example, 퇴근 is
AFTER_WORK and may imply an EVENING-to-NIGHT range with a confidence score, but it never means
"definitely evening"; explicit context such as night shift, morning, or dawn overrides that
typical range. 집에서 나서는 길 is LEAVING_HOME and 집으로 돌아오는 길 is RETURNING_HOME,
but neither supplies a time-of-day range without more context. Store an inferred range only in
time_range with its source and confidence. When confidence is below 0.75, the range is a soft
ordering hint and must not become an explicit_time or other hard scene fact.

A scene-driving inferred scalar field may be HIGH_CONFIDENCE_INFERRED only when confidence is at
least 0.75; otherwise return null and NOT_PROVIDED. Include verbatim evidence, field source, and
confidence for every extracted fact. Use only the supplied enum codes. Remove names, addresses,
schools, companies, accounts, and other identifying details from summaries. Return one valid
JSON object only.
""".strip()


def _running_tests():
    return "test" in sys.argv or getattr(settings, "TESTING", False)


def _clean_text(value, limit=500):
    text = re.sub(r"\s+", " ", str(value or "")).strip()
    text = re.sub(r"[@#][\w.-]+", "", text)
    text = re.sub(r"\b\d{5,}\b", "", text)
    return re.sub(r"\s+", " ", text).strip()[:limit]


def _normalize_user_input(payload):
    supplied_raw_text = _clean_text(payload.get("raw_text"))
    normalized = {
        "emotion_text": _clean_text(payload.get("emotion_text")),
        "event_text": _clean_text(payload.get("event_text")),
        "energy_text": _clean_text(payload.get("energy_text"), 120),
        "need_text": _clean_text(payload.get("need_text"), 120),
        "memory_text": _clean_text(payload.get("memory_text")),
        "explicit_place": _clean_text(payload.get("explicit_place"), 80),
        "energy_code": _clean_text(payload.get("energy_code"), 80),
        "need_code": _clean_text(payload.get("need_code"), 80),
    }
    if normalized["emotion_text"] and normalized["emotion_text"] == normalized["memory_text"]:
        normalized["memory_text"] = ""

    narrative_parts = [supplied_raw_text] if supplied_raw_text else []
    for key in ("emotion_text", "event_text", "memory_text"):
        value = normalized[key]
        if (
            value
            and value not in narrative_parts
            and not (supplied_raw_text and value in supplied_raw_text)
        ):
            narrative_parts.append(value)
    normalized["raw_text"] = _clean_text(" ".join(narrative_parts), 500)
    return normalized


def _extract_json(raw):
    match = re.search(r"\{.*\}", raw or "", re.S)
    return match.group(0) if match else (raw or "")


def _evidence(raw_text, terms):
    lowered = raw_text.lower()
    for term in terms:
        index = lowered.find(term.lower())
        if index >= 0:
            return raw_text[index:index + len(term)]
    return ""


def _source(value, explicit=False, confidence=0.0):
    if value in (None, "", []):
        return "NOT_PROVIDED"
    if explicit:
        return "EXPLICIT"
    return "HIGH_CONFIDENCE_INFERRED" if confidence >= 0.75 else "LOW_CONFIDENCE_INFERRED"


def _valid_feature(group, code):
    return bool(code) and FeatureCode.objects.filter(group=group, code=code).exists()


def _event_exists(code):
    return bool(code) and CatalogEntry.objects.filter(catalog="event", code=code, enabled=True).exists()


EMOTION_TERMS = (
    ("ANGER", ("화가 나", "화났", "짜증", "분노", "억울", "답답")),
    ("ANXIETY", ("불안", "걱정", "무서", "두려", "초조", "긴장")),
    ("SADNESS", ("우울", "슬퍼", "슬펐", "속상", "외로", "가라앉", "마음이 흐", "허전")),
    (
        "JOY",
        (
            "기분은 좋",
            "기분이 좋",
            "좋아졌",
            "즐거",
            "기뻐",
            "행복",
            "뿌듯",
            "반가",
            "차분해",
            "좋았",
            "안도",
            "후련",
            "마음이 놓",
        ),
    ),
)

WEATHER_TERMS = (
    ("AFTER_RAIN", ("비가 그친", "비 온 뒤", "비가 갠", "비가 그치고")),
    ("RAIN", ("비가", "비는", "비를", "비와", "빗물", "장마")),
    ("SNOW", ("눈이", "눈을", "눈 오는", "폭설")),
    (
        "CLEAR",
        (
            "맑은 날",
            "맑았",
            "맑아",
            "날이 개",
            "개어서",
            "개서",
            "갰",
            "쾌청",
            "구름이 걷",
        ),
    ),
    ("CLOUDY", ("흐린 날", "날씨가 흐", "구름 낀")),
    ("FOG", ("안개",)),
    ("WIND", ("바람이", "강풍", "바람 부")),
)

EXPLICIT_TIME_TERMS = (
    ("DAWN", ("새벽",)),
    ("MORNING", ("아침",)),
    ("SUNSET", ("노을", "해질녘")),
    ("EVENING", ("저녁",)),
    ("NIGHT", ("밤에", "밤")),
    ("DAYTIME", ("낮에", "낮")),
    ("TODAY", ("오늘",)),
)

ROUTINE_TIME_TERMS = (
    ("RETURNING_HOME", ("집으로 돌아오는 길", "집에 돌아오는 길", "집으로 돌아갈 때", "귀가하는 길", "귀갓길"), (), 0.0),
    ("LEAVING_HOME", ("집에서 나서는 길", "집을 나서는 길", "집을 나설 때", "집에서 나올 때"), (), 0.0),
    ("COMMUTE_TO_WORK", ("출근하는 길", "출근길", "출근할 때"), ("MORNING", "DAYTIME"), 0.78),
    ("COMMUTE_TO_SCHOOL", ("등교하는 길", "등굣길", "등교할 때"), ("MORNING",), 0.84),
    ("AFTER_WORK", ("퇴근할 때", "퇴근하는 길", "퇴근길", "퇴근 후", "퇴근"), ("EVENING", "NIGHT"), 0.82),
    ("AFTER_SCHOOL", ("하교할 때", "하교하는 길", "하굣길", "하교 후", "하교"), ("DAYTIME", "EVENING"), 0.78),
)


def _ordered_mentions(text, rules):
    mentions = []
    occupied = []
    for code, terms in rules:
        for term in terms:
            start = text.lower().find(term.lower())
            while start >= 0:
                end = start + len(term)
                if not any(start < used_end and end > used_start for used_start, used_end in occupied):
                    mentions.append({
                        "code": code,
                        "evidence": text[start:end],
                        "start": start,
                        "end": end,
                    })
                    occupied.append((start, end))
                start = text.lower().find(term.lower(), start + 1)
    return sorted(mentions, key=lambda item: (item["start"], item["end"]))


def _emotion_mentions(text):
    return _ordered_mentions(text, EMOTION_TERMS)


def _keyword_primary_emotion(text):
    mentions = _emotion_mentions(text)
    if not mentions:
        return None, ""
    final = mentions[-1]
    return final["code"], final["evidence"]


def _weather_mentions(text):
    negated_spans = []
    for term in ("비가 안", "비는 안", "비 안", "비가 오지 않", "비는 오지 않"):
        start = text.find(term)
        if start >= 0:
            negated_spans.append((start, start + len(term) + 3))
    mentions = [
        item
        for item in _ordered_mentions(text, WEATHER_TERMS)
        if not (
            item["code"] == "RAIN"
            and any(item["start"] >= start and item["start"] < end for start, end in negated_spans)
        )
    ]
    return mentions, (["RAIN"] if negated_spans else [])


def _weather_fact(text):
    mentions, negated = _weather_mentions(text)
    if not mentions:
        return None, "", negated
    final = mentions[-1]
    return final["code"], final["evidence"], negated


def _explicit_time_mentions(text):
    return _ordered_mentions(text, EXPLICIT_TIME_TERMS)


def _time_fact(text):
    mentions = _explicit_time_mentions(text)
    if not mentions:
        return None, ""
    first = mentions[0]
    return first["code"], first["evidence"]


def _routine_time_mentions(text):
    mentions = []
    occupied = []
    for anchor, terms, time_range, confidence in ROUTINE_TIME_TERMS:
        for term in terms:
            start = text.find(term)
            while start >= 0:
                end = start + len(term)
                if not any(start < used_end and end > used_start for used_start, used_end in occupied):
                    mentions.append({
                        "anchor": anchor,
                        "evidence": text[start:end],
                        "start": start,
                        "end": end,
                        "range": list(time_range),
                        "range_confidence": confidence,
                    })
                    occupied.append((start, end))
                start = text.find(term, start + 1)
    return sorted(mentions, key=lambda item: (item["start"], item["end"]))


def _split_timeline_clauses(text):
    boundaries = []
    connector_pattern = re.compile(
        r"(?:했는데|었는데|였는데|했지만|었지만|였지만|했으나|었으나|였으나)"
    )
    for match in connector_pattern.finditer(text):
        boundaries.append(match.end())
    if not boundaries:
        return [(text, 0, len(text))]

    clauses = []
    start = 0
    for end in boundaries:
        clause = text[start:end].strip()
        if clause:
            actual_start = text.find(clause, start, end)
            clauses.append((clause, actual_start, actual_start + len(clause)))
        start = end
    clause = text[start:].strip()
    if clause:
        actual_start = text.find(clause, start)
        clauses.append((clause, actual_start, actual_start + len(clause)))
    return clauses or [(text, 0, len(text))]


def _mention_in_span(mentions, start, end):
    return [item for item in mentions if start <= item["start"] < end]


def _weather_transition(initial, final):
    if not initial or not final or initial == final:
        return "NONE"
    transition = f"{initial}_TO_{final}"
    return transition if transition in WEATHER_TRANSITIONS else "UNKNOWN"


def _scene_weather(initial, final, transition):
    if transition == "RAIN_TO_CLEAR":
        return "AFTER_RAIN"
    return final or initial


def _build_timeline(text):
    emotion_mentions = _emotion_mentions(text)
    weather_mentions, _ = _weather_mentions(text)
    explicit_times = _explicit_time_mentions(text)
    routine_times = _routine_time_mentions(text)
    timeline = []

    for sequence, (clause, start, end) in enumerate(_split_timeline_clauses(text), start=1):
        clause_emotions = _mention_in_span(emotion_mentions, start, end)
        clause_weather = _mention_in_span(weather_mentions, start, end)
        clause_explicit_times = _mention_in_span(explicit_times, start, end)
        clause_routine_times = _mention_in_span(routine_times, start, end)
        if not any((clause_emotions, clause_weather, clause_explicit_times, clause_routine_times)):
            continue

        emotion = clause_emotions[-1] if clause_emotions else None
        weather = clause_weather[-1] if clause_weather else None
        explicit_time = clause_explicit_times[-1] if clause_explicit_times else None
        routine_time = clause_routine_times[-1] if clause_routine_times else None

        if routine_time:
            anchor = routine_time["anchor"]
            anchor_expression = routine_time["evidence"]
            anchor_source = "EXPLICIT"
            anchor_confidence = 1.0
        elif explicit_time:
            anchor = explicit_time["code"]
            anchor_expression = explicit_time["evidence"]
            anchor_source = "EXPLICIT"
            anchor_confidence = 1.0
        else:
            anchor = None
            anchor_expression = None
            anchor_source = "NOT_PROVIDED"
            anchor_confidence = 0.0

        if explicit_time and explicit_time["code"] in TIME_BUCKETS:
            time_range = [explicit_time["code"]]
            range_source = "EXPLICIT"
            range_confidence = 1.0
        elif routine_time and routine_time["range"]:
            time_range = routine_time["range"]
            range_confidence = routine_time["range_confidence"]
            range_source = _source(
                time_range,
                explicit=False,
                confidence=range_confidence,
            )
        else:
            time_range = []
            range_source = "NOT_PROVIDED"
            range_confidence = 0.0

        timeline.append({
            "sequence": sequence,
            "clause_text": clause,
            "time_anchor": anchor,
            "time_anchor_expression": anchor_expression,
            "time_anchor_source": anchor_source,
            "time_anchor_confidence": anchor_confidence,
            "time_range": time_range,
            "time_range_source": range_source,
            "time_range_confidence": range_confidence,
            "emotion": emotion["code"] if emotion else None,
            "emotion_evidence": emotion["evidence"] if emotion else None,
            "weather": weather["code"] if weather else None,
            "weather_evidence": weather["evidence"] if weather else None,
        })
    return timeline


def _timeline_summary(timeline):
    emotions = [item["emotion"] for item in timeline if item.get("emotion") in PRIMARY_EMOTIONS]
    weather = [item["weather"] for item in timeline if item.get("weather") in EXPLICIT_WEATHER]
    initial_emotion = emotions[0] if emotions else None
    final_emotion = emotions[-1] if emotions else None
    secondary_emotion = next(
        (emotion for emotion in emotions if emotion != final_emotion),
        None,
    )
    initial_weather = weather[0] if weather else None
    final_weather = weather[-1] if weather else None
    weather_transition = _weather_transition(initial_weather, final_weather)
    final_timed_segment = next(
        (
            item
            for item in reversed(timeline)
            if item.get("time_anchor") or item.get("time_range")
        ),
        None,
    )
    scene_time = {
        "anchor": (final_timed_segment or {}).get("time_anchor"),
        "anchor_expression": (final_timed_segment or {}).get("time_anchor_expression"),
        "anchor_source": (final_timed_segment or {}).get("time_anchor_source", "NOT_PROVIDED"),
        "anchor_confidence": (final_timed_segment or {}).get("time_anchor_confidence", 0.0),
        "range": list((final_timed_segment or {}).get("time_range") or []),
        "range_source": (final_timed_segment or {}).get("time_range_source", "NOT_PROVIDED"),
        "range_confidence": (final_timed_segment or {}).get("time_range_confidence", 0.0),
    }
    return {
        "initial_emotion": initial_emotion,
        "final_emotion": final_emotion,
        "secondary_emotion": secondary_emotion,
        "emotion_transition": (
            f"{initial_emotion}_TO_{final_emotion}"
            if initial_emotion and final_emotion and initial_emotion != final_emotion
            else "NONE"
        ),
        "initial_weather": initial_weather,
        "final_weather": final_weather,
        "weather_transition": weather_transition,
        "scene_weather": _scene_weather(initial_weather, final_weather, weather_transition),
        "scene_time": scene_time,
    }


def _place_fact(text, supplied_place=""):
    if supplied_place:
        return supplied_place, supplied_place
    rules = (
        ("카페", ("카페",)),
        ("창가", ("창가",)),
        ("회사", ("회사", "사무실")),
        ("학교", ("학교", "교실")),
        ("집", ("집에서", "집에")),
        ("방", ("방에서", "방에")),
        ("거리", ("거리에서", "길에서")),
        ("공원", ("공원",)),
        ("해변", ("바닷가", "해변")),
        ("병원", ("병원",)),
        ("도서관", ("도서관",)),
    )
    for value, terms in rules:
        hit = _evidence(text, terms)
        if hit:
            return value, hit
    return None, ""


def _action_fact(text):
    rules = (
        ("비를 피하기", ("비를 피했", "비를 피하")),
        ("비 바라보기", ("비를 보", "빗물을 보")),
        ("걷기", ("걸어서", "걸었", "걷다", "걷고")),
        ("앉아 있기", ("앉아서", "앉아")),
        ("차 마시기", ("차를 마시", "커피를 마시")),
        ("시험 보기", ("시험을 봤", "시험을 보")),
        ("발표하기", ("발표를 했", "발표를 마")),
    )
    for value, terms in rules:
        hit = _evidence(text, terms)
        if hit:
            return value, hit
    return None, ""


def _object_facts(text):
    rules = (
        ("우산", ("우산",)),
        ("머그잔", ("머그",)),
        ("찻잔", ("찻잔", "차를")),
        ("책", ("책",)),
        ("노트북", ("노트북",)),
        ("담요", ("담요",)),
    )
    values, evidence = [], []
    for value, terms in rules:
        hit = _evidence(text, terms)
        if hit and value not in values:
            values.append(value)
            evidence.append(hit)
    return values[:3], evidence[:3]


def _social_fact(text):
    rules = (
        ("ALONE", ("혼자",)),
        ("FRIENDS", ("친구랑", "친구와", "친구들")),
        ("FAMILY", ("가족",)),
        ("COLLEAGUES", ("동료",)),
        ("CLASSMATES", ("반 친구", "학우")),
        ("PARTNER", ("연인이랑", "연인과")),
        ("PET", ("반려견", "반려묘", "강아지", "고양이")),
    )
    for code, terms in rules:
        hit = _evidence(text, terms)
        if hit:
            return code, hit
    return "NOT_DISCLOSED", ""


def _cause_type(text, weather):
    if weather:
        return "WEATHER"
    rules = (
        ("WORK_STUDY", ("시험", "발표", "과제", "공부", "회사", "업무")),
        ("FAMILY", ("가족", "부모", "형제", "자매")),
        ("RELATIONSHIP", ("친구", "연인", "관계", "다퉈")),
        ("HEALTH", ("아파", "통증", "병원", "몸이")),
        ("FINANCE", ("돈", "금전", "비용", "월급")),
        ("SELF_EVALUATION", ("부족", "비교", "자책")),
        ("UNEXPECTED", ("갑자기", "우연히", "뜻밖")),
        ("DAILY_LIFE", ("오늘", "산책", "요리", "카페")),
    )
    for code, terms in rules:
        if _evidence(text, terms):
            return code
    return "UNKNOWN"


def _event_type(cause_type, text):
    preferred = {
        "WEATHER": "EVT_WEATHER_DAY",
        "FINANCE": "EVT_FINANCE_WORRY",
        "HEALTH": "EVT_BODY_PAIN",
    }.get(cause_type)
    if preferred and _event_exists(preferred):
        return preferred
    event_keyword_map = (
        ("시험", "EVT_EXAM_DIFFICULT"),
        ("발표", "EVT_PRESENTATION_NERVOUS"),
        ("카페", "EVT_CAFE_REST"),
        ("걸", "EVT_WALK"),
    )
    for keyword, code in event_keyword_map:
        if keyword in text and _event_exists(code):
            return code
    return "EVT_UNSPECIFIED"


def _explicit_energy_need(normalized):
    energy = normalized.get("energy_code") or None
    need = normalized.get("need_code") or None
    energy_evidence = normalized.get("energy_text") or energy or ""
    need_evidence = normalized.get("need_text") or need or ""
    if not energy and normalized.get("energy_text"):
        value = normalized["energy_text"]
        if any(term in value for term in ("기운이 없어", "지쳤", "무거워")):
            energy = "ENG_HEAVY"
        elif any(term in value for term in ("에너지 넘", "활기", "신나")):
            energy = "ENG_ENERGETIC"
    if not need and normalized.get("need_text"):
        value = normalized["need_text"]
        if any(term in value for term in ("쉬고 싶", "휴식")):
            need = "NEED_REST"
        elif any(term in value for term in ("위로", "안아")):
            need = "NEED_COMFORT"
    if energy and not _valid_feature("ENERGY", energy):
        energy = None
    if need and not _valid_feature("NEED", need):
        need = None
    return energy, need, energy_evidence, need_evidence


def _keyword_extract(normalized):
    text = normalized["raw_text"]
    timeline = _build_timeline(text)
    timeline_summary = _timeline_summary(timeline)
    emotion = timeline_summary["final_emotion"]
    emotion_evidence = next(
        (
            item.get("emotion_evidence")
            for item in reversed(timeline)
            if item.get("emotion") == emotion
        ),
        "",
    )
    weather = timeline_summary["final_weather"]
    weather_evidence = next(
        (
            item.get("weather_evidence")
            for item in reversed(timeline)
            if item.get("weather") == weather
        ),
        "",
    )
    _, _, negated = _weather_fact(text)
    explicit_time, time_evidence = _time_fact(text)
    place, place_evidence = _place_fact(text, normalized.get("explicit_place"))
    action, action_evidence = _action_fact(text)
    objects, object_evidence = _object_facts(text)
    social, social_evidence = _social_fact(text)
    cause_type = _cause_type(text, weather)
    energy, need, energy_evidence, need_evidence = _explicit_energy_need(normalized)

    environment = None
    environment_evidence = ""
    if place in {"카페", "창가", "회사", "학교", "집", "방", "병원", "도서관"}:
        environment, environment_evidence = "INDOOR", place_evidence
    elif place in {"거리", "공원", "해변"}:
        environment, environment_evidence = "OUTDOOR", place_evidence

    evidence_map = {
        key: value
        for key, value in {
            "primary_emotion": emotion_evidence,
            "initial_emotion": next(
                (
                    item.get("emotion_evidence")
                    for item in timeline
                    if item.get("emotion") == timeline_summary["initial_emotion"]
                ),
                "",
            ),
            "final_emotion": emotion_evidence,
            "emotion_cause_type": weather_evidence or emotion_evidence,
            "explicit_weather": weather_evidence,
            "explicit_time": time_evidence,
            "scene_time": timeline_summary["scene_time"].get("anchor_expression") or "",
            "explicit_environment": environment_evidence,
            "explicit_place": place_evidence,
            "explicit_action": action_evidence,
            "explicit_objects": "|".join(object_evidence),
            "social_context": social_evidence,
            "energy_code": energy_evidence if energy else "",
            "need_code": need_evidence if need else "",
            "negated_elements": _evidence(text, ("비가 안", "비는 안", "비 안")) if negated else "",
        }.items()
        if value
    }

    fields = {
        "primary_emotion": emotion,
        "initial_emotion": timeline_summary["initial_emotion"],
        "final_emotion": timeline_summary["final_emotion"],
        "emotion_cause_type": cause_type if cause_type != "UNKNOWN" else None,
        "explicit_weather": weather,
        "explicit_time": explicit_time,
        "explicit_environment": environment,
        "explicit_place": place,
        "explicit_action": action,
        "explicit_objects": objects,
        "social_context": social if social != "NOT_DISCLOSED" else None,
        "energy_code": energy,
        "need_code": need,
        "negated_elements": negated,
    }
    field_sources = {key: _source(value, explicit=bool(evidence_map.get(key)), confidence=1.0) for key, value in fields.items()}
    field_confidences = {key: (1.0 if field_sources[key] == "EXPLICIT" else 0.0) for key in fields}

    valence = {
        "JOY": "POSITIVE",
        "SADNESS": "NEGATIVE",
        "ANGER": "NEGATIVE",
        "ANXIETY": "NEGATIVE",
    }.get(emotion, "UNKNOWN")
    if timeline_summary["emotion_transition"] != "NONE":
        valence = "MIXED"
    cause_summary = {
        "WEATHER": "weather conditions",
        "WORK_STUDY": "work or study event",
        "RELATIONSHIP": "relationship event",
        "FAMILY": "family event",
        "HEALTH": "health-related difficulty",
        "FINANCE": "financial pressure",
        "DAILY_LIFE": "daily-life event",
        "SELF_EVALUATION": "self-evaluation",
        "UNEXPECTED": "unexpected event",
    }.get(cause_type, "unspecified cause")
    if weather == "RAIN":
        cause_summary = "rainy weather"
    elif timeline_summary["weather_transition"] == "RAIN_TO_CLEAR":
        cause_summary = "rain followed by clearing weather"

    return {
        "raw_text": text,
        "primary_emotion": emotion,
        "secondary_emotion": timeline_summary["secondary_emotion"],
        "initial_emotion": timeline_summary["initial_emotion"],
        "final_emotion": timeline_summary["final_emotion"],
        "emotion_transition": timeline_summary["emotion_transition"],
        "emotion_intensity": "HIGH" if any(term in text for term in ("너무", "정말", "엄청")) else "MEDIUM",
        "valence": valence,
        "emotion_cause_type": cause_type,
        "emotion_cause_summary": cause_summary,
        "event_type_id": _event_type(cause_type, text),
        "event_summary": cause_summary,
        "event_outcome": (
            "OUT_RELIEF"
            if timeline_summary["emotion_transition"].endswith("_TO_JOY")
            else ("OUT_POSITIVE" if emotion == "JOY" else "OUT_UNKNOWN")
        ),
        "event_stage": "COMPLETED" if "했" in text or "왔" in text else "UNSPECIFIED",
        "social_context": social,
        "energy_code": energy,
        "need_code": need,
        "explicit_weather": weather,
        "initial_weather": timeline_summary["initial_weather"],
        "final_weather": timeline_summary["final_weather"],
        "weather_transition": timeline_summary["weather_transition"],
        "scene_weather": timeline_summary["scene_weather"],
        "explicit_time": explicit_time,
        "scene_time": timeline_summary["scene_time"],
        "timeline": timeline,
        "explicit_environment": environment,
        "explicit_place": place,
        "explicit_action": action,
        "explicit_objects": objects,
        "negated_elements": negated,
        "evidence_map": evidence_map,
        "field_sources": field_sources,
        "field_confidences": field_confidences,
        "analysis_warnings": [],
        "analysis_status": (
            "MIXED"
            if (
                timeline_summary["emotion_transition"] != "NONE"
                or timeline_summary["weather_transition"] not in {"NONE", "UNKNOWN"}
            )
            else ("CLEAR" if emotion else "AMBIGUOUS")
        ),
    }


def _select_examples(limit=12):
    rows = list(
        RuleEntry.objects.filter(rule_type="extraction_example", enabled=True)
        .order_by("rule_id")
        .values_list("data", flat=True)[:limit]
    )
    return rows


def _llm_extract_facts(normalized):
    if _running_tests() or not getattr(settings, "EMOTION_CARD_ENABLE_LLM_ANALYSIS", True):
        return None, None
    api_key = getattr(settings, "OPENAI_API_KEY", "")
    if not api_key:
        return None, None
    model = (
        getattr(settings, "EMOTION_CARD_ANALYSIS_MODEL", "")
        or getattr(settings, "EMOTION_CARD_LLM_MODEL", "")
        or os.environ.get("OPENAI_MODEL", "gpt-5.4-mini")
    )
    request = {
        "input": {
            "raw_text": normalized["raw_text"],
            "energy_answer": normalized["energy_text"],
            "need_answer": normalized["need_text"],
        },
        "schema": ANALYSIS_OUTPUT_SCHEMA,
        "examples": _select_examples(),
        "timeline_examples": [
            {
                "input": (
                    "아침에 비가 와서 우울했는데 퇴근할 때 되니까 "
                    "날이 맑아져서 기분이 좋아졌어"
                ),
                "expected": {
                    "initial_emotion": "SADNESS",
                    "final_emotion": "JOY",
                    "primary_emotion": "JOY",
                    "secondary_emotion": "SADNESS",
                    "emotion_transition": "SADNESS_TO_JOY",
                    "initial_weather": "RAIN",
                    "final_weather": "CLEAR",
                    "weather_transition": "RAIN_TO_CLEAR",
                    "scene_weather": "AFTER_RAIN",
                    "scene_time": {
                        "anchor": "AFTER_WORK",
                        "anchor_expression": "퇴근할 때",
                        "anchor_source": "EXPLICIT",
                        "anchor_confidence": 1.0,
                        "range": ["EVENING", "NIGHT"],
                        "range_source": "HIGH_CONFIDENCE_INFERRED",
                        "range_confidence": 0.82,
                    },
                },
            },
            {
                "input": (
                    "집에서 나서는 길에는 불안했지만 "
                    "집으로 돌아오는 길에는 안도했어"
                ),
                "expected": {
                    "initial_emotion": "ANXIETY",
                    "final_emotion": "JOY",
                    "primary_emotion": "JOY",
                    "scene_time": {
                        "anchor": "RETURNING_HOME",
                        "anchor_expression": "집으로 돌아오는 길",
                        "anchor_source": "EXPLICIT",
                        "anchor_confidence": 1.0,
                        "range": [],
                        "range_source": "NOT_PROVIDED",
                        "range_confidence": 0.0,
                    },
                },
            },
        ],
    }
    try:
        from openai import OpenAI

        response = OpenAI(api_key=api_key).chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": ANALYSIS_SYSTEM_PROMPT},
                {"role": "user", "content": json.dumps(request, ensure_ascii=False)},
            ],
            max_completion_tokens=2000,
            response_format={"type": "json_object"},
        )
        content = response.choices[0].message.content
        return json.loads(_extract_json(content)), model
    except Exception:
        logger.exception("[emotion_card] fact extraction failed; deterministic extraction will be used (model=%s)", model)
        return None, model


def _model_emotion(raw_text):
    if _running_tests() or not raw_text:
        return None, 0.0
    try:
        from ai.emotion.emotion_model import predict_emotion_with_confidence

        label, confidence = predict_emotion_with_confidence(raw_text)
        code = EMOTION_KO_TO_CODE.get(label or "")
        return code, float(confidence or 0.0)
    except Exception:
        return None, 0.0


def _bounded_string(value, limit):
    return _clean_text(value, limit) if value not in (None, "") else None


def _bounded_confidence(value):
    try:
        return max(0.0, min(1.0, float(value)))
    except (TypeError, ValueError):
        return 0.0


def _validated_source(value, confidence=0.0):
    if value not in FIELD_SOURCES:
        return "NOT_PROVIDED"
    if value == "HIGH_CONFIDENCE_INFERRED" and confidence < 0.75:
        return "LOW_CONFIDENCE_INFERRED"
    return value


def _verbatim_or_none(value, raw_text, limit=160):
    value = _bounded_string(value, limit)
    return value if value and value in raw_text else None


def _validate_timeline(value, raw_text):
    if not isinstance(value, list):
        return []
    timeline = []
    for raw_segment in value[:8]:
        if not isinstance(raw_segment, dict):
            continue
        clause = _verbatim_or_none(raw_segment.get("clause_text"), raw_text, 240)
        if not clause:
            continue
        emotion = raw_segment.get("emotion")
        emotion = emotion if emotion in PRIMARY_EMOTIONS else None
        weather = raw_segment.get("weather")
        weather = weather if weather in EXPLICIT_WEATHER else None
        anchor = raw_segment.get("time_anchor")
        anchor = anchor if anchor in TIME_ANCHORS else None
        anchor_confidence = _bounded_confidence(raw_segment.get("time_anchor_confidence"))
        anchor_source = _validated_source(
            raw_segment.get("time_anchor_source"),
            anchor_confidence,
        )
        anchor_expression = _verbatim_or_none(
            raw_segment.get("time_anchor_expression"),
            raw_text,
            80,
        )
        if not anchor or not anchor_expression:
            anchor = None
            anchor_expression = None
            anchor_source = "NOT_PROVIDED"
            anchor_confidence = 0.0

        time_range = raw_segment.get("time_range")
        if not isinstance(time_range, list):
            time_range = []
        time_range = [
            item
            for item in dict.fromkeys(time_range)
            if item in TIME_BUCKETS
        ][:3]
        range_confidence = _bounded_confidence(raw_segment.get("time_range_confidence"))
        range_source = _validated_source(
            raw_segment.get("time_range_source"),
            range_confidence,
        )
        if not time_range:
            range_source = "NOT_PROVIDED"
            range_confidence = 0.0

        emotion_evidence = _verbatim_or_none(
            raw_segment.get("emotion_evidence"),
            raw_text,
            80,
        )
        weather_evidence = _verbatim_or_none(
            raw_segment.get("weather_evidence"),
            raw_text,
            80,
        )
        if not emotion_evidence:
            emotion = None
        if not weather_evidence:
            weather = None
        if not any((emotion, weather, anchor, time_range)):
            continue
        timeline.append({
            "sequence": len(timeline) + 1,
            "clause_text": clause,
            "time_anchor": anchor,
            "time_anchor_expression": anchor_expression,
            "time_anchor_source": anchor_source,
            "time_anchor_confidence": anchor_confidence,
            "time_range": time_range,
            "time_range_source": range_source,
            "time_range_confidence": range_confidence,
            "emotion": emotion,
            "emotion_evidence": emotion_evidence,
            "weather": weather,
            "weather_evidence": weather_evidence,
        })
    return timeline


def _apply_timeline_summary(result):
    timeline = result.get("timeline") or []
    if not timeline:
        return result
    summary = _timeline_summary(timeline)
    final_emotion = summary["final_emotion"]
    if final_emotion:
        result["primary_emotion"] = final_emotion
        result["final_emotion"] = final_emotion
        result["initial_emotion"] = summary["initial_emotion"]
        result["secondary_emotion"] = summary["secondary_emotion"]
        result["emotion_transition"] = summary["emotion_transition"]
        if summary["emotion_transition"] != "NONE":
            result["valence"] = "MIXED"
            result["analysis_status"] = "MIXED"
            if final_emotion == "JOY":
                result["event_outcome"] = "OUT_RELIEF"
    result["initial_weather"] = summary["initial_weather"]
    result["final_weather"] = summary["final_weather"]
    result["weather_transition"] = summary["weather_transition"]
    result["scene_weather"] = summary["scene_weather"]
    result["scene_time"] = summary["scene_time"]
    if summary["weather_transition"] not in {"NONE", "UNKNOWN"}:
        result["analysis_status"] = "MIXED"
    return result


def _validate_analysis_output(data, raw_text):
    if not isinstance(data, dict):
        return None
    out = {}
    out["raw_text"] = raw_text
    out["primary_emotion"] = data.get("primary_emotion") if data.get("primary_emotion") in PRIMARY_EMOTIONS else None
    out["secondary_emotion"] = data.get("secondary_emotion") if data.get("secondary_emotion") in PRIMARY_EMOTIONS else None
    out["initial_emotion"] = data.get("initial_emotion") if data.get("initial_emotion") in PRIMARY_EMOTIONS else None
    out["final_emotion"] = data.get("final_emotion") if data.get("final_emotion") in PRIMARY_EMOTIONS else None
    transition = _bounded_string(data.get("emotion_transition"), 60)
    out["emotion_transition"] = transition if transition else "UNKNOWN"
    out["emotion_intensity"] = data.get("emotion_intensity") if data.get("emotion_intensity") in {"LOW", "MEDIUM", "HIGH"} else "MEDIUM"
    out["valence"] = data.get("valence") if data.get("valence") in VALENCES else "UNKNOWN"
    out["emotion_cause_type"] = data.get("emotion_cause_type") if data.get("emotion_cause_type") in CAUSE_TYPES else "UNKNOWN"
    out["emotion_cause_summary"] = _bounded_string(data.get("emotion_cause_summary"), 160) or "unspecified cause"
    event_type = data.get("event_type_id")
    out["event_type_id"] = event_type if _event_exists(event_type) else "EVT_UNSPECIFIED"
    out["event_summary"] = _bounded_string(data.get("event_summary"), 200) or out["emotion_cause_summary"]
    out["event_outcome"] = data.get("event_outcome") if data.get("event_outcome") in OUTCOMES else "OUT_UNKNOWN"
    out["event_stage"] = data.get("event_stage") if data.get("event_stage") in STAGES else "UNSPECIFIED"
    out["social_context"] = data.get("social_context") if data.get("social_context") in SOCIAL_CONTEXTS else "NOT_DISCLOSED"
    out["energy_code"] = data.get("energy_code") if _valid_feature("ENERGY", data.get("energy_code")) else None
    out["need_code"] = data.get("need_code") if _valid_feature("NEED", data.get("need_code")) else None
    out["explicit_weather"] = data.get("explicit_weather") if data.get("explicit_weather") in EXPLICIT_WEATHER else None
    out["initial_weather"] = data.get("initial_weather") if data.get("initial_weather") in EXPLICIT_WEATHER else None
    out["final_weather"] = data.get("final_weather") if data.get("final_weather") in EXPLICIT_WEATHER else None
    weather_transition = data.get("weather_transition")
    out["weather_transition"] = weather_transition if weather_transition in WEATHER_TRANSITIONS else "UNKNOWN"
    out["scene_weather"] = data.get("scene_weather") if data.get("scene_weather") in EXPLICIT_WEATHER else None
    out["explicit_time"] = data.get("explicit_time") if data.get("explicit_time") in EXPLICIT_TIMES else None
    out["timeline"] = _validate_timeline(data.get("timeline"), raw_text)
    out["explicit_environment"] = data.get("explicit_environment") if data.get("explicit_environment") in ENVIRONMENTS else None
    out["explicit_place"] = _bounded_string(data.get("explicit_place"), 80)
    out["explicit_action"] = _bounded_string(data.get("explicit_action"), 80)
    objects = data.get("explicit_objects") if isinstance(data.get("explicit_objects"), list) else []
    out["explicit_objects"] = [_clean_text(item, 40) for item in objects if _clean_text(item, 40)][:3]
    negated = data.get("negated_elements") if isinstance(data.get("negated_elements"), list) else []
    out["negated_elements"] = [_clean_text(item, 40).upper() for item in negated if _clean_text(item, 40)][:8]

    supplied_evidence = data.get("evidence_map") if isinstance(data.get("evidence_map"), dict) else {}
    out["evidence_map"] = {}
    for field, evidence in supplied_evidence.items():
        evidence = _clean_text(evidence, 120)
        if evidence and evidence in raw_text:
            out["evidence_map"][_clean_text(field, 60)] = evidence

    supplied_sources = data.get("field_sources") if isinstance(data.get("field_sources"), dict) else {}
    supplied_confidence = data.get("field_confidences") if isinstance(data.get("field_confidences"), dict) else {}
    out["field_sources"] = {}
    out["field_confidences"] = {}
    fact_fields = (
        "primary_emotion",
        "emotion_cause_type",
        "explicit_weather",
        "explicit_time",
        "explicit_environment",
        "explicit_place",
        "explicit_action",
        "explicit_objects",
        "social_context",
        "energy_code",
        "need_code",
        "negated_elements",
    )
    for field in fact_fields:
        try:
            confidence = max(0.0, min(1.0, float(supplied_confidence.get(field, 0.0))))
        except (TypeError, ValueError):
            confidence = 0.0
        source = supplied_sources.get(field)
        if source not in FIELD_SOURCES:
            source = "EXPLICIT" if out["evidence_map"].get(field) else "NOT_PROVIDED"
        value = out.get(field)
        if value in (None, "", []) or (source == "HIGH_CONFIDENCE_INFERRED" and confidence < 0.75):
            if field in {"energy_code", "need_code", "explicit_place", "explicit_action", "explicit_objects"}:
                out[field] = None if field != "explicit_objects" else []
            source = "NOT_PROVIDED"
            confidence = 0.0
        out["field_sources"][field] = source
        out["field_confidences"][field] = confidence

    warnings = data.get("analysis_warnings") if isinstance(data.get("analysis_warnings"), list) else []
    out["analysis_warnings"] = [_clean_text(item, 120) for item in warnings if _clean_text(item, 120)][:8]
    status = data.get("analysis_status")
    out["analysis_status"] = status if status in {"CLEAR", "MIXED", "AMBIGUOUS", "NOT_DISCLOSED"} else "CLEAR"
    return _apply_timeline_summary(out)


def _merge_explicit_facts(llm, fallback):
    if not llm:
        return fallback
    merged = dict(llm)
    merged["evidence_map"] = dict(llm.get("evidence_map") or {})
    merged["field_sources"] = dict(llm.get("field_sources") or {})
    merged["field_confidences"] = dict(llm.get("field_confidences") or {})

    # Deterministic extraction is a guardrail for literal facts, not an
    # emotion classifier that can overwrite a valid chronological LLM result.
    guarded_literal_fields = {
        "explicit_weather",
        "explicit_time",
        "explicit_environment",
        "explicit_place",
        "explicit_action",
        "explicit_objects",
        "social_context",
        "energy_code",
        "need_code",
        "negated_elements",
    }
    for field, source in fallback["field_sources"].items():
        if source == "EXPLICIT" and (
            field in guarded_literal_fields or not merged.get(field)
        ):
            merged[field] = fallback.get(field)
            evidence = fallback["evidence_map"].get(field, "")
            if evidence:
                merged["evidence_map"][field] = evidence
            merged["field_sources"][field] = "EXPLICIT"
            merged["field_confidences"][field] = 1.0

    def timeline_evidence_score(timeline):
        return sum(
            bool(item.get("emotion"))
            + bool(item.get("weather"))
            + bool(item.get("time_anchor"))
            for item in (timeline or [])
        )

    llm_timeline = llm.get("timeline") or []
    fallback_timeline = fallback.get("timeline") or []
    merged["timeline"] = (
        fallback_timeline
        if timeline_evidence_score(fallback_timeline) > timeline_evidence_score(llm_timeline)
        else llm_timeline
    )
    if not merged["timeline"] and fallback.get("primary_emotion") and not merged.get("primary_emotion"):
        merged["primary_emotion"] = fallback["primary_emotion"]
    merged = _apply_timeline_summary(merged)

    if merged.get("primary_emotion"):
        merged["field_sources"]["primary_emotion"] = "EXPLICIT"
        merged["field_confidences"]["primary_emotion"] = 1.0
        final_evidence = next(
            (
                item.get("emotion_evidence")
                for item in reversed(merged.get("timeline") or [])
                if item.get("emotion") == merged["primary_emotion"]
            ),
            None,
        )
        if final_evidence:
            merged["evidence_map"]["primary_emotion"] = final_evidence
            merged["evidence_map"]["final_emotion"] = final_evidence
    merged["raw_text"] = fallback["raw_text"]
    return merged


def extract_analysis(payload, allow_llm=True):
    normalized = _normalize_user_input(payload)
    fallback = _keyword_extract(normalized)
    raw_llm, model = _llm_extract_facts(normalized) if allow_llm else (None, None)
    validated_llm = _validate_analysis_output(raw_llm, normalized["raw_text"]) if raw_llm else None
    result = _merge_explicit_facts(validated_llm, fallback)
    if (
        fallback.get("field_sources", {}).get("primary_emotion")
        != "EXPLICIT"
        and not result.get("primary_emotion")
    ):
        model_emotion, model_confidence = _model_emotion(
            normalized["raw_text"]
        )
        gate = float(
            getattr(settings, "EMOTION_CARD_EMOTION_CONF_GATE", 0.80)
        )
        if model_emotion and model_confidence >= gate:
            result["primary_emotion"] = model_emotion
            result.setdefault("field_sources", {})[
                "primary_emotion"
            ] = "HIGH_CONFIDENCE_INFERRED"
            result.setdefault("field_confidences", {})[
                "primary_emotion"
            ] = model_confidence
    result["analysis_model"] = model or "deterministic-timeline-v2.1"
    result["analysis_prompt_version"] = ANALYSIS_PROMPT_VERSION
    return normalized, result


def sanitize_analysis_text(value, limit=200):
    return _clean_text(value, limit)

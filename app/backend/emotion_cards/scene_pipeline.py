import json
import logging
import os
import re
import sys
from collections import defaultdict

from django.conf import settings

from .models import CatalogEntry, RuleEntry, SocialCompanionRule


logger = logging.getLogger("emotion_cards")

SCENE_VERSION = "2.1-timeline"
DIRECTOR_PROMPT_VERSION = "scene-director-v2.1-timeline"

SCENE_DIRECTOR_SYSTEM = """
You are a visual scene director for an emotional wellness card service.
Preserve every explicitly stated user fact. Use only eligible candidates from the supplied
candidate pool for weather, location, action, pose, expression, lighting, palette, composition,
objects, effects, and companions. You may add ordinary spatial relations, body language, gaze,
camera framing, and object placement needed to connect selected candidates into one coherent
symbolic scene; this staging is not a claim about what happened. Keep the visible cause of the
emotion recognizable and include at least the required number of visible cues. The final emotion
is the dominant expression and body language. Earlier emotions and earlier weather may appear
only as environmental traces (for example wet pavement after rain or cooler shadows behind warm
light), never as the dominant current state. Treat an inferred time range as soft atmosphere,
not an exact clock fact. Never allow a decorative style to replace or contradict scene content.
Do not invent named people, companies, schools, addresses, readable documents, or personal facts.
Return valid JSON only.
""".strip()

CATEGORY_CATALOG = {
    "weather": "weather",
    "location": "location",
    "action": "action",
    "pose": "character_visual",
    "expression": "character_visual",
    "lighting": "lighting",
    "palette": "lighting",
    "composition": "effect",
    "objects": "object",
    "effects": "effect",
}

SELECTED_KEYS = {
    "weather": "weather_id",
    "location": "location_id",
    "action": "action_id",
    "pose": "pose_id",
    "expression": "expression_id",
    "lighting": "lighting_id",
    "palette": "palette_id",
    "composition": "composition_id",
    "objects": "object_ids",
    "effects": "effect_ids",
    "companions": "companion_ids",
}

EXPLICIT_WEATHER_IDS = {
    "RAIN": "WTH_RAIN",
    "AFTER_RAIN": "WTH_AFTER_RAIN",
    "CLEAR": "WTH_CLEAR",
    "CLOUDY": "WTH_CLOUDY",
    "FOG": "WTH_MIST_DAWN",
    "WIND": "WTH_LIGHT_CLOUDS",
}

DEFAULTS = {
    "JOY": {
        "weather": ["WTH_CLEAR"],
        "location": ["LOC_PARK", "LOC_WINDOW"],
        "action": ["ACT_WATCH_VIEW", "ACT_SIT_QUIET"],
        "pose": ["POSE_OPEN", "POSE_NATURAL"],
        "expression": ["EXP_BRIGHT", "EXP_RELIEVED"],
        "lighting": ["LGT_WARM_SUN"],
        "palette": ["PAL_CORAL_GOLD"],
        "composition": ["COMP_BALANCED"],
    },
    "SADNESS": {
        "weather": ["WTH_CLOUDY", "WTH_AFTER_RAIN"],
        "location": ["LOC_WINDOW", "LOC_QUIET_ROOM", "LOC_CAFE", "LOC_STREET"],
        "action": ["ACT_WATCH_RAIN", "ACT_SIT_QUIET", "ACT_SLOW_WALK"],
        "pose": ["POSE_SAD_SEATED", "POSE_LOW"],
        "expression": ["EXP_SAD", "EXP_QUIET"],
        "lighting": ["LGT_COOL_WINDOW", "LGT_OVERCAST", "LGT_LAMP"],
        "palette": ["PAL_BLUE_GRAY", "PAL_LAVENDER_BLUE"],
        "composition": ["COMP_OFF_CENTER_WINDOW", "COMP_CLOSE"],
    },
    "ANGER": {
        "weather": ["WTH_CLOUDY"],
        "location": ["LOC_QUIET_ROOM", "LOC_STREET"],
        "action": ["ACT_SLOW_WALK", "ACT_SIT_QUIET"],
        "pose": ["POSE_NATURAL", "POSE_LOW"],
        "expression": ["EXP_ANGER", "EXP_IRRITATED"],
        "lighting": ["LGT_CLOUD"],
        "palette": ["PAL_PLUM_CORAL"],
        "composition": ["COMP_DISTANCE", "COMP_BALANCED"],
    },
    "ANXIETY": {
        "weather": ["WTH_CLOUDY"],
        "location": ["LOC_QUIET_ROOM", "LOC_WINDOW"],
        "action": ["ACT_SIT_QUIET", "ACT_SLOW_WALK"],
        "pose": ["POSE_LOW", "POSE_NATURAL"],
        "expression": ["EXP_TENSE", "EXP_CONFUSED"],
        "lighting": ["LGT_OVERCAST", "LGT_CLOUD"],
        "palette": ["PAL_LAVENDER_BLUE", "PAL_BLUE_GRAY"],
        "composition": ["COMP_CLOSE", "COMP_BALANCED"],
    },
}


def _running_tests():
    return "test" in sys.argv or getattr(settings, "TESTING", False)


def _split(value):
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]
    return [part.strip() for part in str(value or "").split("|") if part.strip()]


def _int(value, default=0):
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _float(value, default=0.0):
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _catalog_entry(category, code):
    catalog = CATEGORY_CATALOG.get(category)
    if not catalog or not code:
        return None
    entry = CatalogEntry.objects.filter(catalog=catalog, code=code, enabled=True).first()
    if not entry:
        return None
    visual_type = str(entry.metadata.get("visual_type") or entry.metadata.get("element_type") or "").upper()
    if category == "pose" and visual_type and visual_type != "POSE":
        return None
    if category == "expression" and visual_type and visual_type != "EXPRESSION":
        return None
    if category == "lighting" and visual_type and visual_type != "LIGHTING":
        return None
    if category == "palette" and visual_type and visual_type != "PALETTE":
        return None
    if category == "composition" and visual_type and visual_type != "COMPOSITION":
        return None
    if category == "effects" and visual_type and visual_type != "EFFECT":
        return None
    return entry


def _candidate(entry, category, score, source, reason_code, rule_id=None, hard_required=False, hard_forbidden=False):
    return {
        "candidate_id": entry.code,
        "category": category,
        "display_name": entry.display_name,
        "visual_prompt": entry.visual_prompt,
        "initial_score": score,
        "score": score,
        "source": source,
        "reason_codes": [reason_code] if reason_code else [],
        "applied_rule_ids": [rule_id] if rule_id else [],
        "excluded_reasons": [],
        "selected": False,
        "hard_required": hard_required,
        "hard_forbidden": hard_forbidden,
        "metadata": entry.metadata,
    }


def _merge_candidate(pool, category, code, score, source, reason_code, rule_id=None, hard_required=False, hard_forbidden=False):
    entry = _catalog_entry(category, code)
    if not entry:
        return
    existing = next((item for item in pool[category] if item["candidate_id"] == code), None)
    if not existing:
        pool[category].append(
            _candidate(
                entry,
                category,
                score,
                source,
                reason_code,
                rule_id=rule_id,
                hard_required=hard_required,
                hard_forbidden=hard_forbidden,
            )
        )
        return
    existing["score"] += score
    existing["hard_required"] = existing["hard_required"] or hard_required
    existing["hard_forbidden"] = existing["hard_forbidden"] or hard_forbidden
    if reason_code and reason_code not in existing["reason_codes"]:
        existing["reason_codes"].append(reason_code)
    if rule_id and rule_id not in existing["applied_rule_ids"]:
        existing["applied_rule_ids"].append(rule_id)
    if hard_required:
        existing["source"] = source


def _matching_rules(rule_type, predicate):
    rows = []
    for row in RuleEntry.objects.filter(rule_type=rule_type, enabled=True):
        if predicate(row.data):
            rows.append((row.rule_id, row.data))
    return rows


def _add_rule_candidates(pool, category, values, score, source, reason_code, rule_id):
    for code in _split(values):
        _merge_candidate(pool, category, code, score, source, reason_code, rule_id=rule_id)


def _match_catalog_code(category, text):
    text = str(text or "").strip().lower()
    if not text:
        return None
    catalog = CATEGORY_CATALOG[category]
    entries = list(CatalogEntry.objects.filter(catalog=catalog, enabled=True))
    aliases = {
        ("location", "카페"): "LOC_CAFE",
        ("location", "창가"): "LOC_WINDOW",
        ("location", "거리"): "LOC_STREET",
        ("location", "방"): "LOC_QUIET_ROOM",
        ("location", "해변"): "LOC_BEACH",
        ("action", "걷기"): "ACT_SLOW_WALK",
        ("action", "비 바라보기"): "ACT_WATCH_RAIN",
        ("action", "비를 피하기"): "ACT_SIT_QUIET",
        ("action", "발표하기"): "ACT_PRESENTATION_DONE",
        ("action", "시험 보기"): "ACT_HOLD_RESULT",
        ("objects", "머그잔"): "OBJ_MUG",
        ("objects", "찻잔"): "OBJ_TEA",
        ("objects", "우산"): "OBJ_UMBRELLA",
    }
    direct = aliases.get((category, text))
    if direct and _catalog_entry(category, direct):
        return direct
    for entry in entries:
        label = (entry.display_name or "").lower()
        alias_values = _split(entry.metadata.get("aliases"))
        if (label and (label in text or text in label)) or any(alias.lower() in text for alias in alias_values):
            return entry.code
    return None


def _profile_preferences(user):
    profile = getattr(user, "profile", None)
    if not profile:
        return set()
    return {str(value).strip() for value in [*(profile.hobbies or []), *(profile.interests or [])] if str(value).strip()}


def build_candidate_pool(analysis, style_id=None, user_profile=None):
    result = analysis.result if hasattr(analysis, "result") else analysis
    user = getattr(analysis, "user", None)
    pool = defaultdict(list)
    emotion = ((result.get("primary_emotion") or {}).get("code") if isinstance(result.get("primary_emotion"), dict)
               else result.get("primary_emotion")) or "SADNESS"
    intensity = result.get("emotion_intensity") or "MEDIUM"
    event_id = (result.get("event_type") or {}).get("id") or result.get("event_type_id") or "EVT_UNSPECIFIED"
    outcome = result.get("event_outcome") or "OUT_UNKNOWN"
    stage = result.get("event_stage") or "UNSPECIFIED"

    explicit_weather = result.get("explicit_weather")
    scene_weather = result.get("scene_weather") or explicit_weather
    weather_transition = result.get("weather_transition")
    weather_id = EXPLICIT_WEATHER_IDS.get(scene_weather)
    if weather_id:
        transition_driven = bool(
            weather_transition not in {None, "", "NONE", "UNKNOWN"}
            and scene_weather != explicit_weather
        )
        _merge_candidate(
            pool,
            "weather",
            weather_id,
            1000,
            "DERIVED_FROM_EXPLICIT_TIMELINE" if transition_driven else "EXPLICIT",
            "WEATHER_TRANSITION" if transition_driven else "EXPLICIT_WEATHER",
            hard_required=True,
        )

    explicit_mappings = (
        ("location", result.get("explicit_place"), "EXPLICIT_PLACE"),
        ("action", result.get("explicit_action"), "EXPLICIT_ACTION"),
    )
    for category, value, reason in explicit_mappings:
        code = _match_catalog_code(category, value)
        if code:
            _merge_candidate(pool, category, code, 1000, "EXPLICIT", reason, hard_required=True)
    for value in result.get("explicit_objects") or []:
        code = _match_catalog_code("objects", value)
        if code:
            _merge_candidate(pool, "objects", code, 1000, "EXPLICIT", "EXPLICIT_OBJECT", hard_required=True)

    emotion_rows = _matching_rules(
        "emotion_visual",
        lambda data: data.get("primary_emotion") == emotion
        and data.get("intensity") in ("", None, intensity),
    )
    if not emotion_rows:
        emotion_rows = _matching_rules("emotion_visual", lambda data: data.get("primary_emotion") == emotion)
    for rule_id, data in emotion_rows:
        field_map = {
            "weather": data.get("weather_candidates") or data.get("weather_id"),
            "lighting": data.get("lighting_candidates") or data.get("lighting_id"),
            "palette": data.get("palette_candidates") or data.get("palette_id"),
            "expression": data.get("expression_candidates") or data.get("expression_id"),
            "pose": data.get("pose_candidates") or data.get("pose_ids"),
            "effects": data.get("effect_candidates") or data.get("effect_id"),
            "composition": data.get("composition_candidates") or data.get("composition_id"),
        }
        for category, values in field_map.items():
            if category == "weather" and scene_weather:
                continue
            _add_rule_candidates(pool, category, values, 50, "EMOTION_VISUAL", "EMOTION_VISUAL", rule_id)

    event_rows = _matching_rules(
        "event_scene",
        lambda data: data.get("event_type_id") == event_id
        and data.get("outcome_condition") in ("", None, outcome)
        and data.get("stage_condition") in ("", None, stage),
    )
    for rule_id, data in event_rows:
        for category, field in (
            ("location", "location_candidates"),
            ("action", "action_candidates"),
            ("objects", "object_candidates"),
            ("effects", "effect_candidates"),
        ):
            _add_rule_candidates(pool, category, data.get(field), 60, "EVENT_RULE", "EVENT_CANDIDATE", rule_id)

    for field, rule_type, category_fields in (
        ("energy", "energy", (("pose", "pose_id"), ("composition", "composition_id"), ("action", "default_action"))),
        ("need", "need_environment", (("location", "location_candidates"), ("action", "action_candidates"),
                                      ("objects", "object_candidates"), ("lighting", "lighting_id"))),
    ):
        data_value = result.get(field)
        code = data_value.get("code") if isinstance(data_value, dict) else None
        source = result.get("field_sources", {}).get(f"{field}_code", "NOT_PROVIDED")
        confidence = _float(result.get("field_confidences", {}).get(f"{field}_code"))
        if not code or source in {"NOT_PROVIDED", "DEFAULT", "LOW_CONFIDENCE_INFERRED"}:
            continue
        score = 40 if source == "EXPLICIT" else (15 if source == "HIGH_CONFIDENCE_INFERRED" and confidence >= 0.75 else 0)
        if not score:
            continue
        for rule_id, data in _matching_rules(rule_type, lambda item, c=code, f=f"{field}_code": item.get(f) == c):
            for category, source_field in category_fields:
                _add_rule_candidates(pool, category, data.get(source_field), score, source, f"{field.upper()}_PREFERENCE", rule_id)

    preferences = _profile_preferences(user) if user_profile is None else set(user_profile)
    if preferences:
        for rule_id, data in _matching_rules("interest_scene", lambda item: item.get("display_name") in preferences):
            for category, field in (
                ("location", "location_candidates"),
                ("action", "action_candidates"),
                ("objects", "object_candidates"),
                ("effects", "effect_candidates"),
            ):
                _add_rule_candidates(pool, category, data.get(field), 5, "INTEREST", "INTEREST_OPTIONAL", rule_id)

    social = result.get("social_context", "NOT_DISCLOSED")
    social_source = result.get("field_sources", {}).get("social_context", "NOT_PROVIDED")
    social_confidence = _float(result.get("field_confidences", {}).get("social_context"))
    if social not in {"NOT_DISCLOSED", "ALONE"} and (
        social_source == "EXPLICIT" or (social_source == "HIGH_CONFIDENCE_INFERRED" and social_confidence >= 0.75)
    ):
        for rule in SocialCompanionRule.objects.filter(social_context=social, enabled=True):
            pool["companions"].append({
                "candidate_id": rule.rule_id,
                "category": "companions",
                "display_name": rule.companion_type,
                "visual_prompt": rule.visual_prompt,
                "initial_score": rule.weight,
                "score": rule.weight,
                "source": social_source,
                "reason_codes": ["SOCIAL_CONTEXT"],
                "applied_rule_ids": [rule.rule_id],
                "excluded_reasons": [],
                "selected": False,
                "hard_required": social_source == "EXPLICIT",
                "hard_forbidden": False,
                "metadata": {
                    "companion_count_max": rule.companion_count_max,
                    "privacy_note": rule.privacy_note,
                },
            })

    for category, codes in DEFAULTS.get(emotion, DEFAULTS["SADNESS"]).items():
        if category == "weather" and scene_weather:
            continue
        for index, code in enumerate(codes):
            _merge_candidate(pool, category, code, 20 - index, "SYMBOLIC_DEFAULT", "SYMBOLIC_SCENE")

    if scene_weather == "RAIN":
        for category, codes in {
            "location": ["LOC_WINDOW", "LOC_QUIET_ROOM", "LOC_CAFE", "LOC_STREET"],
            "action": ["ACT_WATCH_RAIN", "ACT_SIT_QUIET", "ACT_SLOW_WALK"],
            "lighting": ["LGT_COOL_WINDOW", "LGT_OVERCAST", "LGT_LAMP"],
            "palette": ["PAL_BLUE_GRAY", "PAL_LAVENDER_BLUE"],
            "pose": ["POSE_SAD_SEATED", "POSE_LOW"],
            "composition": ["COMP_OFF_CENTER_WINDOW", "COMP_CLOSE"],
        }.items():
            for index, code in enumerate(codes):
                _merge_candidate(pool, category, code, 200 - index, "EXPLICIT_CAUSE", "RAIN_SCENE_CUE")

    if weather_transition == "RAIN_TO_CLEAR":
        for category, codes in {
            "lighting": ["LGT_AFTER_RAIN", "LGT_GOLDEN", "LGT_WARM_SUN"],
            "palette": ["PAL_MINT_SKY", "PAL_LAVENDER_BLUE"],
            "effects": ["FX_AFTER_RAIN", "FX_RAIN"],
            "composition": ["COMP_PATH", "COMP_BALANCED"],
        }.items():
            for index, code in enumerate(codes):
                _merge_candidate(
                    pool,
                    category,
                    code,
                    250 - index,
                    "TIMELINE_TRANSITION",
                    "WEATHER_TRANSITION_TRACE",
                )

    previous_emotion = result.get("initial_emotion")
    if previous_emotion and previous_emotion != emotion:
        trace_candidates = {
            "SADNESS": {
                "palette": ["PAL_LAVENDER_BLUE", "PAL_BLUE_GRAY"],
                "effects": ["FX_AFTER_RAIN"],
            },
            "ANXIETY": {
                "palette": ["PAL_LAVENDER_BLUE"],
                "composition": ["COMP_PATH"],
            },
            "ANGER": {
                "palette": ["PAL_PLUM_CORAL"],
                "composition": ["COMP_DISTANCE"],
            },
            "JOY": {
                "palette": ["PAL_CORAL_GOLD"],
                "effects": ["FX_SPARKLE"],
            },
        }.get(previous_emotion, {})
        for category, codes in trace_candidates.items():
            for index, code in enumerate(codes):
                _merge_candidate(
                    pool,
                    category,
                    code,
                    100 - index,
                    "TIMELINE_TRANSITION",
                    "PREVIOUS_EMOTION_TRACE",
                )

    scene_time = result.get("scene_time") or {}
    time_range = set(scene_time.get("range") or [])
    range_source = scene_time.get("range_source")
    range_confidence = _float(scene_time.get("range_confidence"))
    if range_source == "EXPLICIT":
        time_score = 120
    elif range_source == "HIGH_CONFIDENCE_INFERRED" and range_confidence >= 0.75:
        time_score = 40
    elif range_source == "LOW_CONFIDENCE_INFERRED" and range_confidence > 0:
        time_score = 10
    else:
        time_score = 0
    time_lighting = []
    if "DAWN" in time_range:
        time_lighting.append("LGT_DAWN")
    if "MORNING" in time_range:
        time_lighting.append("LGT_MORNING")
    if "SUNSET" in time_range or "EVENING" in time_range:
        time_lighting.append("LGT_GOLDEN")
    if "NIGHT" in time_range:
        time_lighting.extend(["LGT_LAMP", "LGT_MOON"])
    for index, code in enumerate(dict.fromkeys(time_lighting)):
        _merge_candidate(
            pool,
            "lighting",
            code,
            max(1, time_score - index),
            range_source or "NOT_PROVIDED",
            "TIME_RANGE_ATMOSPHERE",
        )

    anchor = scene_time.get("anchor")
    if anchor in {"LEAVING_HOME", "RETURNING_HOME"}:
        for category, code in (
            ("location", "LOC_STREET"),
            ("action", "ACT_SLOW_WALK"),
            ("composition", "COMP_PATH"),
        ):
            _merge_candidate(
                pool,
                category,
                code,
                100,
                "EXPLICIT_EVENT_ANCHOR",
                "ROUTINE_ROUTE_ANCHOR",
            )

    negated = set(result.get("negated_elements") or [])
    if "RAIN" in negated:
        _merge_candidate(pool, "weather", "WTH_RAIN", -1000, "EXPLICIT_NEGATION", "NEGATED_RAIN", hard_forbidden=True)

    explicit_environment = result.get("explicit_environment")
    if explicit_environment in {"INDOOR", "OUTDOOR"}:
        expected = explicit_environment.lower()
        for item in pool.get("location", []):
            environment = str(item.get("metadata", {}).get("environment") or "").lower()
            if environment and environment != expected and not item.get("hard_required"):
                item["hard_forbidden"] = True
                item["score"] -= 1000
                item["excluded_reasons"].append("EXPLICIT_ENVIRONMENT_CONFLICT")
        conflicting_tag = "OUTDOOR" if explicit_environment == "INDOOR" else "INDOOR"
        for item in pool.get("action", []):
            required_tags = set(_split(item.get("metadata", {}).get("required_location_tags")))
            if conflicting_tag in required_tags and not item.get("hard_required"):
                item["hard_forbidden"] = True
                item["score"] -= 1000
                item["excluded_reasons"].append("EXPLICIT_ENVIRONMENT_CONFLICT")

    for category in SELECTED_KEYS:
        values = pool[category]
        values.sort(key=lambda item: (item["hard_required"], not item["hard_forbidden"], item["score"]), reverse=True)
        keep = values[:5]
        for forbidden in [item for item in values if item["hard_forbidden"] and item not in keep]:
            keep.append(forbidden)
        pool[category] = keep
    return dict(pool)


def _priority_map():
    result = {}
    for row in RuleEntry.objects.filter(rule_type="conflict_priority", enabled=True):
        group = row.data.get("rule_group")
        if group:
            result[group] = _int(row.data.get("priority_rank"), 999)
    return result


def resolve_scene_constraints(analysis, candidate_pool, safety_result=None):
    result = analysis.result if hasattr(analysis, "result") else analysis
    safety = safety_result or getattr(analysis, "safety_status", "SAFE")
    priorities = _priority_map()
    emotion = ((result.get("primary_emotion") or {}).get("code") if isinstance(result.get("primary_emotion"), dict)
               else result.get("primary_emotion"))
    constraints = {
        "hard_required": [],
        "hard_forbidden": [],
        "soft_preferences": [],
        "required_visual_cues": [],
        "min_required_visual_cues": 0,
        "reason_codes": [],
        "explicit_fact_constraints": [],
        "priority_map": priorities,
        "safety_status": safety,
    }
    if safety == "BLOCKED":
        constraints["hard_forbidden"].append({
            "type": "generation",
            "value": "IMAGE_GENERATION",
            "reason": "SAFETY_BLOCKED",
            "priority": priorities.get("SAFETY_HARD", 1),
        })
        return constraints

    for category, items in candidate_pool.items():
        for item in items:
            if item.get("hard_required"):
                constraint = {
                    "type": "candidate",
                    "category": category,
                    "value": item["candidate_id"],
                    "reason": next(iter(item["reason_codes"]), "EXPLICIT_FACT"),
                    "priority": priorities.get(next(iter(item["reason_codes"]), "EXPLICIT_FACT"), 3),
                }
                constraints["hard_required"].append(constraint)
                constraints["explicit_fact_constraints"].append(constraint)
            if item.get("hard_forbidden"):
                constraints["hard_forbidden"].append({
                    "type": "candidate",
                    "category": category,
                    "value": item["candidate_id"],
                    "reason": "EXPLICIT_NEGATION",
                    "priority": priorities.get("EXPLICIT_NEGATION", 2),
                })

    explicit_weather = result.get("explicit_weather")
    scene_weather = result.get("scene_weather") or explicit_weather
    weather_transition = result.get("weather_transition")
    if scene_weather == "RAIN":
        rain = _catalog_entry("weather", "WTH_RAIN")
        cues = _split((rain.metadata if rain else {}).get("required_visual_cues"))
        constraints["required_visual_cues"] = cues or ["visible steady rain or rain streaks", "wet pavement or puddles"]
        constraints["min_required_visual_cues"] = max(2, _int((rain.metadata if rain else {}).get("min_required_visual_cues"), 2))
        constraints["hard_forbidden"].extend([
            {"type": "visual_cue", "value": "clear sunny sky", "reason": "EXPLICIT_WEATHER", "priority": 4},
            {"type": "visual_cue", "value": "dry ground", "reason": "EXPLICIT_WEATHER", "priority": 4},
        ])
        constraints["reason_codes"].append("WEATHER_RAIN_VISIBLE")
    elif scene_weather == "AFTER_RAIN" and weather_transition == "RAIN_TO_CLEAR":
        after_rain = _catalog_entry("weather", "WTH_AFTER_RAIN")
        cues = _split((after_rain.metadata if after_rain else {}).get("required_visual_cues"))
        constraints["required_visual_cues"] = cues or [
            "wet pavement, puddles, or raindrops remaining on glass",
            "clearing sky or warm light breaking through clouds",
        ]
        constraints["min_required_visual_cues"] = max(
            2,
            _int((after_rain.metadata if after_rain else {}).get("min_required_visual_cues"), 2),
        )
        constraints["hard_forbidden"].extend([
            {
                "type": "visual_cue",
                "value": "heavy steady rain dominating the current scene",
                "reason": "WEATHER_TRANSITION",
                "priority": 4,
            },
            {
                "type": "visual_cue",
                "value": "completely dry ground",
                "reason": "WEATHER_TRANSITION",
                "priority": 4,
            },
        ])
        constraints["reason_codes"].append("WEATHER_TRANSITION_VISIBLE")

    if emotion in {"SADNESS", "ANGER", "ANXIETY"}:
        constraints["hard_forbidden"].extend([
            {"type": "visual_cue", "value": "broad cheerful smile", "reason": "EMOTION_VISUAL", "priority": 12},
            {"type": "visual_cue", "value": "celebratory posture", "reason": "EMOTION_VISUAL", "priority": 12},
        ])
    constraints["hard_forbidden"].extend(
        {"type": "visual_cue", "value": value, "reason": "EXPLICIT_NEGATION", "priority": 2}
        for value in result.get("negated_elements") or []
    )
    for category, items in candidate_pool.items():
        for item in items[:2]:
            if not item.get("hard_forbidden") and not item.get("hard_required"):
                constraints["soft_preferences"].append({
                    "category": category,
                    "value": item["candidate_id"],
                    "score": item["score"],
                    "reason_codes": item["reason_codes"],
                })
    return constraints


def _eligible(candidate_pool, category):
    return [item for item in candidate_pool.get(category, []) if not item.get("hard_forbidden")]


def _select_one(candidate_pool, category):
    items = _eligible(candidate_pool, category)
    if not items:
        return None
    return max(items, key=lambda item: (item.get("hard_required", False), item.get("score", 0)))


def _selected_candidate(candidate_pool, category, candidate_id):
    return next((item for item in candidate_pool.get(category, []) if item["candidate_id"] == candidate_id), None)


def deterministic_scene_plan(analysis, candidate_pool, constraints):
    result = analysis.result if hasattr(analysis, "result") else analysis
    selected = {}
    for category in ("weather", "location", "action", "pose", "expression", "lighting", "palette", "composition"):
        item = _select_one(candidate_pool, category)
        selected[SELECTED_KEYS[category]] = item["candidate_id"] if item else None
    selected["object_ids"] = [
        item["candidate_id"] for item in _eligible(candidate_pool, "objects")
        if item.get("hard_required")
    ][:3]
    if not selected["object_ids"]:
        selected["object_ids"] = [item["candidate_id"] for item in _eligible(candidate_pool, "objects")[:1]]
    selected["effect_ids"] = [item["candidate_id"] for item in _eligible(candidate_pool, "effects")[:1]]
    selected["companion_ids"] = [item["candidate_id"] for item in _eligible(candidate_pool, "companions")[:1]]

    weather = _selected_candidate(candidate_pool, "weather", selected.get("weather_id"))
    location = _selected_candidate(candidate_pool, "location", selected.get("location_id"))
    action = _selected_candidate(candidate_pool, "action", selected.get("action_id"))
    pose = _selected_candidate(candidate_pool, "pose", selected.get("pose_id"))
    expression = _selected_candidate(candidate_pool, "expression", selected.get("expression_id"))
    lighting = _selected_candidate(candidate_pool, "lighting", selected.get("lighting_id"))
    palette = _selected_candidate(candidate_pool, "palette", selected.get("palette_id"))
    composition = _selected_candidate(candidate_pool, "composition", selected.get("composition_id"))
    emotion = ((result.get("primary_emotion") or {}).get("code") if isinstance(result.get("primary_emotion"), dict)
               else result.get("primary_emotion")) or "SADNESS"
    emotion_phrase = {
        "JOY": "a gently positive emotional tone",
        "SADNESS": "a subdued contemplative emotional tone",
        "ANGER": "a restrained tense emotional tone",
        "ANXIETY": "a quiet uneasy emotional tone",
    }.get(emotion, "a restrained emotional tone")
    initial_emotion = result.get("initial_emotion")
    emotion_transition = result.get("emotion_transition") or "NONE"
    weather_transition = result.get("weather_transition") or "NONE"
    scene_time = result.get("scene_time") or {}
    time_range = list(scene_time.get("range") or [])
    time_source = scene_time.get("range_source") or "NOT_PROVIDED"
    time_phrase = ""
    if time_range:
        joined_range = " to ".join(item.lower().replace("_", " ") for item in time_range)
        if time_source == "EXPLICIT":
            time_phrase = f" at the explicitly stated {joined_range} time"
        else:
            time_phrase = (
                f" with a subtle {joined_range} atmosphere suggested by the routine anchor, "
                "without asserting an exact clock time"
            )
    cause = result.get("emotion_cause_summary") or "the stated cause"
    weather_prompt = (weather or {}).get("visual_prompt") if isinstance(weather, dict) else (weather["visual_prompt"] if weather else "")
    location_prompt = location["visual_prompt"] if location else "a modest anonymous setting"
    action_prompt = action["visual_prompt"] if action else "remaining still"
    pose_prompt = pose["visual_prompt"] if pose else "quiet natural body language"
    expression_prompt = expression["visual_prompt"] if expression else "a contemplative expression"

    object_placements = []
    for object_id in selected["object_ids"]:
        item = _selected_candidate(candidate_pool, "objects", object_id)
        if item:
            object_placements.append({
                "object_id": object_id,
                "placement": item["metadata"].get("placement_hint") or "placed naturally near the main character",
            })
    required_cues = list(constraints.get("required_visual_cues") or [])
    optional_cues = []
    if initial_emotion and initial_emotion != emotion:
        optional_cues.append(
            f"subtle environmental traces of earlier {initial_emotion.lower()}, while current "
            f"{emotion.lower()} remains dominant"
        )
    if weather_transition == "RAIN_TO_CLEAR":
        optional_cues.append(
            "lingering cool rain reflections behind the warmer clearing light"
        )
    avoid = [item["value"] for item in constraints.get("hard_forbidden", []) if item.get("type") == "visual_cue"]
    transition_summary = (
        f" The current expression is {emotion.lower()}, while the earlier "
        f"{initial_emotion.lower()} appears only as a subtle environmental trace."
        if emotion_transition not in {"NONE", "UNKNOWN"} and initial_emotion
        else ""
    )
    return {
        "scene_summary_ko": (
            f"{cause}의 변화가 보이는 공간에서 마지막 감정인 {emotion}을 중심으로, "
            "이전 상태의 흔적을 배경에 남긴 상징적 장면"
            if emotion_transition not in {"NONE", "UNKNOWN"} or weather_transition not in {"NONE", "UNKNOWN"}
            else f"{cause}가 보이는 공간에서 한 인물이 감정을 조용히 드러내는 상징적 장면"
        ),
        "scene_summary_en": (
            f"One original character in {location_prompt}{time_phrase}, with {cause} clearly "
            f"visible and {emotion_phrase}.{transition_summary}"
        ),
        "selected_elements": selected,
        "subject_description": "one original, fully clothed young adult character with generic non-identifying features",
        "body_language": pose_prompt,
        "gaze_direction": (action or {}).get("metadata", {}).get("gaze_target") or "toward the visible cause in the environment",
        "action_narrative": action_prompt,
        "spatial_relation": "the character occupies the foreground or midground while the cause remains clearly readable in the environment",
        "environment_narrative": (
            f"{location_prompt}; {weather_prompt or 'weather consistent with the selected candidate'}."
            + (
                " Wet surfaces and leftover droplets preserve the earlier rain, while the sky "
                "and light show that the weather is now clearing."
                if weather_transition == "RAIN_TO_CLEAR"
                else ""
            )
        ),
        "cause_visualization": (
            f"The emotional cause, {cause}, remains visually recognizable rather than being "
            "replaced by decorative mood. The final emotion controls the character; previous "
            "states remain only as environmental traces."
        ),
        "required_visual_cues": required_cues,
        "optional_visual_cues": optional_cues,
        "object_placements": object_placements,
        "lighting_narrative": lighting["visual_prompt"] if lighting else "soft scene-consistent light",
        "palette_narrative": palette["visual_prompt"] if palette else "a restrained scene-consistent palette",
        "composition_narrative": composition["visual_prompt"] if composition else "an eye-level balanced composition",
        "avoid_visuals": list(dict.fromkeys(avoid)),
        "director_confidence": 0.82,
        "director_source": "deterministic-fallback-v2.1-timeline",
    }


def _director_payload(analysis, candidate_pool, constraints, repair_errors=None):
    result = analysis.result if hasattr(analysis, "result") else analysis
    safe_analysis = {
        key: result.get(key)
        for key in (
            "primary_emotion",
            "initial_emotion",
            "final_emotion",
            "secondary_emotion",
            "emotion_transition",
            "emotion_intensity",
            "emotion_cause_type",
            "emotion_cause_summary",
            "explicit_weather",
            "initial_weather",
            "final_weather",
            "weather_transition",
            "scene_weather",
            "explicit_time",
            "scene_time",
            "timeline",
            "explicit_environment",
            "explicit_place",
            "explicit_action",
            "explicit_objects",
            "negated_elements",
            "evidence_map",
        )
    }
    candidates = {
        category: [
            {
                "candidate_id": item["candidate_id"],
                "display_name": item["display_name"],
                "visual_prompt": item["visual_prompt"],
                "score": item["score"],
                "hard_required": item["hard_required"],
                "hard_forbidden": item["hard_forbidden"],
                "metadata": item["metadata"],
            }
            for item in items
        ]
        for category, items in candidate_pool.items()
    }
    payload = {
        "analysis": safe_analysis,
        "candidate_pool": candidates,
        "constraints": constraints,
        "output_contract": {
            "scene_summary_ko": "string",
            "scene_summary_en": "string",
            "selected_elements": SELECTED_KEYS,
            "subject_description": "string",
            "body_language": "string",
            "gaze_direction": "string",
            "action_narrative": "string",
            "spatial_relation": "string",
            "environment_narrative": "string",
            "cause_visualization": "string",
            "required_visual_cues": ["string"],
            "optional_visual_cues": ["string"],
            "object_placements": [{"object_id": "catalog id", "placement": "string"}],
            "lighting_narrative": "string",
            "palette_narrative": "string",
            "composition_narrative": "string",
            "avoid_visuals": ["string"],
            "director_confidence": "0..1",
        },
    }
    if repair_errors:
        payload["repair_errors"] = repair_errors
        payload["repair_instruction"] = "Correct only these errors and preserve all valid selections."
    return payload


def llm_direct_scene(analysis, candidate_pool, constraints, style_id=None, repair_errors=None):
    if (
        _running_tests()
        or not getattr(settings, "EMOTION_CARD_SCENE_DIRECTOR_ENABLED", True)
        or not getattr(settings, "OPENAI_API_KEY", "")
    ):
        return None, None
    model = (
        getattr(settings, "EMOTION_CARD_SCENE_DIRECTOR_MODEL", "")
        or getattr(settings, "EMOTION_CARD_ANALYSIS_MODEL", "")
        or getattr(settings, "EMOTION_CARD_LLM_MODEL", "")
        or os.environ.get("OPENAI_MODEL", "gpt-5.4-mini")
    )
    try:
        from openai import OpenAI

        response = OpenAI(api_key=settings.OPENAI_API_KEY).chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": SCENE_DIRECTOR_SYSTEM},
                {
                    "role": "user",
                    "content": json.dumps(_director_payload(analysis, candidate_pool, constraints, repair_errors), ensure_ascii=False),
                },
            ],
            max_completion_tokens=1800,
            response_format={"type": "json_object"},
        )
        return json.loads(response.choices[0].message.content), model
    except Exception:
        logger.exception("[emotion_card] scene director failed (model=%s)", model)
        return None, model


def _all_scene_text(scene_plan):
    values = []
    for key, value in scene_plan.items():
        if key in {"avoid_visuals", "validation_errors"}:
            continue
        if isinstance(value, str):
            values.append(value)
        elif isinstance(value, list):
            values.extend(str(item) for item in value)
    return " ".join(values).lower()


def validate_scene_plan(scene_plan, analysis, candidate_pool, constraints):
    errors = []
    if not isinstance(scene_plan, dict):
        return False, ["SCENE_PLAN_NOT_OBJECT"]
    selected = scene_plan.get("selected_elements")
    if not isinstance(selected, dict):
        return False, ["SELECTED_ELEMENTS_MISSING"]

    for category, key in SELECTED_KEYS.items():
        values = selected.get(key, [])
        values = values if isinstance(values, list) else [values]
        allowed = {item["candidate_id"] for item in candidate_pool.get(category, []) if not item.get("hard_forbidden")}
        for value in [value for value in values if value]:
            if value not in allowed:
                errors.append(f"ID_NOT_IN_CANDIDATE_POOL:{category}:{value}")

    for required in constraints.get("hard_required", []):
        if required.get("type") != "candidate":
            continue
        key = SELECTED_KEYS.get(required.get("category"))
        value = selected.get(key)
        values = value if isinstance(value, list) else [value]
        if required.get("value") not in values:
            errors.append(f"HARD_REQUIRED_MISSING:{required.get('category')}:{required.get('value')}")

    for forbidden in constraints.get("hard_forbidden", []):
        if forbidden.get("type") != "candidate":
            continue
        key = SELECTED_KEYS.get(forbidden.get("category"))
        value = selected.get(key)
        values = value if isinstance(value, list) else [value]
        if forbidden.get("value") in values:
            errors.append(f"HARD_FORBIDDEN_SELECTED:{forbidden.get('category')}:{forbidden.get('value')}")

    cues = [str(item).lower() for item in scene_plan.get("required_visual_cues") or []]
    if len(cues) < _int(constraints.get("min_required_visual_cues")):
        errors.append("REQUIRED_VISUAL_CUES_INSUFFICIENT")
    required_tokens = constraints.get("required_visual_cues") or []
    for expected in required_tokens:
        alternatives = [part.strip().lower() for part in re.split(r"\s+or\s+|\|", expected) if part.strip()]
        if alternatives and not any(any(alt in cue or cue in alt for cue in cues) for alt in alternatives):
            errors.append(f"REQUIRED_VISUAL_CUE_MISSING:{expected}")

    scene_text = _all_scene_text(scene_plan)
    for forbidden in constraints.get("hard_forbidden", []):
        if forbidden.get("type") == "visual_cue":
            cue = str(forbidden.get("value") or "").lower()
            if cue and cue in scene_text:
                errors.append(f"FORBIDDEN_VISUAL_PRESENT:{cue}")

    object_ids = selected.get("object_ids") or []
    if len(object_ids) > 3:
        errors.append("OBJECT_MAX_EXCEEDED")
    for object_id in object_ids:
        item = _selected_candidate(candidate_pool, "objects", object_id)
        max_count = _int((item or {}).get("metadata", {}).get("max_count"), 1)
        if object_ids.count(object_id) > max_count:
            errors.append(f"OBJECT_ITEM_MAX_EXCEEDED:{object_id}")

    companion_ids = selected.get("companion_ids") or []
    if len(companion_ids) > 1:
        errors.append("COMPANION_RULE_MAX_EXCEEDED")

    result = analysis.result if hasattr(analysis, "result") else analysis
    explicit_place = result.get("explicit_place")
    explicit_action = result.get("explicit_action")
    explicit_objects = result.get("explicit_objects") or []
    for field, value in (("explicit_place", explicit_place), ("explicit_action", explicit_action)):
        if value and value.lower() not in scene_text:
            mapped_category = "location" if field == "explicit_place" else "action"
            mapped = _match_catalog_code(mapped_category, value)
            selected_key = SELECTED_KEYS[mapped_category]
            if not mapped or selected.get(selected_key) != mapped:
                errors.append(f"EXPLICIT_FACT_NOT_PRESERVED:{field}")
    for value in explicit_objects:
        mapped = _match_catalog_code("objects", value)
        if mapped and mapped not in object_ids:
            errors.append(f"EXPLICIT_FACT_NOT_PRESERVED:object:{value}")

    if constraints.get("safety_status") == "BLOCKED":
        errors.append("SAFETY_BLOCKED")
    if any(token in scene_text for token in ("readable text", "company logo", "specific address", "identifiable real person")):
        errors.append("PRIVACY_OR_TEXT_CONFLICT")
    if "style_id" in selected or any(key.startswith("style") for key in selected):
        errors.append("STYLE_MUST_NOT_SELECT_SCENE_IDS")
    return not errors, list(dict.fromkeys(errors))


def direct_and_validate_scene(analysis, candidate_pool, constraints):
    plan, model = llm_direct_scene(analysis, candidate_pool, constraints)
    used_llm = plan is not None
    if plan is None:
        plan = deterministic_scene_plan(analysis, candidate_pool, constraints)
    valid, errors = validate_scene_plan(plan, analysis, candidate_pool, constraints)
    repair_count = 0

    if not valid and used_llm and getattr(settings, "EMOTION_CARD_SCENE_REPAIR_ENABLED", True):
        repair_count = 1
        repaired, repair_model = llm_direct_scene(analysis, candidate_pool, constraints, repair_errors=errors)
        if repaired is not None:
            plan = repaired
            model = repair_model or model
            valid, errors = validate_scene_plan(plan, analysis, candidate_pool, constraints)

    if not valid:
        plan = deterministic_scene_plan(analysis, candidate_pool, constraints)
        valid, errors = validate_scene_plan(plan, analysis, candidate_pool, constraints)
        if not valid:
            logger.warning("[emotion_card] deterministic scene validation errors: %s", errors)

    plan["validation_status"] = "VALID" if valid else "FALLBACK_WITH_WARNINGS"
    plan["validation_errors"] = errors
    plan["repair_count"] = repair_count
    plan["director_model"] = (
        model or "deterministic-scene-director-v2.1-timeline"
    )
    plan["director_prompt_version"] = DIRECTOR_PROMPT_VERSION
    return plan


def selected_candidate_scores(candidate_pool, selected_elements):
    selected = {}
    for category, key in SELECTED_KEYS.items():
        values = selected_elements.get(key, [])
        values = values if isinstance(values, list) else [values]
        for value in [value for value in values if value]:
            item = _selected_candidate(candidate_pool, category, value)
            if item:
                item["selected"] = True
                selected[value] = {
                    "category": category,
                    "initial_score": item["initial_score"],
                    "final_score": item["score"],
                    "source": item["source"],
                    "reason_codes": item["reason_codes"],
                    "applied_rule_ids": item["applied_rule_ids"],
                    "hard_required": item["hard_required"],
                    "hard_forbidden": item["hard_forbidden"],
                }
    return selected

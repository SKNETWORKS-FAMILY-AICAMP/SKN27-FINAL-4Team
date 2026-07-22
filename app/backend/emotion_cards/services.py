import base64
import hashlib
import json
import logging
import random
import re
import uuid
from html import escape
from pathlib import Path

from django.conf import settings
from django.db import transaction
from django.utils import timezone

from .analysis import extract_analysis, sanitize_analysis_text
from .models import (
    CatalogEntry,
    EmotionCardAnalysis,
    EmotionCardJob,
    EmotionCardScene,
    FeatureCode,
    GeneratedEmotionCard,
    RuleEntry,
    SocialCompanionRule,
)
from .prompt_compiler import PROMPT_VERSION, build_image_prompt
from .scene_pipeline import (
    SCENE_VERSION,
    build_candidate_pool,
    direct_and_validate_scene,
    resolve_scene_constraints,
    selected_candidate_scores,
)


logger = logging.getLogger("emotion_cards")

NEGATIVE_EMOTIONS = {"SADNESS", "ANGER", "ANXIETY"}
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
GENDER_TO_CARD_GENDER = {
    "남": "MALE",
    "남성": "MALE",
    "남자": "MALE",
    "male": "MALE",
    "여": "FEMALE",
    "여성": "FEMALE",
    "여자": "FEMALE",
    "female": "FEMALE",
}


def daily_generation_queryset(user):
    """Count accepted jobs rather than saved image files.

    Storage changes must not weaken the daily generation limit.
    """
    return EmotionCardJob.objects.filter(
        user=user,
        created_at__date=timezone.localdate(),
    )


def _catalog(catalog, code):
    if not code:
        return None
    return CatalogEntry.objects.filter(catalog=catalog, code=code, enabled=True).first()


def _label(group, code):
    if not code:
        return None
    item = FeatureCode.objects.filter(group=group, code=code).first()
    return item.label if item else code


def _entry_or_text(catalog, code, fallback):
    entry = _catalog(catalog, code)
    return {
        "id": code,
        "label": entry.display_name if entry else fallback,
        "visual_prompt": entry.visual_prompt if entry else fallback,
    }


def _card_gender_for_user(user):
    profile = getattr(user, "profile", None) if user else None
    gender = str(getattr(profile, "gender", "") or "").strip().lower()
    return GENDER_TO_CARD_GENDER.get(gender) or random.choice(("MALE", "FEMALE"))


def _safety_rules_status(text):
    policy_status = {
        "BLOCK_AND_SUPPORT": "BLOCKED",
        "BLOCK_OR_REVIEW": "REVIEW",
        "REVIEW": "REVIEW",
        "REFRAME": "REFRAMED",
    }
    rank = {"SAFE": 0, "REFRAMED": 1, "REVIEW": 2, "BLOCKED": 3}
    worst = "SAFE"
    for row in RuleEntry.objects.filter(rule_type="safety", enabled=True):
        hints = [hint for hint in str(row.data.get("keyword_hints") or "").split("|") if hint]
        if any(hint.lower() in text for hint in hints):
            candidate = policy_status.get(row.data.get("policy"), "SAFE")
            if rank[candidate] > rank[worst]:
                worst = candidate
    return worst


def safety_status(payload):
    text = " ".join(
        str(payload.get(key, ""))
        for key in ("emotion_text", "event_text", "memory_text")
    ).lower()
    critical = ("자해", "죽고 싶", "죽고싶", "사라지고 싶", "해치고 싶")
    if any(term in text for term in critical):
        return "BLOCKED"
    try:
        return _safety_rules_status(text)
    except Exception:
        logger.exception("[emotion_card] local safety rule lookup failed")
        return "SAFE"


def analyze(payload, user):
    status = safety_status(payload)
    normalized, facts = extract_analysis(
        payload,
        allow_llm=status == "SAFE",
    )
    emotion = facts.get("primary_emotion")
    event_id = facts.get("event_type_id") or "EVT_UNSPECIFIED"
    event = _catalog("event", event_id)
    energy_code = facts.get("energy_code")
    need_code = facts.get("need_code")
    memory_focus = normalized.get("memory_text") or facts.get("emotion_cause_summary") or ""

    result = {
        **facts,
        "primary_emotion": {
            "code": emotion,
            "label": _label("PRIMARY_EMOTION", emotion),
        },
        "state_tags": facts.get("state_tags") or [],
        "event_type": {
            "id": event_id,
            "label": event.display_name if event else event_id,
        },
        "event_domain": facts.get("event_domain") or "UNKNOWN",
        "energy": (
            {"code": energy_code, "label": _label("ENERGY", energy_code)}
            if energy_code
            else None
        ),
        "need": (
            {"code": need_code, "label": _label("NEED", need_code)}
            if need_code
            else None
        ),
        "memory_focus": sanitize_analysis_text(memory_focus, 200),
        "activity_sequence": facts.get("activity_sequence") or [],
        "analysis_source": facts.get(
            "analysis_model",
            "deterministic-timeline-v2.1",
        ),
    }
    return EmotionCardAnalysis.objects.create(
        user=user,
        raw_input={key: str(value)[:500] for key, value in normalized.items()},
        result=result,
        analysis_status=facts.get("analysis_status", "CLEAR"),
        safety_status=status,
    )


def update_analysis(analysis, values):
    result = dict(analysis.result)
    for key in ("energy_code", "need_code"):
        if key not in values:
            continue
        group = "ENERGY" if key == "energy_code" else "NEED"
        nested = "energy" if key == "energy_code" else "need"
        result[key] = values[key]
        result[nested] = {"code": values[key], "label": _label(group, values[key])}
        result.setdefault("field_sources", {})[key] = "EXPLICIT"
        result.setdefault("field_confidences", {})[key] = 1.0
    if "primary_emotion" in values:
        code = values["primary_emotion"]
        result["primary_emotion"] = {
            "code": code,
            "label": _label("PRIMARY_EMOTION", code),
        }
        result["final_emotion"] = code
        initial_emotion = result.get("initial_emotion")
        result["secondary_emotion"] = (
            initial_emotion
            if initial_emotion and initial_emotion != code
            else None
        )
        result["emotion_transition"] = (
            f"{initial_emotion}_TO_{code}"
            if initial_emotion and initial_emotion != code
            else "NONE"
        )
        result.setdefault("field_sources", {})["primary_emotion"] = "EXPLICIT"
        result.setdefault("field_confidences", {})["primary_emotion"] = 1.0
    if "memory_focus" in values:
        result["memory_focus"] = sanitize_analysis_text(values["memory_focus"], 200)
    analysis.result = result
    analysis.save(update_fields=["result", "updated_at"])
    analysis.scenes.filter(invalidated=False).update(invalidated=True)
    return analysis


def _message_rule(emotion, outcome, need):
    best, best_weight = None, -1
    for row in RuleEntry.objects.filter(rule_type="message_mapping", enabled=True):
        data = row.data
        comparisons = (
            ("primary_emotion", emotion),
            ("event_outcome", outcome),
            ("need_code", need),
        )
        specified = [
            (data.get(field), actual)
            for field, actual in comparisons
            if data.get(field)
        ]
        if not specified or any(expected != actual for expected, actual in specified):
            continue
        weight = int(data.get("weight") or 0)
        if weight > best_weight:
            best = data.get("message_id")
            best_weight = weight
    return best


def _legacy_companion(selected_ids, social):
    if not selected_ids:
        return None
    rule = SocialCompanionRule.objects.filter(
        rule_id=selected_ids[0],
        enabled=True,
    ).first()
    if not rule:
        return None
    return {
        "social_context": social,
        "companion_type": rule.companion_type,
        "count_max": rule.companion_count_max,
        "visual_prompt": rule.visual_prompt,
        "privacy_note": rule.privacy_note,
    }


def build_scene(analysis):
    if analysis.safety_status not in {"SAFE", "REFRAMED"}:
        return None

    result = analysis.result or {}
    emotion = (result.get("primary_emotion") or {}).get("code") or "SADNESS"
    need = (result.get("need") or {}).get("code")
    energy = (result.get("energy") or {}).get("code")
    event_id = (result.get("event_type") or {}).get("id", "EVT_UNSPECIFIED")
    social = result.get("social_context", "NOT_DISCLOSED")

    candidate_pool = build_candidate_pool(analysis)
    constraints = resolve_scene_constraints(
        analysis,
        candidate_pool,
        analysis.safety_status,
    )
    plan = direct_and_validate_scene(analysis, candidate_pool, constraints)
    selected = plan.get("selected_elements") or {}
    scores = selected_candidate_scores(candidate_pool, selected)

    weather = _entry_or_text(
        "weather",
        selected.get("weather_id"),
        "scene-consistent weather",
    )
    location = _entry_or_text(
        "location",
        selected.get("location_id"),
        "an anonymous setting",
    )
    action = _entry_or_text(
        "action",
        selected.get("action_id"),
        "a quiet safe action",
    )
    lighting = _entry_or_text(
        "lighting",
        selected.get("lighting_id"),
        "scene-consistent lighting",
    )
    expression = _entry_or_text(
        "character_visual",
        selected.get("expression_id"),
        "a restrained expression",
    )
    pose = _entry_or_text(
        "character_visual",
        selected.get("pose_id"),
        "quiet body language",
    )
    objects = [
        _entry_or_text("object", code, "a small anonymous object")
        for code in (selected.get("object_ids") or [])[:3]
    ]
    companion = _legacy_companion(selected.get("companion_ids") or [], social)
    message_code = (
        _message_rule(emotion, result.get("event_outcome", "OUT_UNKNOWN"), need)
        or "MSG_CARE"
    )
    message = _entry_or_text(
        "message",
        message_code,
        "Take gentle care of today.",
    )

    mapping_reason_codes = list(dict.fromkeys([
        *constraints.get("reason_codes", []),
        *[
            reason
            for item in scores.values()
            for reason in [
                *item.get("reason_codes", []),
                *item.get("applied_rule_ids", []),
            ]
        ],
    ]))
    spec = {
        "scene_version": SCENE_VERSION,
        **plan,
        "raw_text_safe": sanitize_analysis_text(result.get("raw_text"), 200),
        "emotion_cause_type": result.get("emotion_cause_type"),
        "emotion_cause_summary": result.get("emotion_cause_summary"),
        "explicit_fact_constraints": constraints.get(
            "explicit_fact_constraints",
            [],
        ),
        "candidate_pool": candidate_pool,
        "hard_constraints": {
            "required": constraints.get("hard_required", []),
            "forbidden": constraints.get("hard_forbidden", []),
        },
        "soft_preferences": constraints.get("soft_preferences", []),
        "selected_candidate_scores": scores,
        "evidence_map": result.get("evidence_map", {}),
        "weather": weather,
        "location": location,
        "action": action,
        "objects": objects,
        "lighting": lighting,
        "expression": expression,
        "pose": pose,
        "companion": companion,
        "message": message,
        "memory_focus": result.get("memory_focus", ""),
        "primary_emotion": emotion,
        "initial_emotion": result.get("initial_emotion"),
        "final_emotion": result.get("final_emotion") or emotion,
        "secondary_emotion": result.get("secondary_emotion"),
        "emotion_transition": result.get("emotion_transition", "NONE"),
        "initial_weather": result.get("initial_weather"),
        "final_weather": result.get("final_weather"),
        "weather_transition": result.get("weather_transition", "NONE"),
        "scene_weather": (
            result.get("scene_weather")
            or result.get("explicit_weather")
        ),
        "scene_time": result.get("scene_time") or {},
        "timeline": result.get("timeline") or [],
        "energy_code": energy,
        "need_code": need,
        "event_type": event_id,
        "social_context": social,
        "character": _card_gender_for_user(analysis.user),
        "mapping_reason_codes": mapping_reason_codes,
        "prompt_version": PROMPT_VERSION,
    }
    digest = hashlib.sha256(
        json.dumps(
            spec,
            ensure_ascii=False,
            sort_keys=True,
            default=str,
        ).encode()
    ).hexdigest()
    styles = list(
        CatalogEntry.objects.filter(
            catalog="style",
            enabled=True,
            metadata__preserve_scene=True,
        ).values("code", "display_name")
    )
    if not styles:
        styles = list(
            CatalogEntry.objects.filter(
                catalog="style",
                enabled=True,
            ).values("code", "display_name")
        )
    return EmotionCardScene.objects.create(
        user=analysis.user,
        analysis=analysis,
        scene_hash=digest,
        scene_spec=spec,
        available_styles=styles,
        safety_status=analysis.safety_status,
    )


def _build_image_prompt(spec, style_id):
    return build_image_prompt(spec, style_id)


def _build_fallback_card_svg(spec):
    emotion = escape(str(spec.get("primary_emotion", "TODAY")))
    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="1024" height="1536" viewBox="0 0 1024 1536" role="img" aria-label="{emotion} emotional card preview">
  <defs>
    <linearGradient id="sky" x1="0" y1="0" x2="1" y2="1">
      <stop stop-color="#261349"/>
      <stop offset=".52" stop-color="#5d467e"/>
      <stop offset="1" stop-color="#8292aa"/>
    </linearGradient>
    <radialGradient id="glow" cx="50%" cy="29%" r="48%">
      <stop stop-color="#fff0c9" stop-opacity=".8"/>
      <stop offset="1" stop-color="#ffc47d" stop-opacity="0"/>
    </radialGradient>
  </defs>
  <rect width="1024" height="1536" rx="56" fill="url(#sky)"/>
  <rect width="1024" height="1536" rx="56" fill="url(#glow)"/>
  <path d="M0 1100 C170 960 330 1170 500 1035 S800 980 1024 1105 V1536 H0Z" fill="#291447" fill-opacity=".68"/>
  <circle cx="512" cy="448" r="158" fill="#fff0ba" fill-opacity=".7"/>
</svg>"""


def _store_fallback_card_image(spec):
    filename = f"emotion_cards/fallback-{uuid.uuid4().hex}.svg"
    target = Path(settings.MEDIA_ROOT) / filename
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(_build_fallback_card_svg(spec), encoding="utf-8")
    return f"{settings.MEDIA_URL}{filename}"


def ensure_card_image(card):
    if card.image_url:
        return card
    card.image_url = _store_fallback_card_image(card.scene.scene_spec)
    card.save(update_fields=["image_url"])
    return card


def _delete_card_image_file(image_url):
    """Delete only files owned by this app under MEDIA_ROOT."""
    media_url = str(settings.MEDIA_URL)
    if not image_url or not image_url.startswith(media_url):
        return

    media_root = Path(settings.MEDIA_ROOT).resolve()
    target = (media_root / image_url.removeprefix(media_url).lstrip('/')).resolve()
    try:
        target.relative_to(media_root)
    except ValueError:
        logger.warning("[emotion_card] refused to delete a path outside MEDIA_ROOT")
        return

    try:
        target.unlink(missing_ok=True)
    except OSError:
        logger.exception("[emotion_card] failed to delete previous card image: %s", target)


def _delete_previous_cards(user, current_card_id):
    """Keep just the latest completed card for each user."""
    previous_cards = list(GeneratedEmotionCard.objects.filter(user=user).exclude(id=current_card_id))
    for previous_card in previous_cards:
        _delete_card_image_file(previous_card.image_url)
    if previous_cards:
        GeneratedEmotionCard.objects.filter(id__in=[card.id for card in previous_cards]).delete()


def _scene_label(spec, key, fallback):
    return (spec.get(key) or {}).get("label") or fallback


def _record_generation_prompt(scene, style_id, prompt, model, size, quality):
    spec = dict(scene.scene_spec or {})
    generation_prompts = dict(spec.get("generation_prompts") or {})
    generation_prompts[style_id] = {
        "final_prompt": prompt,
        "image_model": model,
        "image_size": size,
        "image_quality": quality,
        "style_id": style_id,
        "prompt_version": PROMPT_VERSION,
        "generated_at": timezone.now().isoformat(),
    }
    spec["generation_prompts"] = generation_prompts
    spec["final_prompt"] = prompt
    spec["prompt_version"] = PROMPT_VERSION
    scene.scene_spec = spec
    scene.save(update_fields=["scene_spec"])
    return spec


def _create_card(job, image_url):
    spec = job.scene.scene_spec
    weather = _scene_label(spec, "weather", "weather")
    action = _scene_label(spec, "action", "quiet moment")
    location = _scene_label(spec, "location", "anonymous place")
    card = GeneratedEmotionCard.objects.create(
        user=job.user,
        scene=job.scene,
        style_id=job.style_id,
        image_url=image_url,
        image_alt=f"{weather}, {action}",
        summary=f"{spec.get('primary_emotion', 'TODAY')} · {weather} · {location}",
    )
    job.status = "COMPLETED"
    job.progress = 100
    job.card = card
    job.save(update_fields=["status", "progress", "card", "updated_at"])
    _delete_previous_cards(job.user, card.id)
    return job


def _fake_complete(job):
    model = getattr(settings, "EMOTION_CARD_IMAGE_MODEL", "gpt-image-2")
    size = getattr(settings, "EMOTION_CARD_IMAGE_SIZE", "1024x1536")
    quality = getattr(settings, "EMOTION_CARD_IMAGE_QUALITY", "medium")
    prompt = _build_image_prompt(job.scene.scene_spec, job.style_id)
    spec = _record_generation_prompt(
        job.scene,
        job.style_id,
        prompt,
        model,
        size,
        quality,
    )
    return _create_card(job, _store_fallback_card_image(spec))


def _passes_moderation(text):
    model = getattr(settings, "EMOTION_CARD_MODERATION_MODEL", "") or "omni-moderation-latest"
    api_key = getattr(settings, "OPENAI_API_KEY", "")
    if not model or not api_key:
        return True
    try:
        from openai import OpenAI

        result = OpenAI(api_key=api_key).moderations.create(
            model=model,
            input=text,
        )
        return not result.results[0].flagged
    except Exception:
        logger.exception("[emotion_card] optional moderation request failed")
        return True


def _generate_image_bytes(client, model, prompt, size, quality):
    response = client.images.generate(
        model=model,
        prompt=prompt,
        size=size,
        quality=quality,
    )
    return base64.b64decode(response.data[0].b64_json)


def _real_complete(job):
    api_key = getattr(settings, "OPENAI_API_KEY", "")
    model = getattr(settings, "EMOTION_CARD_IMAGE_MODEL", "gpt-image-2")
    if not api_key or not model:
        job.status = "FAILED"
        job.error_code = "EMOTION_CARD_PROVIDER_NOT_CONFIGURED"
        job.save(update_fields=["status", "error_code", "updated_at"])
        return job

    size = getattr(settings, "EMOTION_CARD_IMAGE_SIZE", "1024x1536")
    quality = getattr(settings, "EMOTION_CARD_IMAGE_QUALITY", "medium")
    prompt = _build_image_prompt(job.scene.scene_spec, job.style_id)
    _record_generation_prompt(
        job.scene,
        job.style_id,
        prompt,
        model,
        size,
        quality,
    )
    if not _passes_moderation(prompt):
        job.status = "BLOCKED"
        job.error_code = "EMOTION_CARD_MODERATION_BLOCKED"
        job.save(update_fields=["status", "error_code", "updated_at"])
        return job

    try:
        from openai import OpenAI

        image_bytes = _generate_image_bytes(
            OpenAI(api_key=api_key),
            model,
            prompt,
            size,
            quality,
        )
        filename = f"emotion_cards/{uuid.uuid4().hex}.png"
        target = Path(settings.MEDIA_ROOT) / filename
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(image_bytes)
        return _create_card(job, f"{settings.MEDIA_URL}{filename}")
    except Exception:
        logger.exception(
            "[emotion_card] image generation failed (model=%s size=%s quality=%s)",
            model,
            size,
            quality,
        )
        job.status = "FAILED"
        job.error_code = "EMOTION_CARD_IMAGE_PROVIDER_FAILED"
        job.save(update_fields=["status", "error_code", "updated_at"])
        return job


def create_generation_job(scene, style_id, user, idempotency_key=None):
    key = idempotency_key or uuid.uuid4().hex
    with transaction.atomic():
        if (
            scene.user_id != user.id
            or scene.invalidated
            or scene.safety_status not in {"SAFE", "REFRAMED"}
        ):
            raise ValueError("EMOTION_CARD_SCENE_BLOCKED")
        daily_limit = int(
            getattr(settings, "EMOTION_CARD_MAX_DAILY_GENERATIONS", 10)
        )
        if (
            daily_limit > 0
            and daily_generation_queryset(user).count() >= daily_limit
        ):
            raise ValueError("EMOTION_CARD_RATE_LIMITED")
        if style_id not in {
            style["code"]
            for style in scene.available_styles
        }:
            raise ValueError("EMOTION_CARD_STYLE_NOT_FOUND")
        existing = EmotionCardJob.objects.filter(
            user=user,
            idempotency_key=key,
        ).first()
        if existing:
            return existing, True
        job = EmotionCardJob.objects.create(
            user=user,
            scene=scene,
            style_id=style_id,
            idempotency_key=key,
            status="QUEUED",
            progress=10,
        )
    provider = (
        _real_complete
        if getattr(settings, "EMOTION_CARD_ENABLE_REAL_IMAGE_API", False)
        else _fake_complete
    )
    return provider(job), False

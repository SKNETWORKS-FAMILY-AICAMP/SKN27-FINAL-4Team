from .models import CatalogEntry


PROMPT_VERSION = "emotion-card-image-v2.1-timeline"
PROMPT_MAX_CHARS = 7000

HUMAN_CHARACTERS = {
    "MALE": (
        "one original, warm young adult man with generic non-identifying facial features, "
        "simple modern clothing, natural anatomy, fully clothed and non-sexualized"
    ),
    "FEMALE": (
        "one original, warm young adult woman with generic non-identifying facial features, "
        "simple modern clothing, natural anatomy, fully clothed and non-sexualized"
    ),
}


def _text(value, limit=800):
    return " ".join(str(value or "").split())[:limit]


def _split(value):
    if isinstance(value, list):
        return [_text(item, 200) for item in value if _text(item, 200)]
    return [_text(item, 200) for item in str(value or "").split("|") if _text(item, 200)]


def _style(style_id):
    entry = CatalogEntry.objects.filter(catalog="style", code=style_id, enabled=True).first()
    metadata = entry.metadata if entry else {}
    return {
        "rendering_prompt": _text((entry.visual_prompt if entry else "") or f"{style_id} illustration rendering", 900),
        "line_style": _text(metadata.get("line_style"), 400),
        "texture": _text(metadata.get("texture"), 400),
        "shading_method": _text(metadata.get("shading_method"), 400),
        "negative_prompt": _split(metadata.get("negative_prompt")),
    }


def _legacy_scene_summary(spec):
    location = (spec.get("location") or {}).get("visual_prompt") or (spec.get("location") or {}).get("label")
    weather = (spec.get("weather") or {}).get("visual_prompt") or (spec.get("weather") or {}).get("label")
    action = (spec.get("action") or {}).get("visual_prompt") or (spec.get("action") or {}).get("label")
    return f"One original character in {location or 'an anonymous setting'}, {action or 'remaining still'}, while {weather or 'the selected weather'} is visible."


def _panel_prompt(spec, style, character):
    panels = spec.get("panels") or []
    summary = _text(spec.get("scene_summary_en"), 500)
    avoid = list(dict.fromkeys([
        *[_text(item, 200) for item in spec.get("avoid_visuals") or [] if _text(item, 200)],
        *style["negative_prompt"],
    ]))
    lighting = _text(spec.get("lighting_narrative") or (spec.get("lighting") or {}).get("visual_prompt"), 400)
    palette = _text(spec.get("palette_narrative"), 300)

    parts = [
        f"Create one single coherent vertical illustration divided into {len(panels)} clearly separated "
        "panels, like a comic-strip or photo-diary layout with thin panel dividers.",
        "CONTENT FIDELITY IS MORE IMPORTANT THAN DECORATIVE STYLE.",
        "Arrange the panels from top to bottom in chronological order: panel 1 is the earliest moment "
        "and the last panel is the most recent moment of the same day.",
        f"Day overview: {summary}" if summary else "",
        f"The exact same character (identity, outfit, hairstyle, and art style) must appear in every "
        f"panel: {character}. This is an original illustrated character - not a photo, not any specific "
        "real or famous person, fully clothed and non-sexualized, friendly and safe for all ages.",
    ]
    for panel in panels:
        sequence = panel.get("sequence")
        place_narrative = _text(panel.get("place_narrative"), 400)
        action_narrative = _text(panel.get("action_narrative"), 400)
        object_narrative = _text(panel.get("object_narrative"), 200)
        panel_line = f"Panel {sequence}: the character in {place_narrative or 'a pleasant everyday setting'}, {action_narrative or 'spending a quiet moment'}."
        if object_narrative:
            panel_line += f" Include {object_narrative}."
        parts.append(panel_line)
    parts.extend([
        f"Shared lighting and mood across all panels: {lighting or 'soft, scene-consistent light'}.",
        f"Shared palette across all panels: {palette or 'a consistent, restrained palette'}.",
        f"Rendering style (applies identically to every panel): {style['rendering_prompt']}.",
    ])
    if style["line_style"]:
        parts.append(f"Linework: {style['line_style']}.")
    if style["texture"]:
        parts.append(f"Texture: {style['texture']}.")
    if style["shading_method"]:
        parts.append(f"Shading: {style['shading_method']}.")
    parts.extend([
        (
            "Apply the selected style only to linework, texture, shading, material treatment, and rendering "
            "technique. Do not alter panel content, panel order, the character's identity, or the overall "
            "emotional tone."
        ),
        "Avoid: " + (", ".join(avoid) if avoid else "content that contradicts the described panels"),
        (
            "No readable text, captions, letters, logos, watermarks, identifiable real people, specific "
            "addresses, real brand or idol names, company or school branding, readable documents, weapons, "
            "graphic violence, self-harm imagery, gore, extra limbs, or anatomical errors. Other people must "
            "be fully illustrated in the selected art style with generic non-identifying facial features; do "
            "not render stark black silhouettes except for a distant softly blurred background crowd."
        ),
    ])
    prompt = "\n\n".join(part for part in parts if part.strip())
    return prompt[:PROMPT_MAX_CHARS]


def build_image_prompt(spec, style_id):
    style = _style(style_id)
    character = HUMAN_CHARACTERS.get(
        spec.get("character"),
        "one original young adult character with generic non-identifying features and natural anatomy",
    )
    panels = spec.get("panels") or []
    if len(panels) >= 2:
        return _panel_prompt(spec, style, character)
    summary = _text(spec.get("scene_summary_en") or _legacy_scene_summary(spec), 1100)
    subject = _text(spec.get("subject_description") or character, 700)
    body_language = _text(spec.get("body_language") or (spec.get("pose") or {}).get("visual_prompt"), 600)
    gaze = _text(spec.get("gaze_direction"), 400)
    action = _text(spec.get("action_narrative") or (spec.get("action") or {}).get("visual_prompt"), 700)
    environment = _text(spec.get("environment_narrative"), 900)
    cause = _text(spec.get("cause_visualization"), 800)
    required_cues = [_text(item, 300) for item in spec.get("required_visual_cues") or [] if _text(item, 300)]
    optional_cues = [_text(item, 300) for item in spec.get("optional_visual_cues") or [] if _text(item, 300)]
    object_placements = [
        f"{_text(item.get('object_id'), 100)}: {_text(item.get('placement'), 300)}"
        for item in spec.get("object_placements") or []
        if isinstance(item, dict)
    ]
    lighting = _text(spec.get("lighting_narrative") or (spec.get("lighting") or {}).get("visual_prompt"), 600)
    palette = _text(spec.get("palette_narrative"), 500)
    composition = _text(spec.get("composition_narrative"), 700)
    avoid = list(dict.fromkeys([
        *[_text(item, 200) for item in spec.get("avoid_visuals") or [] if _text(item, 200)],
        *style["negative_prompt"],
    ]))

    parts = [
        "Create one coherent vertical emotional wellness card illustration.",
        "CONTENT FIDELITY IS MORE IMPORTANT THAN DECORATIVE STYLE.",
        f"Core scene: {summary}",
        f"Subject: {subject}. {character}.",
        f"Body language: {body_language or 'quiet, natural body language consistent with the stated emotion'}.",
        f"Gaze: {gaze or 'toward the visible emotional cause'}.",
        f"Action: {action or 'a safe, visually clear action consistent with the scene'}.",
        f"Environment: {environment or 'an anonymous environment with no identifying details'}.",
        f"Cause visibility: {cause or 'keep the stated emotional cause visibly recognizable'}.",
        "The cause of the emotion must be visibly represented through: "
        + ("; ".join(required_cues) if required_cues else "the validated scene cues"),
    ]
    if object_placements:
        parts.append("Objects and placement: " + "; ".join(object_placements))
    if optional_cues:
        parts.append(
            "Subtle transition traces (keep secondary to the current emotion): "
            + "; ".join(optional_cues)
        )
    parts.extend([
        f"Lighting: {lighting or 'scene-consistent soft light'}.",
        f"Palette: {palette or 'a restrained palette consistent with the selected scene'}.",
        f"Composition: {composition or 'an eye-level, coherent vertical composition'}.",
        f"Rendering style: {style['rendering_prompt']}.",
    ])
    if style["line_style"]:
        parts.append(f"Linework: {style['line_style']}.")
    if style["texture"]:
        parts.append(f"Texture: {style['texture']}.")
    if style["shading_method"]:
        parts.append(f"Shading: {style['shading_method']}.")
    parts.extend([
        (
            "Apply the selected style only to linework, texture, shading, material treatment, and rendering technique. "
            "Do not alter the selected scene content, weather, location, emotional tone, lighting direction, palette, "
            "subject pose, action, required visual cues, or composition."
        ),
        "Avoid: " + (", ".join(avoid) if avoid else "content that contradicts the validated scene"),
        (
            "No readable text, captions, letters, logos, watermarks, identifiable real people, specific addresses, "
            "company or school branding, readable documents, weapons, graphic violence, self-harm imagery, gore, "
            "extra limbs, or anatomical errors. Other people must be fully illustrated in the selected art style with "
            "generic non-identifying facial features; do not render stark black silhouettes except for a distant softly "
            "blurred background crowd."
        ),
    ])
    prompt = "\n\n".join(part for part in parts if part.strip())
    if len(prompt) <= PROMPT_MAX_CHARS:
        return prompt

    # Core scene, required cues, avoid constraints, and the final safety/style-preservation blocks stay intact.
    compact = [
        parts[0],
        parts[1],
        f"Core scene: {summary[:700]}",
        f"Subject: {subject[:400]}.",
        f"Body language: {body_language[:300]}. Gaze: {gaze[:200]}. Action: {action[:350]}.",
        f"Environment: {environment[:500]}. Cause visibility: {cause[:400]}.",
        "Required visual cues: " + "; ".join(required_cues),
        f"Lighting: {lighting[:300]}. Palette: {palette[:300]}. Composition: {composition[:350]}.",
        f"Rendering style: {style['rendering_prompt'][:500]}.",
        parts[-3],
        parts[-2],
        parts[-1],
    ]
    return "\n\n".join(part for part in compact if part.strip())[:PROMPT_MAX_CHARS]

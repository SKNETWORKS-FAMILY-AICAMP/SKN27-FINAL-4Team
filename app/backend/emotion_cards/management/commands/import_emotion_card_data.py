import csv
import re
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from emotion_cards.models import (
    CatalogEntry,
    FeatureCode,
    RuleEntry,
    SocialCompanionRule,
)


DATA_DIR = Path(__file__).resolve().parents[2] / "data"
EXPECTED_CSV_COUNT = 29

CATALOG_SPECS = {
    "03_event_types.csv": ("event", "event_type_id", "display_name", ""),
    "04_weather_catalog.csv": ("weather", "weather_id", "display_name", "visual_prompt"),
    "05_location_catalog.csv": ("location", "location_id", "display_name", "visual_prompt"),
    "06_lighting_palette_catalog.csv": ("lighting", "element_id", "display_name", "visual_prompt"),
    "07_character_visual_catalog.csv": ("character_visual", "visual_id", "display_name", "visual_prompt"),
    "08_action_catalog.csv": ("action", "action_id", "display_name", "visual_prompt"),
    "09_object_symbol_catalog.csv": ("object", "object_id", "display_name", "visual_prompt"),
    "10_effect_composition_catalog.csv": ("effect", "element_id", "display_name", "visual_prompt"),
    "11_style_presets.csv": ("style", "style_id", "display_name", "rendering_prompt"),
    "17_card_messages.csv": ("message", "message_id", "message_text", ""),
}

RULE_SPECS = {
    "12_emotion_visual_rules.csv": "emotion_visual",
    "13_event_scene_rules.csv": "event_scene",
    "14_energy_rules.csv": "energy",
    "15_need_environment_rules.csv": "need_environment",
    "16_interest_scene_rules.csv": "interest_scene",
    "18_message_mapping_rules.csv": "message_mapping",
    "19_safety_visual_rules.csv": "safety",
    "20_fallback_rules.csv": "fallback",
    "21_conflict_priority_rules.csv": "conflict_priority",
    "22_prompt_templates.csv": "prompt_template",
    "23_output_scene_schema.csv": "output_schema",
    "24_llm_extraction_examples.csv": "extraction_example",
    "25_scene_mapping_test_cases.csv": "scene_mapping_test",
}

REQUIRED_COLUMNS = {
    "01_analysis_schema.csv": {
        "field",
        "type",
        "required",
        "fallback",
    },
    "04_weather_catalog.csv": {
        "required_visual_cues",
        "conflict_visual_cues",
        "deprecated",
        "alias_of",
    },
    "11_style_presets.csv": {
        "rendering_prompt",
        "style_color_influence",
        "style_environment_influence",
        "preserve_scene",
    },
    "12_emotion_visual_rules.csv": {
        "weather_candidates",
        "lighting_candidates",
        "palette_candidates",
        "pose_candidates",
        "composition_candidates",
    },
    "21_conflict_priority_rules.csv": {
        "priority_rank",
        "rule_group",
        "resolution",
    },
    "22_prompt_templates.csv": {
        "template_id",
        "component",
        "template",
        "required_slots",
    },
    "23_output_scene_schema.csv": {
        "field_name",
        "data_type",
        "required",
        "validation_rule",
    },
    "24_llm_extraction_examples.csv": {
        "example_id",
        "user_input",
        "emotion_cause_type",
        "explicit_weather",
        "evidence_map",
        "field_sources",
    },
    "25_scene_mapping_test_cases.csv": {
        "test_id",
        "example_id",
        "required_explicit_facts",
        "required_visual_cues",
        "allowed_weather_ids",
        "forbidden_visual_cues",
    },
    "28_social_companion_rules.csv": {
        "required_source",
        "min_confidence",
        "emotional_alignment",
    },
}


def _rows(path):
    with path.open("r", encoding="utf-8-sig", newline="") as source:
        return list(csv.DictReader(source))


def _headers(path):
    with path.open("r", encoding="utf-8-sig", newline="") as source:
        return list(csv.DictReader(source).fieldnames or [])


def _truthy(value):
    return str(value).strip().lower() in {"true", "1", "yes", "y"}


def _split(value):
    return [part.strip() for part in str(value or "").split("|") if part.strip()]


def _check_references(errors, filename, rows, field, valid, placeholders=()):
    placeholder_set = set(placeholders)
    for row in rows:
        row_id = (
            row.get("rule_id")
            or row.get("test_id")
            or row.get("fallback_id")
            or row.get("example_id")
            or "row"
        )
        for value in _split(row.get(field)):
            if value not in valid and value not in placeholder_set:
                errors.append(f"{filename}:{row_id}:{field} references missing ID {value}")


def validate_data_files():
    errors = []
    warnings = []
    checks = []
    files = sorted(DATA_DIR.glob("*.csv"))
    file_names = {path.name for path in files}

    if len(files) != EXPECTED_CSV_COUNT:
        errors.append(f"expected {EXPECTED_CSV_COUNT} CSV files, found {len(files)}")
    checks.append(("CSV file count", len(files), f"expected {EXPECTED_CSV_COUNT}"))

    expected_names = {f"{index:02d}_" for index in range(29)}
    actual_prefixes = {path.name[:3] for path in files}
    missing_prefixes = sorted(expected_names - actual_prefixes)
    if missing_prefixes:
        errors.append(f"missing numbered CSV prefixes: {', '.join(missing_prefixes)}")

    for path in files:
        if not path.read_bytes().startswith(b"\xef\xbb\xbf"):
            errors.append(f"{path.name} is not UTF-8-SIG")
    checks.append(("UTF-8-SIG encoding", len(files), "all CSV files checked"))

    manifest_path = DATA_DIR / "00_manifest.csv"
    manifest_rows = _rows(manifest_path)
    if {row.get("file_name") for row in manifest_rows} != file_names:
        errors.append("00_manifest.csv does not list every CSV exactly once")
    for row in manifest_rows:
        filename = row.get("file_name")
        path = DATA_DIR / str(filename)
        if not path.exists():
            errors.append(f"manifest references missing file {filename}")
            continue
        actual_rows = len(_rows(path))
        actual_columns = len(_headers(path))
        if int(row.get("row_count") or -1) != actual_rows:
            errors.append(
                f"{filename}: manifest row_count={row.get('row_count')} actual={actual_rows}"
            )
        if int(row.get("column_count") or -1) != actual_columns:
            errors.append(
                f"{filename}: manifest column_count={row.get('column_count')} actual={actual_columns}"
            )
    checks.append(("Manifest counts", len(manifest_rows), "row and column counts checked"))

    for filename, required in REQUIRED_COLUMNS.items():
        missing = required - set(_headers(DATA_DIR / filename))
        if missing:
            errors.append(f"{filename}: missing columns {', '.join(sorted(missing))}")
    checks.append(("Required columns", len(REQUIRED_COLUMNS), "runtime schemas checked"))

    ids = {
        "event": {row["event_type_id"] for row in _rows(DATA_DIR / "03_event_types.csv")},
        "weather": {row["weather_id"] for row in _rows(DATA_DIR / "04_weather_catalog.csv")},
        "location": {row["location_id"] for row in _rows(DATA_DIR / "05_location_catalog.csv")},
        "lighting": {row["element_id"] for row in _rows(DATA_DIR / "06_lighting_palette_catalog.csv")},
        "character": {row["visual_id"] for row in _rows(DATA_DIR / "07_character_visual_catalog.csv")},
        "action": {row["action_id"] for row in _rows(DATA_DIR / "08_action_catalog.csv")},
        "object": {row["object_id"] for row in _rows(DATA_DIR / "09_object_symbol_catalog.csv")},
        "effect": {row["element_id"] for row in _rows(DATA_DIR / "10_effect_composition_catalog.csv")},
        "style": {row["style_id"] for row in _rows(DATA_DIR / "11_style_presets.csv")},
        "message": {row["message_id"] for row in _rows(DATA_DIR / "17_card_messages.csv")},
    }
    for catalog_name, values in ids.items():
        if len(values) != len(set(values)):
            errors.append(f"duplicate IDs in {catalog_name} catalog")

    weather_rows = _rows(DATA_DIR / "04_weather_catalog.csv")
    for row in weather_rows:
        alias = row.get("alias_of")
        if alias and alias not in ids["weather"]:
            errors.append(f"04_weather_catalog.csv:{row['weather_id']} invalid alias {alias}")
    rain = next((row for row in weather_rows if row.get("weather_id") == "WTH_RAIN"), None)
    if not rain or len(_split(rain.get("required_visual_cues"))) < 2:
        errors.append("WTH_RAIN must define at least two required_visual_cues")
    checks.append(("Weather aliases and rain cues", len(weather_rows), "WTH_RAIN requires 2+ cues"))

    emotion_rows = _rows(DATA_DIR / "12_emotion_visual_rules.csv")
    for field, valid in (
        ("weather_candidates", ids["weather"]),
        ("lighting_candidates", ids["lighting"]),
        ("palette_candidates", ids["lighting"]),
        ("expression_candidates", ids["character"]),
        ("pose_candidates", ids["character"]),
        ("effect_candidates", ids["effect"]),
        ("composition_candidates", ids["effect"]),
    ):
        _check_references(errors, "12_emotion_visual_rules.csv", emotion_rows, field, valid)

    event_rows = _rows(DATA_DIR / "13_event_scene_rules.csv")
    _check_references(errors, "13_event_scene_rules.csv", event_rows, "event_type_id", ids["event"])
    _check_references(errors, "13_event_scene_rules.csv", event_rows, "location_candidates", ids["location"])
    _check_references(errors, "13_event_scene_rules.csv", event_rows, "action_candidates", ids["action"])
    _check_references(errors, "13_event_scene_rules.csv", event_rows, "object_candidates", ids["object"])

    energy_rows = _rows(DATA_DIR / "14_energy_rules.csv")
    _check_references(errors, "14_energy_rules.csv", energy_rows, "pose_id", ids["character"])
    _check_references(errors, "14_energy_rules.csv", energy_rows, "composition_id", ids["effect"])
    _check_references(errors, "14_energy_rules.csv", energy_rows, "default_action", ids["action"])

    need_rows = _rows(DATA_DIR / "15_need_environment_rules.csv")
    _check_references(errors, "15_need_environment_rules.csv", need_rows, "location_candidates", ids["location"])
    _check_references(errors, "15_need_environment_rules.csv", need_rows, "action_candidates", ids["action"])
    _check_references(errors, "15_need_environment_rules.csv", need_rows, "object_candidates", ids["object"])
    _check_references(errors, "15_need_environment_rules.csv", need_rows, "lighting_id", ids["lighting"])
    _check_references(errors, "15_need_environment_rules.csv", need_rows, "message_id", ids["message"])

    interest_rows = _rows(DATA_DIR / "16_interest_scene_rules.csv")
    _check_references(errors, "16_interest_scene_rules.csv", interest_rows, "location_candidates", ids["location"])
    _check_references(errors, "16_interest_scene_rules.csv", interest_rows, "action_candidates", ids["action"])
    _check_references(errors, "16_interest_scene_rules.csv", interest_rows, "object_candidates", ids["object"])
    _check_references(errors, "16_interest_scene_rules.csv", interest_rows, "effect_candidates", ids["effect"])

    message_rows = _rows(DATA_DIR / "18_message_mapping_rules.csv")
    _check_references(errors, "18_message_mapping_rules.csv", message_rows, "message_id", ids["message"])

    test_rows = _rows(DATA_DIR / "25_scene_mapping_test_cases.csv")
    examples = {row["example_id"] for row in _rows(DATA_DIR / "24_llm_extraction_examples.csv")}
    for row in test_rows:
        if row.get("example_id") not in examples:
            errors.append(
                f"25_scene_mapping_test_cases.csv:{row.get('test_id')} missing example {row.get('example_id')}"
            )
    _check_references(errors, "25_scene_mapping_test_cases.csv", test_rows, "allowed_weather_ids", ids["weather"], ("FLEXIBLE",))
    _check_references(errors, "25_scene_mapping_test_cases.csv", test_rows, "allowed_location_ids", ids["location"], ("FLEXIBLE", "USE_EXPLICIT_PLACE"))
    _check_references(errors, "25_scene_mapping_test_cases.csv", test_rows, "allowed_action_ids", ids["action"], ("FLEXIBLE",))
    _check_references(errors, "25_scene_mapping_test_cases.csv", test_rows, "allowed_expression_ids", ids["character"], ("FLEXIBLE",))
    _check_references(errors, "25_scene_mapping_test_cases.csv", test_rows, "allowed_lighting_ids", ids["lighting"], ("FLEXIBLE",))
    _check_references(errors, "25_scene_mapping_test_cases.csv", test_rows, "allowed_palette_ids", ids["lighting"], ("FLEXIBLE",))
    _check_references(errors, "25_scene_mapping_test_cases.csv", test_rows, "allowed_composition_ids", ids["effect"], ("FLEXIBLE",))
    checks.append(("Extraction example links", len(test_rows), "every regression test references an example"))

    styles = _rows(DATA_DIR / "11_style_presets.csv")
    for row in styles:
        if not _truthy(row.get("preserve_scene")):
            errors.append(f"11_style_presets.csv:{row['style_id']} preserve_scene must be true")
        if row.get("style_environment_influence") != "NONE":
            errors.append(
                f"11_style_presets.csv:{row['style_id']} style_environment_influence must be NONE"
            )
    anime = next(row for row in styles if row["style_id"] == "STYLE_ANIME_FILM")
    forbidden_style_terms = ("lush painterly nature", "verdant green", "golden-hour light")
    if any(term in anime.get("rendering_prompt", "").lower() for term in forbidden_style_terms):
        errors.append("STYLE_ANIME_FILM still forces environment or golden-hour content")
    checks.append(("Style scene preservation", len(styles), "preserve_scene=true and environment influence NONE"))

    analysis_schema = _rows(DATA_DIR / "01_analysis_schema.csv")
    required_analysis_fields = {
        "raw_text",
        "emotion_cause_type",
        "explicit_weather",
        "evidence_map",
        "field_sources",
        "field_confidences",
    }
    actual_analysis_fields = {
        row.get("field") for row in analysis_schema
    }
    if not required_analysis_fields <= actual_analysis_fields:
        errors.append(
            "01_analysis_schema.csv missing fields: "
            + ", ".join(
                sorted(required_analysis_fields - actual_analysis_fields)
            )
        )
    for field_name in ("energy_code", "need_code"):
        row = next((item for item in analysis_schema if item.get("field") == field_name), None)
        if not row or row.get("fallback"):
            errors.append(f"01_analysis_schema.csv:{field_name} fallback must be empty")
    checks.append(("Null energy and need fallbacks", 2, "both optional with blank fallback"))

    prompt_rows = _rows(DATA_DIR / "22_prompt_templates.csv")
    required_templates = {
        "PRM_DIRECTOR_SYSTEM",
        "PRM_DIRECTOR_INPUT",
        "PRM_DIRECTOR_OUTPUT_RULES",
        "PRM_IMAGE_SCENE",
    }
    actual_templates = {row["template_id"] for row in prompt_rows}
    if not required_templates <= actual_templates:
        errors.append(
            "22_prompt_templates.csv missing required templates: "
            + ", ".join(sorted(required_templates - actual_templates))
        )
    for row in prompt_rows:
        if row.get("template_id") not in required_templates:
            continue
        placeholders = set(re.findall(r"\{([a-zA-Z0-9_]+)\}", row.get("template", "")))
        required_slots = set(_split(row.get("required_slots")))
        if not required_slots <= placeholders:
            errors.append(
                f"22_prompt_templates.csv:{row['template_id']} required_slots not present in template"
            )
    checks.append(("Prompt template slots", len(prompt_rows), "required slots are present"))

    schema_fields = {
        row["field_name"] for row in _rows(DATA_DIR / "23_output_scene_schema.csv")
    }
    required_scene_fields = {
        "scene_summary_en",
        "selected_candidate_scores",
        "required_visual_cues",
        "validation_status",
        "repair_count",
        "final_prompt",
        "prompt_version",
    }
    if not required_scene_fields <= schema_fields:
        errors.append(
            "23_output_scene_schema.csv missing fields: "
            + ", ".join(sorted(required_scene_fields - schema_fields))
        )
    checks.append(("Scene v2 schema", len(schema_fields), "required runtime fields present"))

    priority_groups = {
        row["rule_group"]
        for row in _rows(DATA_DIR / "21_conflict_priority_rules.csv")
    }
    required_priority = {
        "SAFETY_HARD",
        "EXPLICIT_NEGATION",
        "EXPLICIT_CAUSE",
        "EXPLICIT_WEATHER",
        "STYLE",
    }
    if not required_priority <= priority_groups:
        errors.append("21_conflict_priority_rules.csv missing hard-priority groups")
    checks.append(("Conflict priorities", len(priority_groups), "18 runtime priority groups"))

    return {
        "errors": errors,
        "warnings": warnings,
        "checks": checks,
    }


class Command(BaseCommand):
    help = "Import the emotion-card v2 CSV candidate and constraint data."

    def add_arguments(self, parser):
        parser.add_argument("--dry-run", action="store_true")
        parser.add_argument(
            "--strict",
            action="store_true",
            help="Treat validation warnings as errors.",
        )

    def _validate_files(self, strict=False):
        report = validate_data_files()
        failures = list(report["errors"])
        if strict:
            failures.extend(report["warnings"])
        if failures:
            raise CommandError("; ".join(failures))
        return report["warnings"]

    def handle(self, *args, **options):
        warnings = self._validate_files(options["strict"])
        counts = {"feature": 0, "catalog": 0, "rule": 0, "social": 0}
        with transaction.atomic():
            for filename in (
                "02_feature_codes.csv",
                "27_feature_codes_extended.csv",
            ):
                for row in _rows(DATA_DIR / filename):
                    FeatureCode.objects.update_or_create(
                        group=row["group"],
                        code=row["code"],
                        defaults={
                            "label": row.get("label", row["code"]),
                            "metadata": {
                                key: value
                                for key, value in row.items()
                                if key not in {"group", "code", "label"}
                            },
                        },
                    )
                    counts["feature"] += 1

            for filename, (
                catalog,
                code_key,
                label_key,
                prompt_key,
            ) in CATALOG_SPECS.items():
                imported_codes = set()
                for row in _rows(DATA_DIR / filename):
                    code = row.get(code_key)
                    imported_codes.add(code)
                    metadata = {
                        key: value
                        for key, value in row.items()
                        if key not in {code_key, label_key, prompt_key}
                    }
                    for boolean_key in (
                        "preserve_scene",
                        "deprecated",
                        "ui_selectable",
                        "is_comfort_accent",
                    ):
                        if boolean_key in metadata:
                            metadata[boolean_key] = _truthy(metadata[boolean_key])
                    CatalogEntry.objects.update_or_create(
                        catalog=catalog,
                        code=code,
                        defaults={
                            "display_name": row.get(label_key, code),
                            "visual_prompt": row.get(prompt_key, ""),
                            "metadata": metadata,
                            "enabled": _truthy(row.get("enabled", "True"))
                            and not _truthy(row.get("deprecated", "False")),
                        },
                    )
                    counts["catalog"] += 1
                CatalogEntry.objects.filter(catalog=catalog).exclude(
                    code__in=imported_codes
                ).update(enabled=False)

            for filename, rule_type in RULE_SPECS.items():
                for index, row in enumerate(
                    _rows(DATA_DIR / filename),
                    start=1,
                ):
                    rule_id = (
                        row.get("rule_id")
                        or row.get("safety_rule_id")
                        or row.get("fallback_id")
                        or row.get("field_name")
                        or row.get("template_id")
                        or row.get("example_id")
                        or row.get("test_id")
                        or f"{rule_type}-{index}"
                    )
                    RuleEntry.objects.update_or_create(
                        rule_type=rule_type,
                        rule_id=rule_id,
                        defaults={
                            "data": row,
                            "enabled": _truthy(row.get("enabled", "True")),
                        },
                    )
                    counts["rule"] += 1

            social_codes = set()
            for row in _rows(DATA_DIR / "28_social_companion_rules.csv"):
                social_codes.add(row["rule_id"])
                SocialCompanionRule.objects.update_or_create(
                    rule_id=row["rule_id"],
                    defaults={
                        "social_context": row.get("social_context", ""),
                        "companion_type": row.get("companion_type", ""),
                        "companion_count_max": int(
                            row.get("companion_count_max") or 0
                        ),
                        "visual_prompt": row.get("visual_prompt", ""),
                        "privacy_note": row.get("privacy_note", ""),
                        "weight": int(row.get("weight") or 35),
                        "enabled": _truthy(row.get("enabled", "True")),
                    },
                )
                counts["social"] += 1
            SocialCompanionRule.objects.exclude(
                rule_id__in=social_codes
            ).update(enabled=False)

            if options["dry_run"]:
                transaction.set_rollback(True)

        for warning in warnings:
            self.stdout.write(self.style.WARNING(f"Warning: {warning}"))
        suffix = " (dry run; rolled back)" if options["dry_run"] else ""
        self.stdout.write(
            self.style.SUCCESS(
                f"Emotion-card v2 data import complete{suffix}: {counts}"
            )
        )

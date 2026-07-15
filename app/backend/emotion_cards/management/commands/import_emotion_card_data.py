import csv
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from emotion_cards.models import CatalogEntry, FeatureCode, RuleEntry, SocialCompanionRule


DATA_DIR = Path(__file__).resolve().parents[2] / "data"
EXTRA_FILES = {"27_feature_codes_extended.csv", "28_social_companion_rules.csv"}


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
}


def _rows(path):
    with path.open("r", encoding="utf-8-sig", newline="") as source:
        return list(csv.DictReader(source))


def _truthy(value):
    return str(value).strip().lower() in {"true", "1", "yes", "y"}


class Command(BaseCommand):
    help = "마음카드 CSV 데이터를 DB 시드로 가져옵니다."

    def add_arguments(self, parser):
        parser.add_argument("--dry-run", action="store_true")
        parser.add_argument("--strict", action="store_true", help="매니페스트 경고도 오류로 처리합니다.")

    def _validate_files(self, strict=False):
        expected = {f"{number:02d}_{name}" for number, name in []}
        files = {path.name for path in DATA_DIR.glob("*.csv")}
        required = {"00_manifest.csv", *CATALOG_SPECS, *RULE_SPECS, "01_analysis_schema.csv", "02_feature_codes.csv", *EXTRA_FILES,
                    "24_llm_extraction_examples.csv", "25_scene_mapping_test_cases.csv", "26_validation_report.csv"}
        missing = sorted(required - files)
        if missing:
            raise CommandError(f"필수 데이터 파일이 없습니다: {', '.join(missing)}")
        if len(files) != 29:
            raise CommandError(f"CSV 파일 수가 예상과 다릅니다: {len(files)}개 (예상 29개)")

        warnings = []
        for row in _rows(DATA_DIR / "00_manifest.csv"):
            filename = row.get("file_name") or row.get("filename")
            declared = int(row.get("row_count") or 0)
            if not filename or not (DATA_DIR / filename).exists():
                raise CommandError(f"매니페스트 파일을 찾을 수 없습니다: {filename}")
            actual = len(_rows(DATA_DIR / filename))
            if actual != declared:
                note = f"{filename}: 매니페스트 {declared}행 / 실제 {actual}행"
                if filename == "00_manifest.csv":
                    warnings.append(note)
                else:
                    raise CommandError(note)
        if warnings and strict:
            raise CommandError("; ".join(warnings))
        return warnings

    def handle(self, *args, **options):
        warnings = self._validate_files(options["strict"])
        counts = {"feature": 0, "catalog": 0, "rule": 0, "social": 0}
        with transaction.atomic():
            for filename in ("02_feature_codes.csv", "27_feature_codes_extended.csv"):
                for row in _rows(DATA_DIR / filename):
                    FeatureCode.objects.update_or_create(
                        group=row["group"], code=row["code"],
                        defaults={"label": row.get("label", row["code"]), "metadata": {key: value for key, value in row.items() if key not in {"group", "code", "label"}}},
                    )
                    counts["feature"] += 1

            for filename, (catalog, code_key, label_key, prompt_key) in CATALOG_SPECS.items():
                for row in _rows(DATA_DIR / filename):
                    code = row.get(code_key) or row.get("element_id") or row.get("rule_id")
                    metadata = {key: value for key, value in row.items() if key not in {code_key, label_key, prompt_key}}
                    if "preserve_scene" in metadata:
                        metadata["preserve_scene"] = _truthy(metadata["preserve_scene"])
                    CatalogEntry.objects.update_or_create(
                        catalog=catalog, code=code,
                        defaults={"display_name": row.get(label_key, code), "visual_prompt": row.get(prompt_key, ""), "metadata": metadata, "enabled": _truthy(row.get("enabled", "True"))},
                    )
                    counts["catalog"] += 1

            # 그림체 프리셋이 교체되면 CSV에 없는 옛 style 코드를 비활성화(고아 방지)
            style_codes = {row.get('style_id') for row in _rows(DATA_DIR / '11_style_presets.csv')}
            CatalogEntry.objects.filter(catalog='style').exclude(code__in=style_codes).update(enabled=False)

            for filename, rule_type in RULE_SPECS.items():
                for index, row in enumerate(_rows(DATA_DIR / filename), start=1):
                    rule_id = row.get("rule_id") or row.get("field_name") or row.get("template_id") or f"{rule_type}-{index}"
                    RuleEntry.objects.update_or_create(
                        rule_type=rule_type, rule_id=rule_id,
                        defaults={"data": row, "enabled": _truthy(row.get("enabled", "True"))},
                    )
                    counts["rule"] += 1

            for row in _rows(DATA_DIR / "28_social_companion_rules.csv"):
                SocialCompanionRule.objects.update_or_create(
                    rule_id=row["rule_id"],
                    defaults={
                        "social_context": row.get("social_context", ""),
                        "companion_type": row.get("companion_type", ""),
                        "companion_count_max": int(row.get("companion_count_max") or 0),
                        "visual_prompt": row.get("visual_prompt", ""),
                        "privacy_note": row.get("privacy_note", ""),
                        "weight": int(row.get("weight") or 35),
                        "enabled": _truthy(row.get("enabled", "True")),
                    },
                )
                counts["social"] += 1

            if options["dry_run"]:
                transaction.set_rollback(True)
        for warning in warnings:
            self.stdout.write(self.style.WARNING(f"경고(허용): {warning}"))
        suffix = " (저장하지 않음)" if options["dry_run"] else ""
        self.stdout.write(self.style.SUCCESS(f"마음카드 데이터 시드 완료{suffix}: {counts}"))

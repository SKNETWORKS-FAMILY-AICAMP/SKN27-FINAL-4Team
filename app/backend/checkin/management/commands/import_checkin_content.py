import csv
import json
import tempfile
import zipfile
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError
from django.db import IntegrityError

from checkin.models import (
    CauseOption,
    CauseContextConfig,
    CharacterFragment,
    CharacterToneRule,
    DialogueTemplate,
    NeedOption,
    PreferenceMapping,
    RecommendationAction,
    ReflectionOption,
)


class Command(BaseCommand):
    help = '운영 데이터 JSON/CSV를 오늘의 나 찾기 기준 데이터에 idempotent upsert 합니다.'

    def add_arguments(self, parser):
        parser.add_argument('--source', default=str(Path(__file__).resolve().parents[2] / 'data' / 'fallback_content.json'))

    def handle(self, *args, **options):
        source = Path(options['source']).expanduser()
        if not source.exists():
            raise CommandError(f'데이터 파일을 찾을 수 없습니다: {source}')
        if source.suffix.lower() == '.zip':
            with tempfile.TemporaryDirectory() as temp_dir:
                with zipfile.ZipFile(source) as archive:
                    archive.extractall(temp_dir)
                payload = self._load_directory(Path(temp_dir))
        elif source.is_dir():
            payload = self._load_directory(source)
        else:
            try:
                payload = json.loads(source.read_text(encoding='utf-8-sig'))
            except (OSError, json.JSONDecodeError) as exc:
                raise CommandError(f'JSON을 읽을 수 없습니다: {exc}') from exc

        counts = {'created': 0, 'updated': 0, 'skipped': 0}
        self._upsert(payload, 'reflection_options', ReflectionOption, 'reflection_id', counts, self._reflection_fields)
        self._upsert(payload, 'cause_contexts', CauseContextConfig, 'cause_context', counts, self._context_fields)
        self._upsert(payload, 'cause_options', CauseOption, 'cause_id', counts, self._cause_fields)
        self._upsert(payload, 'need_options', NeedOption, 'need_id', counts, self._need_fields)
        self._upsert(payload, 'character_tone_rules', CharacterToneRule, 'character_id', counts, self._tone_fields)
        self._upsert(payload, 'character_fragments', CharacterFragment, None, counts, self._fragment_fields)
        self._upsert(payload, 'dialogue_templates', DialogueTemplate, None, counts, self._dialogue_fields)
        self._upsert(payload, 'preference_mapping', PreferenceMapping, None, counts, self._mapping_fields)
        self._upsert(payload, 'recommendation_actions', RecommendationAction, 'action_id', counts, self._action_fields)
        self.stdout.write(self.style.SUCCESS(
            f"import_checkin_content 완료: 생성 {counts['created']} / 수정 {counts['updated']} / 건너뜀 {counts['skipped']}"
        ))

    def _load_directory(self, directory):
        bundle = directory / 'checkin_content_bundle.json'
        if bundle.exists():
            return json.loads(bundle.read_text(encoding='utf-8-sig'))
        aliases = {
            'reflection_options': 'day_reflection_options.csv',
            'cause_contexts': 'cause_contexts.csv',
            'cause_options': 'cause_options.csv',
            'need_options': 'need_options.csv',
            'character_tone_rules': 'character_tone_rules.csv',
            'character_fragments': 'character_fragments.csv',
            'dialogue_templates': 'dialogue_templates.csv',
            'preference_mapping': 'preference_mapping.csv',
            'recommendation_actions': 'recommendation_actions.csv',
        }
        result = {}
        for key, filename in aliases.items():
            matches = list(directory.rglob(filename))
            if matches:
                with matches[0].open(encoding='utf-8-sig', newline='') as handle:
                    result[key] = list(csv.DictReader(handle))
        if not result:
            raise CommandError(f'지원하는 JSON/CSV 파일이 없습니다: {directory}')
        return result

    def _upsert(self, payload, key, model, natural_key, counts, field_builder):
        seen = set()
        for raw in payload.get(key, []) or []:
            fields = field_builder(raw)
            if natural_key:
                identity = {natural_key: fields.pop(natural_key, None)}
            else:
                identity = {name: fields.pop(name) for name in field_builder.identity if name in fields}
            if not all(identity.values()):
                raise CommandError(f'{key}: 식별자 누락: {raw}')
            identity_key = tuple(identity.items())
            if identity_key in seen:
                raise CommandError(f'{key}: 중복 ID: {identity_key}')
            seen.add(identity_key)
            try:
                obj, created = model.objects.update_or_create(defaults=fields, **identity)
            except IntegrityError:
                if model is not CauseOption or 'cause_code' not in fields:
                    raise
                conflict = model.objects.filter(cause_code=fields['cause_code']).exclude(pk=identity['cause_id']).first()
                if not conflict:
                    raise
                conflict.cause_code = f'LEGACY_{conflict.cause_id}'[:40]
                conflict.save(update_fields=['cause_code'])
                obj, created = model.objects.update_or_create(defaults=fields, **identity)
            counts['created' if created else 'updated'] += 1

    @staticmethod
    def _list(value):
        if isinstance(value, list):
            return value
        if value in (None, ''):
            return []
        if isinstance(value, str):
            try:
                parsed = json.loads(value)
                if isinstance(parsed, list):
                    return parsed
            except json.JSONDecodeError:
                pass
            return [item.strip() for item in value.split('|') if item.strip()]
        return [value]

    @staticmethod
    def _bool(value, default=False):
        if isinstance(value, bool):
            return value
        if value in (None, ''):
            return default
        return str(value).strip().lower() in {'1', 'true', 'yes', 'y', 'on'}

    def _reflection_fields(self, raw):
        emotion = str(raw.get('primary_emotion') or raw.get('emotion') or '').upper()
        energy = str(raw.get('energy_level') or 'MEDIUM').upper()
        if emotion and emotion not in {'JOY', 'SADNESS', 'ANGER', 'ANXIETY'}:
            raise CommandError(f"reflection_options: 잘못된 primary_emotion '{emotion}'")
        if energy not in {'LOW', 'MEDIUM', 'HIGH', 'UNKNOWN'}:
            raise CommandError(f"reflection_options: 잘못된 energy_level '{energy}'")
        return {
            'reflection_id': raw.get('reflection_id') or raw.get('id'),
            'label': raw.get('label') or raw.get('text') or raw.get('option_text') or raw.get('title'),
            'hint': raw.get('hint') or raw.get('description') or '',
            'icon': raw.get('icon') or raw.get('emoji') or raw.get('ui_icon') or '',
            'primary_emotion': emotion,
            'secondary_emotion': str(raw.get('secondary_emotion') or '').upper(),
            'emotion_intensity_default': int(raw.get('emotion_intensity_default') or 0),
            'state_tags': self._list(raw.get('state_tags')),
            'energy_level': energy,
            'cause_context': str(raw.get('cause_context') or 'DIFFICULT').upper(),
            'ack_key': raw.get('ack_key') or '',
            'next_stage': raw.get('next_stage') or 'CAUSE',
            'include_weekly': self._bool(raw.get('include_weekly'), True),
            'display_order': int(raw.get('display_order') or 0),
            'enabled': self._bool(raw.get('enabled'), True),
        }
    def _cause_fields(self, raw):
        return {
            'cause_id': raw.get('cause_id') or raw.get('id'), 'cause_code': raw.get('cause_code') or raw.get('code') or raw.get('cause_id'),
            'label': raw.get('label') or raw.get('text') or raw.get('option_text_neutral') or raw.get('title'), 'hint': raw.get('hint') or raw.get('description') or '',
            'icon': raw.get('icon') or raw.get('emoji') or raw.get('ui_icon') or '', 'available_contexts': self._list(raw.get('available_contexts')) or ['POSITIVE', 'DIFFICULT', 'MIXED', 'NEUTRAL'],
            'option_text_neutral': raw.get('option_text_neutral') or raw.get('label') or '', 'option_text_positive': raw.get('option_text_positive') or raw.get('label') or '',
            'option_text_difficult': raw.get('option_text_difficult') or raw.get('label') or '', 'option_text_mixed': raw.get('option_text_mixed') or raw.get('label') or '',
            'examples_internal': raw.get('examples_internal') or '', 'sensitive': self._bool(raw.get('sensitive')),
            'chat_seed': raw.get('chat_seed') or raw.get('chat_seed_template') or '',
            'chat_seed_templates': {
                key.replace('chat_seed_template_', ''): value
                for key, value in raw.items() if key.startswith('chat_seed_template_') and value
            },
            'display_order': int(raw.get('display_order') or 0), 'enabled': self._bool(raw.get('enabled'), True),
        }
    def _context_fields(self, raw):
        return {
            'cause_context': raw.get('cause_context') or raw.get('id'), 'display_order': int(raw.get('display_order') or 0),
            'title': raw.get('title') or '', 'question_text': raw.get('question_text') or '',
            'option_text_field': raw.get('option_text_field') or '', 'show_cause_options': self._bool(raw.get('show_cause_options'), True),
            'next_stage': raw.get('next_stage') or 'CAUSE', 'weekly_label': raw.get('weekly_label') or '', 'description': raw.get('description') or '',
        }
    def _need_fields(self, raw):
        return {
            'need_id': raw.get('need_id') or raw.get('id'), 'need_code': raw.get('need_code') or raw.get('code') or '', 'label': raw.get('label') or raw.get('text') or raw.get('option_text') or raw.get('title'),
            'hint': raw.get('hint') or raw.get('description') or '', 'icon': raw.get('icon') or raw.get('emoji') or '',
            'response_mode': raw.get('response_mode') or 'GENTLE', 'llm_instruction': raw.get('llm_instruction') or '',
            'display_order': int(raw.get('display_order') or 0), 'enabled': self._bool(raw.get('enabled'), True),
        }
    def _tone_fields(self, raw):
        return {'character_id': raw.get('character_id') or raw.get('id'), 'tone': raw.get('tone') or '', 'avoid_phrases': self._list(raw.get('avoid_phrases'))}
    def _fragment_fields(self, raw):
        return {'character_id': raw.get('character_id'), 'stage': raw.get('stage') or 'ALL', 'fragment_key': raw.get('fragment_key') or raw.get('key'), 'text': raw.get('text') or raw.get('fragment_text') or raw.get('content') or ''}
    def _dialogue_fields(self, raw):
        return {'stage': raw.get('stage'), 'context_key': raw.get('context_key') or 'base', 'template': raw.get('template') or raw.get('base_template') or raw.get('text') or ''}
    def _mapping_fields(self, raw):
        return {
            'source_label': raw.get('source_label') or raw.get('source') or raw.get('keyword') or raw.get('interest_label') or raw.get('normalized_interest_label'),
            'target_action_ids': self._list(raw.get('target_action_ids') or raw.get('action_ids') or raw.get('linked_hobby_id')),
            'enabled': self._bool(raw.get('enabled'), True),
        }
    def _action_fields(self, raw):
        return {
            'action_id': raw.get('action_id') or raw.get('id'), 'title': raw.get('title') or raw.get('name'), 'description': raw.get('description') or raw.get('detail') or '',
            'expected_minutes': int(raw.get('expected_minutes') or raw.get('estimated_minutes') or raw.get('duration_minutes') or 3), 'icon': raw.get('icon') or raw.get('emoji') or '',
            'tags': self._list(raw.get('tags') or raw.get('action_tags')), 'suitable_needs': self._list(raw.get('suitable_needs')), 'suitable_emotions': self._list(raw.get('suitable_emotions')),
            'energy_levels': self._list(raw.get('energy_levels') or raw.get('suitable_energy') or raw.get('energy_level')), 'linked_keywords': self._list(raw.get('linked_keywords') or raw.get('keywords') or raw.get('source_label') or raw.get('normalized_label') or raw.get('linked_hobby_id')),
            'avoid_emotions': self._list(raw.get('avoid_emotions')), 'avoid_causes': self._list(raw.get('avoid_causes')),
            'default_weight': int(raw.get('default_weight') or 0), 'safety_notice': raw.get('safety_notice') or raw.get('safety') or '', 'enabled': self._bool(raw.get('enabled'), True),
        }


Command._fragment_fields.identity = ('character_id', 'stage', 'fragment_key')
Command._dialogue_fields.identity = ('stage', 'context_key')
Command._mapping_fields.identity = ('source_label',)

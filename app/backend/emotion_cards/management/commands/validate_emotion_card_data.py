from django.core.management.base import BaseCommand, CommandError

from emotion_cards.models import CatalogEntry, FeatureCode, RuleEntry, SocialCompanionRule
from .import_emotion_card_data import Command as ImportCommand


class Command(BaseCommand):
    help = "마음카드 CSV와 DB 시드 상태를 검증합니다."

    def add_arguments(self, parser):
        parser.add_argument("--strict", action="store_true")

    def handle(self, *args, **options):
        warnings = ImportCommand()._validate_files(options["strict"])
        missing = []
        for model, label in ((FeatureCode, "특성 코드"), (CatalogEntry, "카탈로그"), (RuleEntry, "규칙"), (SocialCompanionRule, "동행 규칙")):
            if not model.objects.exists():
                missing.append(label)
        if missing:
            raise CommandError(f"DB 시드가 비어 있습니다: {', '.join(missing)}. import_emotion_card_data를 먼저 실행하세요.")
        for warning in warnings:
            self.stdout.write(self.style.WARNING(f"경고(허용): {warning}"))
        self.stdout.write(self.style.SUCCESS("마음카드 데이터 검증을 통과했습니다."))

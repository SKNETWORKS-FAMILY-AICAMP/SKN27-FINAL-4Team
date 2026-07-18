# -*- coding: utf-8 -*-
"""기존 채팅 데이터 일괄 암호화 (2026-07-15) — 암호화 도입 전 평문 행 전환.

실행:
    python manage.py encrypt_chat          # 미리보기 (대상 수만 출력)
    python manage.py encrypt_chat --yes    # 실행

동작: 접두사(enc:v1:) 없는 평문 행만 재저장 → EncryptedTextField가 자동 암호화.
멱등: 이미 암호화된 행은 건드리지 않음. CHAT_ENC_KEY 없으면 중단.
"""
from django.core.management.base import BaseCommand

from chat.crypto_fields import _PREFIX, _fernet
from chat.models import ChatMessage, UserMemory


class Command(BaseCommand):
    help = '평문으로 저장된 기존 채팅·요약을 일괄 암호화'

    def add_arguments(self, parser):
        parser.add_argument('--yes', action='store_true', help='실제 실행 (없으면 미리보기)')

    def handle(self, *args, **opts):
        if _fernet() is None:
            self.stdout.write(self.style.ERROR('CHAT_ENC_KEY 미설정 — .env에 키를 넣고 다시 실행'))
            return
        # 주의: values_list는 필드 변환(복호화)을 타므로, 원시 판별은 DB 원문 기준으로.
        targets = []
        for model, field in ((ChatMessage, 'content'), (UserMemory, 'summary_text')):
            raw_ids = [
                pk for pk, raw in model.objects.extra(
                    select={'_raw': field}).values_list('pk', '_raw')
                if raw and not str(raw).startswith(_PREFIX)
            ]
            targets.append((model, field, raw_ids))
            self.stdout.write(f'  {model.__name__}.{field}: 평문 {len(raw_ids)}건')
        if not opts['yes']:
            self.stdout.write('미리보기 모드 — 실행: python manage.py encrypt_chat --yes')
            return
        total = 0
        for model, field, ids in targets:
            for pk in ids:
                obj = model.objects.get(pk=pk)
                obj.save(update_fields=[field])   # 재저장 → 필드가 암호화
                total += 1
        self.stdout.write(self.style.SUCCESS(f'완료 — {total}건 암호화'))

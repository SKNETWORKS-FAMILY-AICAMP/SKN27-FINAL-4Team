# -*- coding: utf-8 -*-
"""특정 키워드가 든 기억 줄을 user_memory에서 삭제하는 관리 명령.

사용법:
    python manage.py forget_memory 제주            # '제주' 든 줄 삭제 (전체 유저)
    python manage.py forget_memory 면접 이직        # 여러 키워드 동시
    python manage.py forget_memory 제주 --user 3    # 특정 user_id만
    python manage.py forget_memory 제주 --dry-run   # 실제 삭제 없이 미리보기

user_memory.summary_text는 유저당 한 블롭(여러 줄)이라, 키워드가 든 '줄만'
골라 빼고 나머지는 그대로 둔다.
"""
from django.core.management.base import BaseCommand

from chat.models import UserMemory


class Command(BaseCommand):
    help = 'user_memory 요약에서 특정 키워드가 든 줄을 삭제한다.'

    def add_arguments(self, parser):
        parser.add_argument('keywords', nargs='+', help='삭제할 줄에 포함된 키워드(공백 구분)')
        parser.add_argument('--user', type=int, default=None, help='특정 user_id만 대상 (기본: 전체)')
        parser.add_argument('--dry-run', action='store_true', help='실제 삭제 없이 미리보기')

    def handle(self, *args, **opts):
        keywords = opts['keywords']
        qs = UserMemory.objects.all()
        if opts['user'] is not None:
            qs = qs.filter(user_id=opts['user'])

        total_removed = 0
        touched_users = 0
        for mem in qs:
            text = mem.summary_text or ''
            if not text.strip():
                continue
            kept, removed = [], []
            for line in text.splitlines():
                if any(kw in line for kw in keywords):
                    removed.append(line)
                else:
                    kept.append(line)
            if not removed:
                continue

            touched_users += 1
            total_removed += len(removed)
            self.stdout.write(f'\n[user_id={mem.user_id}] 삭제 대상 {len(removed)}줄:')
            for line in removed:
                self.stdout.write(f'   - {line}')

            if not opts['dry_run']:
                mem.summary_text = '\n'.join(kept).strip()
                mem.save(update_fields=['summary_text', 'updated_at'])

        if opts['dry_run']:
            self.stdout.write(self.style.WARNING(
                f'\n[미리보기] 유저 {touched_users}명 / {total_removed}줄이 삭제될 예정 (실제 삭제 안 함).'))
        else:
            self.stdout.write(self.style.SUCCESS(
                f'\n완료: 유저 {touched_users}명 / {total_removed}줄 삭제됨.'))

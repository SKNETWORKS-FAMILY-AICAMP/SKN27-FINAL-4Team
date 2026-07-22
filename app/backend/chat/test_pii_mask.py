# -*- coding: utf-8 -*-
"""PII 마스킹 테스트 — 완전 마스킹 보장 + 일상 숫자 오폭 방지 박제.

실행: python manage.py test chat.test_pii_mask  (DB·LLM 불필요)
"""
from unittest import TestCase

from chat.pii_mask import mask, notice


class MaskTests(TestCase):
    def test_phone_mobile_variants(self):
        for raw in ('010-1234-5678', '010 1234 5678', '01012345678', '010.1234.5678'):
            out, found = mask(f'내 번호 {raw}로 바뀌었어')
            self.assertNotIn('5678', out, raw)       # 값 0비트 보존 확인
            self.assertIn('[전화번호]', out, raw)
            self.assertIn('전화번호', found)

    def test_landline(self):
        out, _ = mask('사무실은 02-312-4567이야')
        self.assertIn('[전화번호]', out)
        self.assertNotIn('4567', out)

    def test_rrn(self):
        out, found = mask('주민번호 900101-2345678 이거든')
        self.assertEqual(out, '주민번호 [주민번호] 이거든')
        self.assertIn('주민번호', found)

    def test_email(self):
        out, _ = mask('메일은 hansol.kim+test@gmail.com 이야')
        self.assertIn('[이메일]', out)
        self.assertNotIn('gmail', out)

    def test_card(self):
        out, _ = mask('카드 1234-5678-9012-3456 정지해야 해')
        self.assertIn('[카드번호]', out)
        self.assertNotIn('3456', out)

    def test_account_with_context(self):
        out, found = mask('내 계좌 110-234-567890 으로 입금해줘')
        self.assertIn('[계좌번호]', out)
        self.assertIn('계좌번호', found)

    def test_account_number_without_context_kept(self):
        """문맥 단어 없는 긴 숫자(운송장 등)는 계좌로 오폭하지 않는다"""
        out, found = mask('택배 운송장 6885-2403-1197 확인해봐')
        self.assertNotIn('[계좌번호]', out)

    def test_third_party_pii_also_masked(self):
        """제3자 정보도 마스킹 — 회원 본인 값 대조가 아닌 형태 기반의 핵심 근거"""
        out, _ = mask('내 친구 민수 번호는 010-9876-5432야')
        self.assertIn('[전화번호]', out)
        self.assertIn('민수', out)   # 이름·맥락은 보존

    def test_everyday_numbers_untouched(self):
        """날짜·D-day·금액·시각은 절대 건드리지 않는다 (오폭 = 기억 품질 파괴)"""
        for s in ('7월 20일에 병원 가', '2026-07-20 발표야', 'D-3 남았어',
                  '5만원 당첨됐어', '3시 30분에 보자', '수능 300점 목표'):
            out, found = mask(s)
            self.assertEqual(out, s, s)
            self.assertEqual(found, [], s)

    def test_notice_line(self):
        _, found = mask('번호 010-1111-2222랑 메일 a@b.com 남길게')
        line = notice(found)
        self.assertIn('전화번호', line)
        self.assertIn('이메일', line)
        self.assertEqual(notice([]), '')

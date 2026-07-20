# -*- coding: utf-8 -*-
"""채팅 암호화 테스트 — 왕복·레거시 평문·키 부재 폴백 박제.

실행: python manage.py test chat.test_crypto  (DB 불필요 — 필드 함수 직접 검증)
"""
import os
from unittest import TestCase, mock

from cryptography.fernet import Fernet

from chat import crypto_fields as cf


def _fresh_key_env(key: str):
    """키 교체 + 캐시 리셋 (모듈 캐시가 1회 로드라 테스트마다 초기화)."""
    cf._fernet_cache['loaded'] = False
    cf._fernet_cache['f'] = None
    return mock.patch.dict(os.environ, {'CHAT_ENC_KEY': key})


class CryptoTests(TestCase):
    def tearDown(self):
        cf._fernet_cache['loaded'] = False
        cf._fernet_cache['f'] = None

    def test_roundtrip(self):
        """암호화 → 복호화 왕복. 암호문엔 평문 흔적 0"""
        with _fresh_key_env(Fernet.generate_key().decode()):
            enc = cf.encrypt('나 오늘 회사에서 혼났어 ㅠㅠ')
            self.assertTrue(enc.startswith('enc:v1:'))
            self.assertNotIn('회사', enc)
            self.assertEqual(cf.decrypt(enc), '나 오늘 회사에서 혼났어 ㅠㅠ')

    def test_legacy_plaintext_passthrough(self):
        """접두사 없는 기존 평문은 그대로 읽힘 — 무중단 도입 보장"""
        with _fresh_key_env(Fernet.generate_key().decode()):
            self.assertEqual(cf.decrypt('옛날에 저장된 평문'), '옛날에 저장된 평문')

    def test_double_encrypt_is_noop(self):
        """이미 암호화된 값을 다시 저장해도 이중 암호화 안 됨 (encrypt_chat 멱등 근거)"""
        with _fresh_key_env(Fernet.generate_key().decode()):
            enc = cf.encrypt('한 번')
            self.assertEqual(cf.encrypt(enc), enc)

    def test_no_key_falls_back_to_plaintext(self):
        """키 미설정 → 평문 저장 (개발 편의) — 운영 체크리스트에서 키 필수로 방어"""
        with _fresh_key_env(''):
            self.assertEqual(cf.encrypt('키 없음'), '키 없음')

    def test_wrong_key_fails_loud_not_crash(self):
        """키 불일치 → 크래시 대신 명시적 실패 문구 (대화 흐름 무중단 원칙)"""
        with _fresh_key_env(Fernet.generate_key().decode()):
            enc = cf.encrypt('비밀')
        with _fresh_key_env(Fernet.generate_key().decode()):   # 다른 키
            self.assertIn('실패', cf.decrypt(enc))

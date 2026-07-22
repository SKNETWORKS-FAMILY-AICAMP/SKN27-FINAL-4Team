# -*- coding: utf-8 -*-
"""DB 채팅 암호화 (2026-07-15, 팀 안건) — 필드 레벨 대칭키(Fernet) 암호화.

설계:
- ChatMessage.content · UserMemory.summary_text를 저장 시 암호화, 읽을 때 복호화.
  DB가 통째로 유출돼도 대화 내용은 암호문 — "오래 보관(7일 삭제 보류)"의 전제 조건.
- 키: .env의 CHAT_ENC_KEY (Fernet 키). 생성:
    python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
- 접두사 'enc:v1:'로 암호문을 표시 → 접두사 없는 값은 평문(레거시)으로 그대로 읽음
  = 무중단 도입 (기존 행은 encrypt_chat 커맨드로 일괄 전환).
- 키 미설정 시: 평문 동작 + 기동 경고 1회 (개발 편의). ★운영 배포 체크리스트에 키 필수★
- 필드 클래스만 바뀌고 DB 컬럼 타입(TEXT)은 그대로 → 마이그레이션은 무SQL 형식 변경.

트레이드오프(의도): DB에서 content로 직접 검색(LIKE) 불가 — 우리 회상은 그래프·요약
경유라 원문 검색 의존이 없어서 수용. 관리자 열람도 앱(복호화 계층) 경유로만.
"""
import os

from django.db import models

_PREFIX = 'enc:v1:'
_fernet_cache = {'loaded': False, 'f': None}


def _fernet():
    """CHAT_ENC_KEY로 Fernet 1회 생성·캐시. 키 없으면 None(평문 모드 + 경고)."""
    if _fernet_cache['loaded']:
        return _fernet_cache['f']
    _fernet_cache['loaded'] = True
    key = os.environ.get('CHAT_ENC_KEY', '').strip()
    if not key:
        print('[crypto] CHAT_ENC_KEY 미설정 — 채팅 암호화 꺼짐(평문 저장). 운영 배포 전 필수!')
        return None
    try:
        from cryptography.fernet import Fernet
        _fernet_cache['f'] = Fernet(key.encode())
    except Exception as e:
        print(f'[crypto] CHAT_ENC_KEY 손상({e}) — 평문 모드로 폴백')
    return _fernet_cache['f']


def encrypt(value: str) -> str:
    """평문 → 'enc:v1:암호문'. 키 없거나 이미 암호문이면 그대로."""
    if not value or value.startswith(_PREFIX):
        return value
    f = _fernet()
    if f is None:
        return value
    return _PREFIX + f.encrypt(value.encode('utf-8')).decode('ascii')


def decrypt(value: str) -> str:
    """'enc:v1:암호문' → 평문. 접두사 없으면 레거시 평문으로 그대로 반환."""
    if not value or not value.startswith(_PREFIX):
        return value
    f = _fernet()
    if f is None:
        return '[암호화된 메시지 — CHAT_ENC_KEY 필요]'
    try:
        from cryptography.fernet import InvalidToken
        return f.decrypt(value[len(_PREFIX):].encode('ascii')).decode('utf-8')
    except Exception:
        return '[복호화 실패 — 키 불일치]'


class EncryptedTextField(models.TextField):
    """저장 시 암호화, 조회 시 복호화되는 TextField. 코드 어디서든 평문처럼 사용."""

    def get_prep_value(self, value):
        value = super().get_prep_value(value)
        return encrypt(value) if value else value

    def from_db_value(self, value, expression, connection):
        return decrypt(value) if value else value

    def to_python(self, value):
        return decrypt(value) if value else value

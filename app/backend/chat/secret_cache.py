# -*- coding: utf-8 -*-
"""시크릿 모드 전용 RAM/세션 캐시 (ERD v6.0 §3-2).

- 시크릿 세션의 대화 문맥은 서버 인메모리에만 유지, DB 저장 없음.
- 세션 종료(purge) 또는 TTL(30분) 만료 시 즉시 파기.
- 스케일아웃 필요 시 Redis로 교체 (2차 확장).
"""
import threading
import time

_TTL_SECONDS = 30 * 60
_lock = threading.Lock()
_store: dict[int, dict] = {}   # {session_id: {'history': [...], 'ts': float}}


def _expire_locked() -> None:
    now = time.time()
    for sid in [s for s, v in _store.items() if now - v['ts'] > _TTL_SECONDS]:
        del _store[sid]


def get_history(session_id: int) -> list:
    with _lock:
        _expire_locked()
        entry = _store.get(session_id)
        return list(entry['history']) if entry else []


def append(session_id: int, role: str, content: str) -> None:
    with _lock:
        _expire_locked()
        entry = _store.setdefault(session_id, {'history': [], 'ts': time.time()})
        entry['history'].append({'role': role, 'content': content})
        entry['history'] = entry['history'][-40:]   # 메모리 상한
        entry['ts'] = time.time()


def purge(session_id: int) -> None:
    """세션 종료 시 즉시 파기."""
    with _lock:
        _store.pop(session_id, None)

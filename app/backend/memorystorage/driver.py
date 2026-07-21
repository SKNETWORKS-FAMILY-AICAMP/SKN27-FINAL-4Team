# -*- coding: utf-8 -*-
"""기억보관함 전용 Neo4j 연결 관리.

대화 기억 저장기의 프로세스 캐시 상태와 무관하게 보관함이 직접 그래프를 조회할
수 있도록 읽기/삭제 API의 연결 책임을 이 모듈에 둔다.
"""
import os
import threading


_driver = None
_lock = threading.Lock()


def get_memory_driver():
    """사용 가능한 Neo4j 드라이버를 반환하며, 실패 후 다음 요청에서 재시도한다."""
    global _driver
    if _driver is not None:
        return _driver

    uri = os.environ.get('NEO4J_URI', '').strip()
    if not uri:
        return None

    with _lock:
        if _driver is not None:
            return _driver
        candidate = None
        try:
            from neo4j import GraphDatabase

            auth = (
                os.environ.get('NEO4J_USER', 'neo4j'),
                os.environ.get('NEO4J_PASSWORD', ''),
            )
            try:
                candidate = GraphDatabase.driver(
                    uri,
                    auth=auth,
                    notifications_min_severity='OFF',
                )
            except Exception:
                candidate = GraphDatabase.driver(uri, auth=auth)
            candidate.verify_connectivity()
            _driver = candidate
        except Exception:
            if candidate is not None:
                try:
                    candidate.close()
                except Exception:
                    pass
            _driver = None
        return _driver

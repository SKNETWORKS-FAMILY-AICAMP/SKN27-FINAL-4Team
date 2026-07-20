# -*- coding: utf-8 -*-
import re
from rest_framework import status
from rest_framework.decorators import api_view, authentication_classes, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from user.views import CsrfExemptSessionAuthentication
from chat.graph_memory import _get_driver

# 감정 영문 키를 따뜻한 한국어 감정 표현으로 치환하는 맵
EMOTION_MAP = {
    'joy': '기쁨과 설렘의',
    'sadness': '조금은 슬픈',
    'anger': '속상하고 화가 난',
    'flutter': '설렘이 가득한',
    'worry': '걱정과 불안이 섞인',
    'anxiety': '불안하고 걱정스러운',
    'hurt': '마음에 상처를 입은',
    'surprise': '조금 놀랍고 당황스러운'
}

EMOTION_MAP_SHORT = {
    'joy': '기쁨',
    'sadness': '슬픔',
    'anger': '화남/분노',
    'flutter': '설렘',
    'worry': '걱정/불안',
    'anxiety': '불안',
    'hurt': '상처',
    'surprise': '당황'
}


def _format_date(date_str):
    if not date_str:
        return None
    # YYYY-MM-DD 형식 매칭 및 변환
    m = re.match(r'^(\d{4})-(\d{2})-(\d{2})', date_str)
    if m:
        year, month, day = m.groups()
        return f"{int(year)}년 {int(month)}월 {int(day)}일"
    return date_str


def _make_event_sentence(name, date_str, people, emotions):
    friendly_date = _format_date(date_str)
    
    # 관련 인물 목록 추출 및 정제
    people_strs = []
    for p in people:
        p_name = p.get('name')
        p_rel = (p.get('relation') or '').strip()
        if p_name:
            if p_rel:
                people_strs.append(f"{p_rel} {p_name}")
            else:
                people_strs.append(p_name)

    # 감정 수식어 생성
    emo_str = ""
    valid_emotions = [em for em in emotions if em]
    if valid_emotions:
        # 첫 번째 기록된 정서를 대표 감정 수식어로 채택
        rep_emo = valid_emotions[0].lower()
        emo_str = EMOTION_MAP.get(rep_emo, f"'{rep_emo}'의") + " "

    if people_strs:
        people_str = ", ".join(people_strs)
        if friendly_date:
            return f"너가 {people_str}와(과) 함께하기로 한 {friendly_date}의 '{name}' 일정을 기억하고 있어. {emo_str}기억으로 다가가길 바라며, 준비는 잘 되어가고 있니?"
        return f"너가 {people_str}와(과) 함께했던 {emo_str}'{name}'에 관한 이야기를 기억하고 있어."

    if friendly_date:
        return f"너에게 다가오는 {friendly_date}의 '{name}' 일정을 기억하고 있어. {emo_str}시간이 되기를 바랄게."
    return f"이전 대화에서 너가 들려주었던 {emo_str}'{name}'에 관한 이야기를 소중하게 간직하고 있어."


@api_view(["GET"])
@authentication_classes([CsrfExemptSessionAuthentication])
@permission_classes([IsAuthenticated])
def memory_vault_list(request):
    """
    Neo4j 그래프 데이터베이스의 사건(Event) 노드를 중심으로 하여,
    엣지(INVOLVES, FELT)로 연결된 인물(Person) 및 감정(Emotion) 노드 데이터를 조회하여 반환합니다.
    """
    uid = request.user.id
    drv = _get_driver()
    if drv is None:
        return Response({"memories": []})

    # 사건(Event) 노드를 핵심으로 하여 엣지들을 한꺼번에 조회
    query = """
    MATCH (u:User {uid: $uid})-[:HAS_EVENT]->(e:Event)
    WHERE e.valid_until IS NULL
    OPTIONAL MATCH (e)-[:INVOLVES]->(p:Person)
    WHERE p.valid_until IS NULL AND (u)-[:KNOWS]->(p)
    OPTIONAL MATCH (e)-[:FELT]->(em:Emotion)
    RETURN e.key as key, e.name as name, e.date as date, 
           collect(distinct {name: p.name, relation: p.relation}) as people,
           collect(distinct em.type) as emotions
    """

    try:
        memories = []

        with drv.session() as session:
            records = session.run(query, uid=uid).data()
            for record in records:
                name_val = record.get('name')
                key_val = record.get('key') or name_val
                if not name_val:
                    continue
                
                raw_people = record.get('people') or []
                people = [p for p in raw_people if p.get('name')]
                
                raw_emotions = record.get('emotions') or []
                emotions = [em for em in raw_emotions if em]
                
                memories.append({
                    "id": f"event:{key_val}",
                    "title": name_val,
                    "content": _make_event_sentence(name_val, record.get('date'), people, emotions),
                    "saved_at": "",
                    "type": "event",
                    "raw_date": record.get('date') or "",
                    "raw_people": people,
                    "raw_emotions": [EMOTION_MAP_SHORT.get(em.lower(), em) for em in emotions if em]
                })

        return Response({"memories": memories})

    except Exception as e:
        return Response({"memories": [], "notice": f"기억 로드 중 오류 발생: {str(e)}"})


@api_view(["DELETE"])
@authentication_classes([CsrfExemptSessionAuthentication])
@permission_classes([IsAuthenticated])
def memory_vault_delete(request, memory_id):
    """Neo4j 데이터베이스에서 특정 사건(Event) 노드를 DETACH DELETE로 삭제합니다."""
    uid = request.user.id
    drv = _get_driver()
    if drv is None:
        return Response({"detail": "Neo4j 드라이버를 사용할 수 없습니다."}, status=status.HTTP_503_SERVICE_UNAVAILABLE)

    parts = memory_id.split(':', 1)
    if len(parts) == 2:
        kind, key = parts
    else:
        kind, key = None, memory_id

    query = "MATCH (u:User {uid: $uid})-[r:HAS_EVENT]->(e:Event {key: $key}) DETACH DELETE e"

    try:
        with drv.session() as session:
            session.run(query, uid=uid, key=key)
        return Response({"success": True})
    except Exception as e:
        return Response({"detail": f"삭제 오류: {str(e)}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

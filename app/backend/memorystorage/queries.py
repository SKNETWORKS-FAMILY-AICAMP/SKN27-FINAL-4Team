"""Neo4j 조회 쿼리.

서비스 코드가 기억 단위의 조립과 정책에 집중할 수 있도록 Cypher를 한곳에서
관리한다. 기억 식별자는 원문 Episode가 있으면 Episode id를, 없으면 User에
연결된 사실의 episode/작성 시각/그래프 element id를 순서대로 사용한다.
"""

MEMORY_UNITS_QUERY = """
MATCH (user:User {uid: $uid})
CALL {
    WITH user
    MATCH (user)-[:HAS_EVENT]->(event:Event {uid: $uid})
          <-[:RECORDS]-(source:Episode {uid: $uid})
    WHERE coalesce(event.suppressed, false) = false
    RETURN source.id AS memory_id,
           source.created_at AS authored_at,
           source.id AS source_id

    UNION

    WITH user
    MATCH (user)-[fact:HAS_EVENT]->(event:Event {uid: $uid})
    WHERE coalesce(event.suppressed, false) = false
      AND NOT EXISTS {
          MATCH (known_source:Episode {uid: $uid})
          WHERE known_source.id = fact.episode
      }
      AND (
          fact.episode IS NOT NULL
          OR NOT EXISTS {
              MATCH (:Episode {uid: $uid})-[:RECORDS]->(event)
          }
      )
    RETURN coalesce(
               fact.episode,
               fact.created_at,
               fact.valid_from,
               event.created_at,
               'event_' + replace(elementId(event), ':', '_')
           ) AS memory_id,
           coalesce(
               fact.created_at,
               fact.valid_from,
               event.created_at,
               ''
           ) AS authored_at,
           fact.episode AS source_id

    UNION

    WITH user
    MATCH (user)-[fact]->(person:Person)
    WHERE type(fact) = 'RELATES_TO'
    RETURN coalesce(
               fact.episode,
               fact.created_at,
               fact.valid_from,
               person.created_at,
               toLower(type(fact)) + '_' + replace(elementId(fact), ':', '_')
           ) AS memory_id,
           coalesce(
               fact.created_at,
               fact.valid_from,
               person.created_at,
               ''
           ) AS authored_at,
           fact.episode AS source_id

    UNION

    WITH user
    MATCH (user)-[fact:PREFERS]->(preference)
    WHERE preference:Topic OR preference:Preference
    RETURN coalesce(
               fact.episode,
               fact.created_at,
               fact.valid_from,
               preference.created_at,
               'preference_' + replace(elementId(fact), ':', '_')
           ) AS memory_id,
           coalesce(
               fact.created_at,
               fact.valid_from,
               preference.created_at,
               ''
           ) AS authored_at,
           fact.episode AS source_id
}
WITH user,
     memory_id,
     max(authored_at) AS fallback_authored_at,
     head([value IN collect(source_id) WHERE value IS NOT NULL]) AS source_id
OPTIONAL MATCH (source:Episode {uid: $uid})
WHERE source.id = source_id
RETURN memory_id,
       coalesce(source.created_at, fallback_authored_at, '') AS saved_at,
       coalesce(source.text, '') AS source_text,
       source.id IS NOT NULL AS has_source,
       elementId(user) AS user_node_id,
       properties(user) AS user_properties,
       elementId(source) AS source_node_id,
       properties(source) AS source_properties
ORDER BY saved_at DESC, memory_id DESC
"""


EVENT_CONTEXT_QUERY = """
MATCH (user:User {uid: $uid})
CALL {
    WITH user
    MATCH (user)-[has_event:HAS_EVENT]->(event:Event {uid: $uid})
          <-[records:RECORDS]-(source:Episode {uid: $uid})
    WHERE coalesce(event.suppressed, false) = false
    RETURN source.id AS memory_id, event, has_event, records

    UNION

    WITH user
    MATCH (user)-[fact:HAS_EVENT]->(event:Event {uid: $uid})
    WHERE coalesce(event.suppressed, false) = false
      AND NOT EXISTS {
          MATCH (known_source:Episode {uid: $uid})
          WHERE known_source.id = fact.episode
      }
      AND (
          fact.episode IS NOT NULL
          OR NOT EXISTS {
              MATCH (:Episode {uid: $uid})-[:RECORDS]->(event)
          }
      )
    RETURN coalesce(
               fact.episode,
               fact.created_at,
               fact.valid_from,
               event.created_at,
               'event_' + replace(elementId(event), ':', '_')
           ) AS memory_id,
           event,
           fact AS has_event,
           null AS records
}
WITH user, memory_id, event, has_event, records
WHERE memory_id IN $memory_ids
OPTIONAL MATCH (event)-[on_rel:ON]->(d:Date)
OPTIONAL MATCH (event)-[at_rel:AT]->(place:Place)
OPTIONAL MATCH (event)-[about_rel:ABOUT]->(topic:Topic)
OPTIONAL MATCH (event)-[involves_rel:INVOLVES]->(person:Person)
OPTIONAL MATCH (user)-[user_rel:RELATES_TO]->(person)
OPTIONAL MATCH (event)-[cause_rel:BECAUSE_OF]->(cause:Event)
RETURN memory_id,
       event.id AS event_id,
       event.key AS event_key,
       event.name AS event_name,
       event.created_at AS event_created_at,
       event.cause AS cause_text,
       event.salience AS salience,
       event.occurs_start AS occurs_start,
       event.occurs_end AS occurs_end,
       event.recall_count AS recall_count,
       event.suppressed AS suppressed,
       elementId(event) AS event_node_id,
       properties(event) AS event_properties,
       elementId(has_event) AS has_event_edge_id,
       properties(has_event) AS has_event_properties,
       elementId(records) AS records_edge_id,
       properties(records) AS records_properties,
       collect(DISTINCT d { .date, role: on_rel.role }) AS dates,
       collect(DISTINCT place.name) AS places,
       collect(DISTINCT topic.name) AS topics,
       collect(DISTINCT person {
           .name, .uid, .key, .suppressed,
           relation: user_rel.relation
       }) AS people,
       collect(DISTINCT cause {
           .id, .uid, .key, .name, .created_at, .cause,
           .salience, .occurs_start, .occurs_end, .recall_count, .suppressed
       }) AS causes,
       collect(DISTINCT {
           node_id: elementId(d),
           labels: labels(d),
           node: properties(d),
           edge_id: elementId(on_rel),
           edge_type: type(on_rel),
           edge: properties(on_rel)
       }) AS date_graph,
       collect(DISTINCT {
           node_id: elementId(place),
           labels: labels(place),
           node: properties(place),
           edge_id: elementId(at_rel),
           edge_type: type(at_rel),
           edge: properties(at_rel)
       }) AS place_graph,
       collect(DISTINCT {
           node_id: elementId(topic),
           labels: labels(topic),
           node: properties(topic),
           edge_id: elementId(about_rel),
           edge_type: type(about_rel),
           edge: properties(about_rel)
       }) AS topic_graph,
       collect(DISTINCT {
           node_id: elementId(person),
           labels: labels(person),
           node: properties(person),
           edge_id: elementId(involves_rel),
           edge_type: type(involves_rel),
           edge: properties(involves_rel),
           user_edge_id: elementId(user_rel),
           user_edge_type: type(user_rel),
           user_edge: properties(user_rel)
       }) AS person_graph,
       collect(DISTINCT {
           node_id: elementId(cause),
           labels: labels(cause),
           node: properties(cause),
           edge_id: elementId(cause_rel),
           edge_type: type(cause_rel),
           edge: properties(cause_rel)
       }) AS cause_graph
ORDER BY memory_id, event_created_at, event_id
"""


RELATION_CONTEXT_QUERY = """
MATCH (user:User {uid: $uid})-[rel]->(person:Person)
WHERE type(rel) = 'RELATES_TO'
WITH rel,
     person,
     coalesce(
         rel.episode,
         rel.created_at,
         rel.valid_from,
         person.created_at,
         toLower(type(rel)) + '_' + replace(elementId(rel), ':', '_')
     ) AS memory_id
WHERE memory_id IN $memory_ids
RETURN memory_id,
       person.name AS name,
       coalesce(rel.relation, person.relation, '지인') AS relation,
       coalesce(rel.valid_from, person.valid_from) AS valid_from,
       coalesce(rel.valid_to, person.valid_to) AS valid_to,
       coalesce(rel.end_reason, person.end_reason) AS end_reason,
       elementId(person) AS person_node_id,
       labels(person) AS person_labels,
       properties(person) AS person_properties,
       elementId(rel) AS relation_edge_id,
       type(rel) AS relation_edge_type,
       properties(rel) AS relation_properties
ORDER BY memory_id, name
"""


PREFERENCE_CONTEXT_QUERY = """
MATCH (user:User {uid: $uid})-[pref:PREFERS]->(topic)
WHERE topic:Topic OR topic:Preference
WITH pref,
     topic,
     coalesce(
         pref.episode,
         pref.created_at,
         pref.valid_from,
         topic.created_at,
         'preference_' + replace(elementId(pref), ':', '_')
     ) AS memory_id
WHERE memory_id IN $memory_ids
RETURN memory_id,
       coalesce(topic.name, topic.topic, topic.key) AS topic,
       coalesce(pref.polarity, topic.polarity, '호') AS polarity,
       coalesce(pref.valid_from, topic.valid_from) AS valid_from,
       coalesce(pref.valid_to, topic.valid_to) AS valid_to,
       coalesce(pref.end_reason, topic.end_reason) AS end_reason,
       elementId(topic) AS topic_node_id,
       labels(topic) AS topic_labels,
       properties(topic) AS topic_properties,
       elementId(pref) AS preference_edge_id,
       type(pref) AS preference_edge_type,
       properties(pref) AS preference_properties
ORDER BY memory_id, topic
"""


FIND_MEMORY_ORIGIN_QUERY = """
MATCH (user:User {uid: $uid})
CALL {
    WITH user
    MATCH (user)-[:HAS_EVENT]->(event:Event {uid: $uid})
          <-[:RECORDS]-(source:Episode {uid: $uid})
    WHERE source.id = $origin
      AND coalesce(event.suppressed, false) = false
    RETURN source.id AS memory_id

    UNION

    WITH user
    MATCH (user)-[fact:HAS_EVENT]->(event:Event {uid: $uid})
    WITH fact,
         event,
         coalesce(
             fact.episode,
             fact.created_at,
             fact.valid_from,
             event.created_at,
             'event_' + replace(elementId(event), ':', '_')
         ) AS memory_id
    WHERE memory_id = $origin
    RETURN memory_id

    UNION

    WITH user
    MATCH (user)-[fact]->(person:Person)
    WHERE type(fact) = 'RELATES_TO'
    WITH fact,
         person,
         coalesce(
             fact.episode,
             fact.created_at,
             fact.valid_from,
             person.created_at,
             toLower(type(fact)) + '_' + replace(elementId(fact), ':', '_')
         ) AS memory_id
    WHERE memory_id = $origin
    RETURN memory_id

    UNION

    WITH user
    MATCH (user)-[fact:PREFERS]->(preference)
    WHERE preference:Topic OR preference:Preference
    WITH fact,
         preference,
         coalesce(
             fact.episode,
             fact.created_at,
             fact.valid_from,
             preference.created_at,
             'preference_' + replace(elementId(fact), ':', '_')
         ) AS memory_id
    WHERE memory_id = $origin
    RETURN memory_id
}
WITH DISTINCT memory_id
OPTIONAL MATCH (source:Episode {uid: $uid})
WHERE source.id = memory_id
RETURN memory_id, source.id IS NOT NULL AS has_source
LIMIT 1
"""

FIND_EVENT_ORIGIN_QUERY = (
    'MATCH (ep:Episode {uid:$uid})-[:RECORDS]->'
    '(e:Event {uid:$uid,key:$key}) '
    'RETURN ep.id AS memory_id, true AS has_source '
    'ORDER BY ep.created_at DESC LIMIT 1'
)

FIND_MEMORY_EVENTS_QUERY = """
MATCH (user:User {uid: $uid})
CALL {
    WITH user
    MATCH (user)-[:HAS_EVENT]->(event:Event {uid: $uid})
          <-[:RECORDS]-(source:Episode {uid: $uid, id: $origin})
    RETURN event

    UNION

    WITH user
    MATCH (user)-[fact:HAS_EVENT]->(event:Event {uid: $uid})
    WITH fact,
         event,
         coalesce(
             fact.episode,
             fact.created_at,
             fact.valid_from,
             event.created_at,
             'event_' + replace(elementId(event), ':', '_')
         ) AS memory_id
    WHERE memory_id = $origin
    RETURN event
}
RETURN DISTINCT event.id AS id, event.key AS key
"""

DELETE_EVENT_FACTS_QUERY = """
MATCH (user:User {uid: $uid})-[fact:HAS_EVENT]->(event:Event {uid: $uid})
WITH fact,
     event,
     coalesce(
         fact.episode,
         fact.created_at,
         fact.valid_from,
         event.created_at,
         'event_' + replace(elementId(event), ':', '_')
     ) AS memory_id
WHERE memory_id = $origin
DELETE fact
"""

DELETE_RELATION_FACTS_QUERY = """
MATCH (user:User {uid: $uid})-[fact]->(person:Person)
WHERE type(fact) = 'RELATES_TO'
WITH fact,
     person,
     coalesce(
         fact.episode,
         fact.created_at,
         fact.valid_from,
         person.created_at,
         toLower(type(fact)) + '_' + replace(elementId(fact), ':', '_')
     ) AS memory_id
WHERE memory_id = $origin
DELETE fact
"""

DELETE_PREFERENCE_FACTS_QUERY = """
MATCH (user:User {uid: $uid})-[fact:PREFERS]->(preference)
WHERE preference:Topic OR preference:Preference
WITH fact,
     preference,
     coalesce(
         fact.episode,
         fact.created_at,
         fact.valid_from,
         preference.created_at,
         'preference_' + replace(elementId(fact), ':', '_')
     ) AS memory_id
WHERE memory_id = $origin
DELETE fact
"""

DELETE_EVENT_CONTEXT_QUERY = """
MATCH (event:Event {uid: $uid})-[fact]->()
WHERE type(fact) IN ['ON', 'AT', 'ABOUT', 'INVOLVES', 'EVOKED']
  AND coalesce(
      fact.episode,
      fact.created_at,
      fact.valid_from,
      ''
  ) = $origin
DELETE fact
"""

DELETE_CAUSAL_LINKS_QUERY = (
    'MATCH (a:Event {uid:$uid})-[r:BECAUSE_OF]->(b:Event {uid:$uid}) '
    'WHERE (a.id IN $event_ids OR a.key IN $event_keys) '
    'AND (b.id IN $event_ids OR b.key IN $event_keys) '
    'DELETE r'
)

DELETE_SOURCE_QUERY = (
    'MATCH (source:Episode {uid:$uid,id:$origin}) DETACH DELETE source'
)

RESTORE_EVENT_FACTS_QUERY = """
MATCH (user:User {uid: $uid}),
      (source:Episode {uid: $uid})-[:RECORDS]->(event:Event {uid: $uid})
WHERE (event.id IN $event_ids OR event.key IN $event_keys)
  AND NOT EXISTS { MATCH (user)-[:HAS_EVENT]->(event) }
WITH user, event, source
ORDER BY source.created_at DESC
WITH user, event, head(collect(source)) AS source
MERGE (user)-[fact:HAS_EVENT]->(event)
ON CREATE SET fact.valid_from = source.created_at,
              fact.valid_to = null,
              fact.created_at = source.created_at,
              fact.episode = source.id
"""

FIND_ORPHAN_EVENTS_QUERY = (
    'MATCH (e:Event {uid:$uid}) '
    'WHERE (e.id IN $event_ids OR e.key IN $event_keys) '
    'AND NOT EXISTS { MATCH (:Episode {uid:$uid})-[:RECORDS]->(e) } '
    'AND NOT EXISTS { MATCH (:User {uid:$uid})-[:HAS_EVENT]->(e) } '
    'RETURN DISTINCT e.id AS id, e.key AS key'
)

DELETE_ORPHAN_EVENTS_QUERY = (
    'MATCH (e:Event {uid:$uid}) '
    'WHERE e.id IN $event_ids OR e.key IN $event_keys '
    'DETACH DELETE e'
)

DELETE_ORPHAN_CONTEXT_QUERY = (
    'MATCH (n) '
    'WHERE (n:Person OR n:Date OR n:Place OR n:Topic OR n:Preference '
    'OR n:Emotion) '
    'AND NOT EXISTS { MATCH (n)--() } '
    'DELETE n'
)

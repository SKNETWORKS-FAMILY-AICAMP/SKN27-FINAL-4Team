"""Verify MindReport persistence against the configured real databases."""

from __future__ import annotations

from datetime import date
import json
import os
from uuid import uuid4

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError
from django.db import connection
from django.utils import timezone
from neo4j import GraphDatabase

from mindreport.constants import PERIOD_WEEK
from mindreport.models import MindReport
from mindreport.services.collection import collect_ltm_events
from mindreport.services.persistence import (
    list_latest_period_reports,
    period_report_exists,
    save_period_report,
)


class Command(BaseCommand):
    help = (
        "Create isolated probe data in the configured PostgreSQL and Neo4j, "
        "verify MindReport write/read/deduplication and LTM lookup, then clean it up."
    )

    def handle(self, *args, **options):
        probe = uuid4().hex
        target_date = date(2026, 7, 30)
        user = None
        graph_driver = None
        result = {
            "executed_at": timezone.localtime().isoformat(),
            "probe": probe,
            "postgresql": {"checks": []},
            "neo4j": {"checks": []},
            "cleanup": {},
            "overall": "FAIL",
        }

        try:
            self._verify_postgresql(result, probe)
            user = get_user_model().objects.create_user(
                email=f"codex-mindreport-{probe}@example.invalid",
                password=None,
                nickname="storage-probe",
            )
            result["postgresql"]["probe_user_id"] = user.pk
            self._verify_mindreport_persistence(result, user, target_date)

            graph_driver = self._connect_neo4j(result)
            self._verify_neo4j_ltm(
                result,
                graph_driver,
                user=user,
                probe=probe,
                target_date=target_date,
            )
            result["overall"] = "PASS"
        except Exception as exc:
            result["error"] = f"{type(exc).__name__}: {exc}"
        finally:
            if graph_driver is not None:
                try:
                    graph_driver.execute_query(
                        "MATCH (n {_codex_probe: $probe}) DETACH DELETE n",
                        probe=probe,
                        database_="neo4j",
                    )
                    remaining = graph_driver.execute_query(
                        "MATCH (n {_codex_probe: $probe}) RETURN count(n) AS count",
                        probe=probe,
                        database_="neo4j",
                    ).records[0]["count"]
                    result["cleanup"]["neo4j_probe_nodes_remaining"] = remaining
                except Exception as cleanup_exc:
                    result["cleanup"]["neo4j_error"] = str(cleanup_exc)
                finally:
                    graph_driver.close()

            if user is not None:
                probe_user_id = user.pk
                user.delete()
                result["cleanup"]["postgres_probe_user_remaining"] = (
                    get_user_model().objects.filter(pk=probe_user_id).count()
                )
                result["cleanup"]["postgres_probe_reports_remaining"] = (
                    MindReport.objects.filter(user_id=probe_user_id).count()
                )

        cleanup_ok = all(
            value == 0
            for key, value in result["cleanup"].items()
            if key.endswith("_remaining")
        ) and not any(key.endswith("_error") for key in result["cleanup"])
        result["cleanup"]["status"] = "PASS" if cleanup_ok else "FAIL"

        self.stdout.write(json.dumps(result, ensure_ascii=False, indent=2))
        if result["overall"] != "PASS" or not cleanup_ok:
            raise CommandError("MindReport real storage integration verification failed.")

    @staticmethod
    def _record_check(section: dict, name: str, condition: bool) -> None:
        section["checks"].append({"name": name, "status": "PASS" if condition else "FAIL"})
        if not condition:
            raise AssertionError(name)

    def _verify_postgresql(self, result: dict, probe: str) -> None:
        section = result["postgresql"]
        with connection.cursor() as cursor:
            cursor.execute("SELECT version()")
            version = cursor.fetchone()[0]
            cursor.execute("SELECT current_database()")
            database_name = cursor.fetchone()[0]
            cursor.execute("SELECT %s::text", [probe])
            round_trip = cursor.fetchone()[0]

        section.update(
            {
                "vendor": connection.vendor,
                "engine": connection.settings_dict["ENGINE"],
                "database": database_name,
                "host": connection.settings_dict["HOST"],
                "port": str(connection.settings_dict["PORT"]),
                "server_version": version,
            }
        )
        self._record_check(section, "configured backend is PostgreSQL", connection.vendor == "postgresql")
        self._record_check(section, "parameterized SQL round trip", round_trip == probe)

    def _verify_mindreport_persistence(self, result: dict, user, target_date: date) -> None:
        section = result["postgresql"]
        fallback_payload = self._payload(title="fallback-probe", is_fallback=True)
        real_payload = self._payload(title="real-probe", is_fallback=False)

        created = save_period_report(
            user=user,
            payload=fallback_payload,
            period_type=PERIOD_WEEK,
            period_name="주간",
            target_date=target_date,
        )
        updated = save_period_report(
            user=user,
            payload=real_payload,
            period_type=PERIOD_WEEK,
            period_name="주간",
            target_date=target_date,
        )
        updated.refresh_from_db()
        stored = MindReport.objects.get(pk=updated.pk)
        latest = list_latest_period_reports(user)

        self._record_check(section, "MindReport INSERT persisted", created.pk is not None)
        self._record_check(section, "same-period UPSERT reused row", created.pk == updated.pk)
        self._record_check(
            section,
            "same-period duplicate removed",
            MindReport.objects.filter(user=user).count() == 1,
        )
        self._record_check(
            section,
            "JSON fields round trip",
            stored.stress_causes == ["업무"]
            and stored.relief_causes == ["산책"]
            and stored.emotions == [{"name": "기쁨", "score": 64}],
        )
        self._record_check(
            section,
            "fallback replaced by real report",
            stored.title == "real-probe" and stored.is_fallback is False,
        )
        self._record_check(
            section,
            "period existence query",
            period_report_exists(
                user=user,
                period_type=PERIOD_WEEK,
                period_name="주간",
                target_date=target_date,
            ),
        )
        self._record_check(
            section,
            "latest-period serialization query",
            len(latest) == 1
            and latest[0]["title"] == "real-probe"
            and latest[0]["stressCauses"] == ["업무"],
        )

    @staticmethod
    def _payload(*, title: str, is_fallback: bool) -> dict:
        return {
            "type": "주간 (데이터 부족)" if is_fallback else "주간",
            "range": "the persistence layer must canonicalize this value",
            "title": title,
            "summary": "실제 PostgreSQL 저장소 왕복 검증",
            "stressCauses": ["업무"],
            "reliefCauses": ["산책"],
            "causeLabels": [
                {
                    "causeType": "stress",
                    "keyword": "업무",
                    "momentDescription": "검증용 데이터",
                }
            ],
            "emotions": [{"name": "기쁨", "score": 64}],
            "analysis": ["실제 DB JSONB 왕복"],
            "recommendations": ["검증 후 데이터 삭제"],
            "is_fallback": is_fallback,
            "is_safety_response": False,
        }

    def _connect_neo4j(self, result: dict):
        uri = os.environ.get("NEO4J_URI", "").strip()
        if not uri:
            raise RuntimeError("NEO4J_URI is not configured")
        driver = GraphDatabase.driver(
            uri,
            auth=(
                os.environ.get("NEO4J_USER", "neo4j"),
                os.environ.get("NEO4J_PASSWORD", ""),
            ),
            notifications_min_severity="OFF",
        )
        driver.verify_connectivity()
        component = driver.execute_query(
            "CALL dbms.components() YIELD name, versions RETURN name, versions",
            database_="neo4j",
        ).records[0]
        result["neo4j"].update(
            {
                "uri": uri,
                "component": component["name"],
                "version": component["versions"][0],
            }
        )
        self._record_check(result["neo4j"], "driver connectivity", True)
        return driver

    def _verify_neo4j_ltm(
        self,
        result: dict,
        driver,
        *,
        user,
        probe: str,
        target_date: date,
    ) -> None:
        section = result["neo4j"]
        existing = driver.execute_query(
            "MATCH (u:User {uid: $uid}) RETURN count(u) AS count",
            uid=user.pk,
            database_="neo4j",
        ).records[0]["count"]
        self._record_check(section, "probe uid is isolated", existing == 0)

        event_id = f"codex-event-{probe}"
        event_name = f"실제 Neo4j 조회 {probe[:8]}"
        driver.execute_query(
            """
            CREATE (u:User {uid: $uid, _codex_probe: $probe})
            CREATE (ep:Episode {
                id: $episode_id,
                uid: $uid,
                created_at: '2026-07-28T09:00:00+09:00',
                _codex_probe: $probe
            })
            CREATE (e:Event {
                id: $event_id,
                uid: $uid,
                name: $event_name,
                cause: '실제 그래프 저장소 검증',
                occurs_start: '2026-07-28',
                occurs_end: '2026-07-29',
                suppressed: false,
                top_emotion: $emotion_type,
                _codex_probe: $probe
            })
            CREATE (p:Person {
                uid: $uid,
                key: $person_key,
                name: $person_name,
                _codex_probe: $probe
            })
            CREATE (em:Emotion {type: $emotion_type, _codex_probe: $probe})
            CREATE (place:Place {name: $place_name, _codex_probe: $probe})
            CREATE (topic:Topic {name: $topic_name, _codex_probe: $probe})
            CREATE (ep)-[:RECORDS]->(e)
            CREATE (u)-[:HAS_EVENT]->(e)
            CREATE (e)-[:INVOLVES]->(p)
            CREATE (u)-[:RELATES_TO {relation: '동료'}]->(p)
            CREATE (e)-[:EVOKED {score: 0.81}]->(em)
            CREATE (e)-[:AT]->(place)
            CREATE (e)-[:ABOUT]->(topic)
            """,
            uid=user.pk,
            probe=probe,
            episode_id=f"codex-episode-{probe}",
            event_id=event_id,
            event_name=event_name,
            person_key=f"codex-person-{probe}",
            person_name=f"검증인물-{probe[:8]}",
            emotion_type=f"probe-emotion-{probe[:8]}",
            place_name=f"검증장소-{probe}",
            topic_name=f"검증주제-{probe}",
            database_="neo4j",
        )
        node_count = driver.execute_query(
            "MATCH (n {_codex_probe: $probe}) RETURN count(n) AS count",
            probe=probe,
            database_="neo4j",
        ).records[0]["count"]
        self._record_check(section, "probe graph persisted", node_count == 7)

        events = collect_ltm_events(
            user=user,
            period_type=PERIOD_WEEK,
            target_date=target_date,
        )
        self._record_check(section, "real LTM Cypher returned one event", len(events) == 1)
        event = events[0]
        self._record_check(
            section,
            "event fields mapped",
            event.event_id == event_id
            and event.name == event_name
            and event.occurs_start == "2026-07-28"
            and event.occurs_end == "2026-07-29",
        )
        self._record_check(
            section,
            "related graph fields mapped",
            len(event.people) == 1
            and len(event.places) == 1
            and len(event.topics) == 1
            and len(event.emotions) == 1,
        )

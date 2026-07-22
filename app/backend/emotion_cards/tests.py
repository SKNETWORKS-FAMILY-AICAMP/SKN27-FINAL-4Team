from copy import deepcopy
import tempfile
from unittest.mock import patch
from pathlib import Path

from django.conf import settings
from django.core.management import call_command
from django.test import TestCase, override_settings

from user.models import User

from .management.commands.import_emotion_card_data import validate_data_files
from .models import (
    CatalogEntry,
    EmotionCardJob,
    GeneratedEmotionCard,
)
from .prompt_compiler import PROMPT_MAX_CHARS, build_image_prompt
from .scene_pipeline import (
    build_candidate_pool,
    deterministic_scene_plan,
    resolve_scene_constraints,
    validate_scene_plan,
)
from .services import analyze, build_scene


@override_settings(
    EMOTION_CARD_ENABLE_LLM_ANALYSIS=False,
    EMOTION_CARD_SCENE_DIRECTOR_ENABLED=False,
    EMOTION_CARD_ENABLE_REAL_IMAGE_API=False,
    MEDIA_ROOT=tempfile.gettempdir(),
)
class EmotionCardPipelineTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        call_command("import_emotion_card_data")
        cls.user = User.objects.create_user(
            email="emotion-pipeline@example.com",
            password="password",
            nickname="마음이",
            character="pori",
            onboarding_done=True,
        )

    def make_analysis(self, text, **extra):
        payload = {"raw_text": text, "emotion_text": text, **extra}
        return analyze(payload, self.user)

    def test_rainy_sad_record_extracts_facts_without_need_defaults(self):
        analysis = self.make_analysis("오늘 비와서 우울했어")
        result = analysis.result

        self.assertEqual(result["primary_emotion"]["code"], "SADNESS")
        self.assertEqual(result["emotion_cause_type"], "WEATHER")
        self.assertEqual(result["explicit_weather"], "RAIN")
        self.assertEqual(result["explicit_time"], "TODAY")
        self.assertIsNone(result["energy"])
        self.assertIsNone(result["need"])
        self.assertEqual(result["field_sources"]["explicit_weather"], "EXPLICIT")
        self.assertIn("explicit_weather", result["evidence_map"])

    def test_rain_does_not_override_explicit_joy(self):
        result = self.make_analysis("비는 왔지만 기분은 좋았어").result
        self.assertEqual(result["primary_emotion"]["code"], "JOY")
        self.assertEqual(result["explicit_weather"], "RAIN")

    def test_timeline_uses_final_emotion_and_preserves_rain_as_a_trace(self):
        analysis = self.make_analysis(
            "아침에 비가와서 우울했는데 퇴근할 때 되니까 "
            "날이 맑아져서 기분이 좋아졌어"
        )
        result = analysis.result

        self.assertEqual(result["initial_emotion"], "SADNESS")
        self.assertEqual(result["final_emotion"], "JOY")
        self.assertEqual(result["primary_emotion"]["code"], "JOY")
        self.assertEqual(result["secondary_emotion"], "SADNESS")
        self.assertEqual(result["emotion_transition"], "SADNESS_TO_JOY")
        self.assertEqual(result["initial_weather"], "RAIN")
        self.assertEqual(result["final_weather"], "CLEAR")
        self.assertEqual(result["weather_transition"], "RAIN_TO_CLEAR")
        self.assertEqual(result["scene_weather"], "AFTER_RAIN")
        self.assertEqual(result["explicit_time"], "MORNING")
        self.assertEqual(result["scene_time"]["anchor"], "AFTER_WORK")
        self.assertEqual(
            result["scene_time"]["range"],
            ["EVENING", "NIGHT"],
        )
        self.assertEqual(
            result["scene_time"]["range_source"],
            "HIGH_CONFIDENCE_INFERRED",
        )
        self.assertAlmostEqual(
            result["scene_time"]["range_confidence"],
            0.82,
        )

        pool = build_candidate_pool(analysis)
        after_rain = next(
            item
            for item in pool["weather"]
            if item["candidate_id"] == "WTH_AFTER_RAIN"
        )
        self.assertTrue(after_rain["hard_required"])
        self.assertIn("WEATHER_TRANSITION", after_rain["reason_codes"])

        scene = build_scene(analysis)
        self.assertEqual(
            scene.scene_spec["selected_elements"]["weather_id"],
            "WTH_AFTER_RAIN",
        )
        self.assertEqual(scene.scene_spec["primary_emotion"], "JOY")
        self.assertIn(
            "Wet surfaces and leftover droplets",
            scene.scene_spec["environment_narrative"],
        )
        self.assertTrue(scene.scene_spec["optional_visual_cues"])

    def test_route_anchors_preserve_order_without_inventing_clock_time(self):
        result = self.make_analysis(
            "집에서 나서는 길에는 불안했지만 "
            "집으로 돌아오는 길에는 안도했어"
        ).result

        self.assertEqual(result["primary_emotion"]["code"], "JOY")
        self.assertEqual(result["initial_emotion"], "ANXIETY")
        self.assertEqual(result["final_emotion"], "JOY")
        self.assertEqual(result["scene_time"]["anchor"], "RETURNING_HOME")
        self.assertEqual(result["scene_time"]["range"], [])
        self.assertEqual(
            result["scene_time"]["range_source"],
            "NOT_PROVIDED",
        )
        self.assertEqual(
            [item["time_anchor"] for item in result["timeline"]],
            ["LEAVING_HOME", "RETURNING_HOME"],
        )

    def test_explicit_time_overrides_typical_after_work_time_range(self):
        result = self.make_analysis(
            "야간 근무를 마치고 퇴근할 때 아침 해를 보니 "
            "기분이 좋아졌어"
        ).result

        self.assertEqual(result["scene_time"]["anchor"], "AFTER_WORK")
        self.assertEqual(result["scene_time"]["range"], ["MORNING"])
        self.assertEqual(result["scene_time"]["range_source"], "EXPLICIT")
        self.assertEqual(result["scene_time"]["range_confidence"], 1.0)

    def test_llm_timeline_can_supply_a_final_emotion_not_in_keyword_fallback(self):
        text = "아침에는 우울했는데 귀갓길에는 홀가분해졌어"
        llm_result = {
            "primary_emotion": "JOY",
            "secondary_emotion": "SADNESS",
            "initial_emotion": "SADNESS",
            "final_emotion": "JOY",
            "emotion_transition": "SADNESS_TO_JOY",
            "emotion_intensity": "MEDIUM",
            "valence": "MIXED",
            "emotion_cause_type": "DAILY_LIFE",
            "emotion_cause_summary": "하루 동안 달라진 마음",
            "event_type_id": "EVT_UNSPECIFIED",
            "event_summary": "외출 후 돌아오는 과정에서 달라진 마음",
            "event_outcome": "OUT_RELIEF",
            "event_stage": "COMPLETED",
            "social_context": "NOT_DISCLOSED",
            "explicit_time": "MORNING",
            "timeline": [
                {
                    "sequence": 1,
                    "clause_text": "아침에는 우울했는데",
                    "time_anchor": "MORNING",
                    "time_anchor_expression": "아침",
                    "time_anchor_source": "EXPLICIT",
                    "time_anchor_confidence": 1.0,
                    "time_range": ["MORNING"],
                    "time_range_source": "EXPLICIT",
                    "time_range_confidence": 1.0,
                    "emotion": "SADNESS",
                    "emotion_evidence": "우울",
                },
                {
                    "sequence": 2,
                    "clause_text": "귀갓길에는 홀가분해졌어",
                    "time_anchor": "RETURNING_HOME",
                    "time_anchor_expression": "귀갓길",
                    "time_anchor_source": "EXPLICIT",
                    "time_anchor_confidence": 1.0,
                    "time_range": [],
                    "time_range_source": "NOT_PROVIDED",
                    "time_range_confidence": 0.0,
                    "emotion": "JOY",
                    "emotion_evidence": "홀가분해졌어",
                },
            ],
            "evidence_map": {
                "primary_emotion": "홀가분해졌어",
                "explicit_time": "아침",
            },
            "field_sources": {
                "primary_emotion": "EXPLICIT",
                "explicit_time": "EXPLICIT",
            },
            "field_confidences": {
                "primary_emotion": 1.0,
                "explicit_time": 1.0,
            },
            "analysis_status": "MIXED",
        }
        with patch(
            "emotion_cards.analysis._llm_extract_facts",
            return_value=(llm_result, "timeline-test-model"),
        ):
            result = self.make_analysis(text).result

        self.assertEqual(result["primary_emotion"]["code"], "JOY")
        self.assertEqual(result["initial_emotion"], "SADNESS")
        self.assertEqual(result["final_emotion"], "JOY")
        self.assertEqual(result["scene_time"]["anchor"], "RETURNING_HOME")
        self.assertEqual(result["scene_time"]["range"], [])
        self.assertEqual(result["analysis_source"], "timeline-test-model")

    def test_negated_rain_becomes_hard_forbidden(self):
        analysis = self.make_analysis("비가 안 왔는데도 마음이 흐렸어")
        self.assertIn("RAIN", analysis.result["negated_elements"])
        pool = build_candidate_pool(analysis)
        rain = next(
            item
            for item in pool["weather"]
            if item["candidate_id"] == "WTH_RAIN"
        )
        self.assertTrue(rain["hard_forbidden"])

    def test_friends_cafe_and_rain_are_preserved_as_explicit_facts(self):
        result = self.make_analysis(
            "친구랑 카페에서 비를 피했는데 즐거웠어"
        ).result
        self.assertEqual(result["primary_emotion"]["code"], "JOY")
        self.assertEqual(result["social_context"], "FRIENDS")
        self.assertEqual(result["explicit_place"], "카페")
        self.assertEqual(result["explicit_weather"], "RAIN")

    def test_short_ambiguous_input_does_not_create_energy_or_need(self):
        result = self.make_analysis("그냥 그래").result
        self.assertIsNone(result["energy"])
        self.assertIsNone(result["need"])
        self.assertEqual(
            result["field_sources"]["energy_code"],
            "NOT_PROVIDED",
        )
        self.assertEqual(
            result["field_sources"]["need_code"],
            "NOT_PROVIDED",
        )

    def test_duplicate_emotion_and_memory_text_is_normalized_once(self):
        text = "오늘 비와서 우울했어"
        analysis = analyze(
            {"emotion_text": text, "memory_text": text},
            self.user,
        )
        self.assertEqual(analysis.raw_input["raw_text"], text)
        self.assertEqual(analysis.raw_input["memory_text"], "")

    def test_raw_text_field_is_processed_without_legacy_fields(self):
        result = analyze(
            {"raw_text": "오늘 비와서 우울했어"},
            self.user,
        ).result
        self.assertEqual(result["primary_emotion"]["code"], "SADNESS")
        self.assertEqual(result["emotion_cause_type"], "WEATHER")
        self.assertEqual(result["explicit_weather"], "RAIN")

    def test_explicit_rain_is_hard_required_and_clouds_cannot_override_it(self):
        analysis = self.make_analysis("오늘 비와서 우울했어")
        pool = build_candidate_pool(analysis)
        rain = next(
            item
            for item in pool["weather"]
            if item["candidate_id"] == "WTH_RAIN"
        )
        self.assertTrue(rain["hard_required"])
        scene = build_scene(analysis)
        self.assertEqual(
            scene.scene_spec["selected_elements"]["weather_id"],
            "WTH_RAIN",
        )

    def test_indoor_fact_excludes_outdoor_only_action_candidate(self):
        entry = CatalogEntry.objects.get(
            catalog="action",
            code="ACT_SLOW_WALK",
        )
        entry.metadata = {
            **entry.metadata,
            "required_location_tags": "OUTDOOR",
        }
        entry.save(update_fields=["metadata"])
        analysis = self.make_analysis("카페에서 우울했어")
        pool = build_candidate_pool(analysis)
        walk = next(
            item
            for item in pool["action"]
            if item["candidate_id"] == "ACT_SLOW_WALK"
        )
        self.assertTrue(walk["hard_forbidden"])
        self.assertIn(
            "EXPLICIT_ENVIRONMENT_CONFLICT",
            walk["excluded_reasons"],
        )

    def test_alone_removes_companion_candidates(self):
        pool = build_candidate_pool(
            self.make_analysis("밤에 혼자 걸어서 조금 무서웠어")
        )
        self.assertFalse(pool.get("companions"))

    def test_null_energy_and_need_contribute_no_candidate_score(self):
        pool = build_candidate_pool(
            self.make_analysis("오늘 비와서 우울했어")
        )
        all_reasons = {
            reason
            for items in pool.values()
            for item in items
            for reason in item["reason_codes"]
        }
        self.assertNotIn("ENERGY_PREFERENCE", all_reasons)
        self.assertNotIn("NEED_PREFERENCE", all_reasons)

    def _validated_rain_fixture(self):
        analysis = self.make_analysis("오늘 비와서 우울했어")
        pool = build_candidate_pool(analysis)
        constraints = resolve_scene_constraints(
            analysis,
            pool,
            "SAFE",
        )
        plan = deterministic_scene_plan(
            analysis,
            pool,
            constraints,
        )
        valid, errors = validate_scene_plan(
            plan,
            analysis,
            pool,
            constraints,
        )
        self.assertTrue(valid, errors)
        return analysis, pool, constraints, plan

    def test_scene_validation_rejects_id_outside_candidate_pool(self):
        analysis, pool, constraints, plan = self._validated_rain_fixture()
        plan["selected_elements"]["location_id"] = "LOC_NOT_REAL"
        valid, errors = validate_scene_plan(
            plan,
            analysis,
            pool,
            constraints,
        )
        self.assertFalse(valid)
        self.assertTrue(
            any(error.startswith("ID_NOT_IN_CANDIDATE_POOL") for error in errors)
        )

    def test_scene_validation_rejects_missing_required_weather_cues(self):
        analysis, pool, constraints, plan = self._validated_rain_fixture()
        plan["required_visual_cues"] = []
        valid, errors = validate_scene_plan(
            plan,
            analysis,
            pool,
            constraints,
        )
        self.assertFalse(valid)
        self.assertIn("REQUIRED_VISUAL_CUES_INSUFFICIENT", errors)

    def test_scene_validation_rejects_sunny_sky_for_explicit_rain(self):
        analysis, pool, constraints, plan = self._validated_rain_fixture()
        plan["scene_summary_en"] += " A clear sunny sky fills the scene."
        valid, errors = validate_scene_plan(
            plan,
            analysis,
            pool,
            constraints,
        )
        self.assertFalse(valid)
        self.assertIn(
            "FORBIDDEN_VISUAL_PRESENT:clear sunny sky",
            errors,
        )

    def test_scene_validation_preserves_explicit_place_action_and_objects(self):
        analysis = self.make_analysis(
            "친구랑 카페에서 비를 피했는데 즐거웠어",
            memory_text="머그잔을 들고 있었어",
        )
        # The separate memory adds an explicit object while preserving the
        # original emotion/event sentence as a distinct input.
        analysis.result["explicit_objects"] = ["머그잔"]
        analysis.result["field_sources"]["explicit_objects"] = "EXPLICIT"
        analysis.save(update_fields=["result"])
        pool = build_candidate_pool(analysis)
        constraints = resolve_scene_constraints(analysis, pool, "SAFE")
        plan = deterministic_scene_plan(analysis, pool, constraints)
        valid, errors = validate_scene_plan(
            plan,
            analysis,
            pool,
            constraints,
        )
        self.assertTrue(valid, errors)

    def test_scene_validation_rejects_negated_element(self):
        analysis = self.make_analysis("비가 안 왔는데도 마음이 흐렸어")
        pool = build_candidate_pool(analysis)
        constraints = resolve_scene_constraints(analysis, pool, "SAFE")
        plan = deterministic_scene_plan(analysis, pool, constraints)
        plan["selected_elements"]["weather_id"] = "WTH_RAIN"
        valid, errors = validate_scene_plan(
            plan,
            analysis,
            pool,
            constraints,
        )
        self.assertFalse(valid)
        self.assertTrue(
            any(error.startswith("HARD_FORBIDDEN_SELECTED") for error in errors)
        )

    def test_scene_validation_enforces_object_and_companion_limits(self):
        analysis, pool, constraints, plan = self._validated_rain_fixture()
        plan["selected_elements"]["object_ids"] = ["OBJ_MUG"] * 4
        valid, errors = validate_scene_plan(
            plan,
            analysis,
            pool,
            constraints,
        )
        self.assertFalse(valid)
        self.assertIn("OBJECT_MAX_EXCEEDED", errors)

        friend_analysis = self.make_analysis(
            "친구랑 카페에서 비를 피했는데 즐거웠어"
        )
        friend_pool = build_candidate_pool(friend_analysis)
        friend_constraints = resolve_scene_constraints(
            friend_analysis,
            friend_pool,
            "SAFE",
        )
        friend_plan = deterministic_scene_plan(
            friend_analysis,
            friend_pool,
            friend_constraints,
        )
        companion = friend_plan["selected_elements"]["companion_ids"][0]
        friend_plan["selected_elements"]["companion_ids"] = [
            companion,
            companion,
        ]
        valid, errors = validate_scene_plan(
            friend_plan,
            friend_analysis,
            friend_pool,
            friend_constraints,
        )
        self.assertFalse(valid)
        self.assertIn("COMPANION_RULE_MAX_EXCEEDED", errors)

    def test_scene_validation_rejects_style_driven_scene_selection(self):
        analysis, pool, constraints, plan = self._validated_rain_fixture()
        plan["selected_elements"]["style_id"] = "STYLE_WATERCOLOR"
        valid, errors = validate_scene_plan(
            plan,
            analysis,
            pool,
            constraints,
        )
        self.assertFalse(valid)
        self.assertIn("STYLE_MUST_NOT_SELECT_SCENE_IDS", errors)

    def test_prompt_is_scene_first_and_style_is_rendering_only(self):
        scene = build_scene(
            self.make_analysis("오늘 비와서 우울했어")
        )
        prompt = build_image_prompt(
            scene.scene_spec,
            "STYLE_WATERCOLOR",
        )
        self.assertLess(
            prompt.index("Core scene:"),
            prompt.index("Rendering style:"),
        )
        self.assertIn("rain streaks on glass", prompt)
        self.assertIn("wet pavement", prompt)
        self.assertIn(
            "Apply the selected style only to linework",
            prompt,
        )
        self.assertIn("No readable text", prompt)
        self.assertIn("logos", prompt)
        self.assertIn("watermarks", prompt)
        self.assertIn("clear sunny sky", prompt)
        self.assertIn("dry ground", prompt)
        self.assertIn("broad cheerful smile", prompt)

    def test_anime_style_does_not_force_nature_or_golden_hour_scene(self):
        scene = build_scene(
            self.make_analysis("오늘 비와서 우울했어")
        )
        prompt = build_image_prompt(
            scene.scene_spec,
            "STYLE_ANIME_FILM",
        )
        self.assertNotIn("lush painterly nature backgrounds", prompt)
        self.assertNotIn("verdant green, warm cream", prompt)
        self.assertIn("Do not alter the selected scene content", prompt)

    def test_csv_integrity_validation_passes(self):
        report = validate_data_files()
        self.assertEqual(report["errors"], [])

    def test_multiple_chronological_activities_extracted_as_a_sequence(self):
        result = self.make_analysis(
            "오늘 친구랑 팝업스토어에 가서 최애 아이돌 굿즈도 사고, "
            "카페에가서 커피랑 케이크도 먹고, 공원에서 산책도 했어. "
            "너무 기분이 좋았어"
        ).result
        sequence = result["activity_sequence"]
        self.assertEqual(len(sequence), 3)
        self.assertEqual(
            [item["place_text"] for item in sequence],
            ["팝업스토어", "카페", "공원"],
        )
        self.assertEqual(result["primary_emotion"]["code"], "JOY")

    def test_single_scene_record_has_no_activity_sequence(self):
        result = self.make_analysis("오늘 비와서 우울했어").result
        self.assertEqual(result["activity_sequence"], [])

    def test_multi_activity_scene_compiles_a_split_panel_prompt(self):
        analysis = self.make_analysis(
            "오늘 친구랑 팝업스토어에 가서 최애 아이돌 굿즈도 사고, "
            "카페에가서 커피랑 케이크도 먹고, 공원에서 산책도 했어. "
            "너무 기분이 좋았어"
        )
        scene = build_scene(analysis)
        self.assertEqual(len(scene.scene_spec.get("panels") or []), 3)

        prompt = build_image_prompt(scene.scene_spec, "STYLE_WATERCOLOR")
        self.assertIn("divided into 3 clearly separated", prompt)
        self.assertIn("chronological order", prompt)
        self.assertIn("Panel 1", prompt)
        self.assertIn("Panel 2", prompt)
        self.assertIn("Panel 3", prompt)
        self.assertLessEqual(len(prompt), PROMPT_MAX_CHARS)

    def test_single_scene_prompt_has_no_panel_markers(self):
        scene = build_scene(self.make_analysis("오늘 비와서 우울했어"))
        self.assertEqual(scene.scene_spec.get("panels"), [])
        prompt = build_image_prompt(scene.scene_spec, "STYLE_WATERCOLOR")
        self.assertNotIn("Panel 1", prompt)
        self.assertNotIn("divided into", prompt)


@override_settings(
    EMOTION_CARD_ENABLE_LLM_ANALYSIS=False,
    EMOTION_CARD_SCENE_DIRECTOR_ENABLED=False,
    EMOTION_CARD_ENABLE_REAL_IMAGE_API=False,
    MEDIA_ROOT=tempfile.gettempdir(),
)
class EmotionCardApiTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        call_command("import_emotion_card_data")
        cls.user = User.objects.create_user(
            email="emotion-card@example.com",
            password="password",
            nickname="마음이",
            character="pori",
            onboarding_done=True,
        )

    def setUp(self):
        self.client.force_login(self.user)

    def test_existing_five_step_flow_and_feedback_remain_compatible(self):
        analysis_response = self.client.post(
            "/api/emotion-cards/analyze/",
            {
                "emotion_text": "발표를 마치고 안도하면서도 조금 긴장했어",
                "event_text": "발표를 잘 마침",
                "energy_code": "ENG_STEADY",
                "need_code": "NEED_COMFORT",
            },
            content_type="application/json",
        )
        self.assertEqual(analysis_response.status_code, 201)
        analysis_payload = analysis_response.json()
        self.assertIn("analysis", analysis_payload)
        analysis_id = analysis_payload["analysis_id"]

        scene_response = self.client.post(
            f"/api/emotion-cards/analyses/{analysis_id}/scene/"
        )
        self.assertEqual(scene_response.status_code, 201)
        scene = scene_response.json()
        self.assertIn("scene_preview", scene)
        self.assertTrue(scene["available_styles"])

        generation_response = self.client.post(
            f"/api/emotion-cards/scenes/{scene['scene_id']}/generate/",
            {
                "style_id": scene["available_styles"][0]["style_id"],
                "idempotency_key": "test-card-job",
            },
            content_type="application/json",
        )
        self.assertEqual(generation_response.status_code, 202)
        job = self.client.get(
            f"/api/emotion-cards/jobs/{generation_response.json()['job_id']}/"
        ).json()
        self.assertEqual(job["status"], "COMPLETED")
        self.assertTrue(job["card_id"])

        card = self.client.get(
            f"/api/emotion-cards/{job['card_id']}/"
        ).json()
        self.assertTrue(card["image_url"])
        self.assertIn("final_prompt", card["scene"])
        self.assertEqual(
            card["scene"]["prompt_version"],
            "emotion-card-image-v2.1-timeline",
        )

        feedback = self.client.post(
            f"/api/emotion-cards/{job['card_id']}/feedback/",
            {"helpful": True},
            content_type="application/json",
        )
        self.assertEqual(feedback.status_code, 200)
        self.assertTrue(feedback.json()["feedback"]["helpful"])

    def test_successful_new_card_replaces_the_previous_card_and_image(self):
        def generate_card(idempotency_key):
            analysis = self.client.post(
                "/api/emotion-cards/analyze/",
                {"emotion_text": "오늘의 마음을 카드로 남겨요"},
                content_type="application/json",
            ).json()
            scene = self.client.post(
                f"/api/emotion-cards/analyses/{analysis['analysis_id']}/scene/"
            ).json()
            generation = self.client.post(
                f"/api/emotion-cards/scenes/{scene['scene_id']}/generate/",
                {"style_id": scene["available_styles"][0]["style_id"], "idempotency_key": idempotency_key},
                content_type="application/json",
            ).json()
            return generation

        # The job endpoint exposes the new card ID after synchronous completion.
        first_job = generate_card("replace-first-card")
        first_card_id = self.client.get(f"/api/emotion-cards/jobs/{first_job['job_id']}/").json()["card_id"]
        first_card = self.client.get(f"/api/emotion-cards/{first_card_id}/").json()
        first_image = Path(settings.MEDIA_ROOT) / first_card["image_url"].removeprefix(settings.MEDIA_URL).lstrip("/")
        self.assertTrue(first_image.exists())

        second_job = generate_card("replace-second-card")
        second_card_id = self.client.get(f"/api/emotion-cards/jobs/{second_job['job_id']}/").json()["card_id"]

        self.assertNotEqual(first_card_id, second_card_id)
        self.assertEqual(GeneratedEmotionCard.objects.filter(user=self.user).count(), 1)
        self.assertFalse(first_image.exists())
        self.assertEqual(self.client.get(f"/api/emotion-cards/{first_card_id}/").status_code, 404)

    def test_safety_block_prevents_image_job_creation(self):
        response = self.client.post(
            "/api/emotion-cards/analyze/",
            {"raw_text": "죽고 싶어", "emotion_text": "죽고 싶어"},
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 422)
        self.assertEqual(EmotionCardJob.objects.count(), 0)

    def test_unauthenticated_request_is_rejected(self):
        self.client.logout()
        response = self.client.post(
            "/api/emotion-cards/analyze/",
            {"emotion_text": "오늘은 괜찮아"},
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 401)

    @override_settings(EMOTION_CARD_MAX_DAILY_GENERATIONS=10)
    def test_today_reports_configured_daily_generation_limit(self):
        response = self.client.get("/api/emotion-cards/today/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.json()["daily_generation_count"]["limit"],
            10,
        )

    @override_settings(EMOTION_CARD_MAX_DAILY_GENERATIONS=10)
    def test_today_usage_reset_route_is_not_exposed(self):
        from django.urls import Resolver404, resolve

        with self.assertRaises(Resolver404):
            resolve('/api/emotion-cards/today/reset/')

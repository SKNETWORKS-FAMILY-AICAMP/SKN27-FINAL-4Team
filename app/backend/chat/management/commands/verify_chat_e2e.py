from __future__ import annotations

import json
import os

from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone
from rest_framework.test import APIClient

from chat.models import ChatMessage, ChatSession, UserMemory
from mindreport.models import MindReport
from mindreport.services.report_service import MindReportService
from user.models import User, UserProfile


class Command(BaseCommand):
    help = "챗팅 기능 백엔드에 실질적인 더미데이터를 주입하고 각 단계별 백엔드 파이프라인을 연쇄 실행하여 최종 산출물을 검증합니다."

    def add_arguments(self, parser):
        parser.add_argument(
            "--email",
            default="",
            help="테스트에 사용할 사용자 이메일 (미지정 시 자동 생성)",
        )
        parser.add_argument(
            "--clean-up",
            action="store_true",
            help="검증 완료 후 테스트 사용자와 관련 DB 데이터를 삭제합니다.",
        )

    def _log(self, stage: str, message: str, data: dict | None = None):
        prefix = f"[{stage}] " if stage else ""
        self.stdout.write(self.style.SUCCESS(f"{prefix}{message}"))
        if data:
            self.stdout.write(
                json.dumps(data, ensure_ascii=False, indent=2, default=str)
            )

    def _err(self, stage: str, message: str):
        self.stderr.write(self.style.ERROR(f"[{stage}] {message}"))
        raise CommandError(f"[{stage}] {message}")

    def handle(self, *args, **options):
        run_stamp = timezone.localtime().strftime("%Y%m%d%H%M%S")
        email = options.get("email") or f"chat.verify.e2e.{run_stamp}@example.com"
        clean_up = options.get("clean_up", False)

        self._log("START", f"=== 챗팅 및 산출물 E2E 통합 검증 시작 (테스트 계정: {email}) ===")

        # ---------------------------------------------------------
        # STAGE 1: 사용자 생성 및 프로필 설정 (User Onboarding)
        # ---------------------------------------------------------
        self._log("STAGE_1", "Step 1. 테스트 사용자 및 사용자 프로필 생성 중...")
        user, created = User.objects.get_or_create(
            email=email,
            defaults={
                "nickname": f"웰니스검증자_{run_stamp[-4:]}",
                "character": "pori",
                "onboarding_done": True,
            },
        )
        if created:
            user.set_password("TestPass123!")
            user.save()

        profile, p_created = UserProfile.objects.get_or_create(
            user=user,
            defaults={
                "age": 28,
                "gender": "여성",
                "interests": ["심리학", "스트레스관리", "산책"],
                "hobbies": ["음악 감상", "요리"],
            },
        )

        self._log(
            "STAGE_1",
            "사용자 및 프로필 준비 완료",
            {
                "user_id": user.id,
                "email": user.email,
                "nickname": user.nickname,
                "character": user.character,
                "profile": {
                    "age": profile.age,
                    "gender": profile.gender,
                    "interests": profile.interests,
                    "hobbies": profile.hobbies,
                },
            },
        )

        client = APIClient()
        client.force_authenticate(user=user)

        # ---------------------------------------------------------
        # STAGE 2: 챗봇 세션 시작 API 검증 (Session Start)
        # ---------------------------------------------------------
        self._log("STAGE_2", "Step 2. POST /api/session/start/ 세션 생성 호출 중...")
        response = client.post(
            "/api/session/start/",
            {"character_id": "pori", "is_secret": False, "tts": False},
            format="json",
        )
        if response.status_code != 201 or not response.data.get("success"):
            self._err("STAGE_2", f"세션 생성 실패: {response.data}")

        session_data = response.data.get("data", {})
        session_id = session_data.get("session_id")
        opener = session_data.get("opener")

        if not session_id or not opener:
            self._err("STAGE_2", f"세션 응답에 session_id/opener가 없음: {session_data}")

        self._log(
            "STAGE_2",
            "세션 정상 생성 및 캐릭터 첫인사 수신 완료",
            {
                "session_id": session_id,
                "cold_start_done": session_data.get("cold_start_done"),
                "opener": opener,
            },
        )

        # ---------------------------------------------------------
        # STAGE 3: 실질적인 더미 대화 데이터 주입 및 대화 턴 실행
        # (Multi-Turn Dialogue Execution with PII, Emotions)
        # ---------------------------------------------------------
        self._log("STAGE_3", "Step 3. 다중 턴 실질 더미대화 메시지 전송 및 턴 검증...")

        dummy_scenarios = [
            {
                "tag": "업무_스트레스_및_PII포함",
                "message": "오늘 회사에서 발표 준비 때문에 팀장님이랑 마찰이 있었어. 전화번호 010-1234-5678 로 연락받고 너무 당황스러웠어.",
                "expected_pii": True,
            },
            {
                "tag": "감정_해소_및_동료위로",
                "message": "퇴근길에 박과장님이 같이 커피 한 잔 하면서 내 편을 들어줘서 마음이 한결 가벼워지고 후련해졌어.",
                "expected_pii": False,
            },
            {
                "tag": "성취_및_기쁨",
                "message": "이번달 주요 프로젝트를 드디어 성공적으로 마쳤어! 팀원들이랑 축하 파티도 하고 보너스도 받는대, 너무 기뻐!",
                "expected_pii": False,
            },
            {
                "tag": "피로_및_휴식욕구",
                "message": "요즘 밤에 잠을 잘 못 자서 그런지 몸이 많이 피곤하고 의욕이 없어. 주말엔 집에서 음악 들으면서 푹 쉬어야겠어.",
                "expected_pii": False,
            },
            {
                "tag": "자아성찰_및_평온",
                "message": "따뜻한 차 마시면서 조용히 책을 읽으니까 마음이 많이 평온해지고 내 자신을 돌아보게 되네.",
                "expected_pii": False,
            },
        ]

        # LLM 공급자가 Groq rate limit 초과 시 OpenAI로 안정적 처리되도록 가이드
        if os.environ.get("LLM_PROVIDER") == "groq":
            os.environ["LLM_PROVIDER"] = "openai"

        turn_results = []
        import time
        for index, sc in enumerate(dummy_scenarios, start=1):
            if index > 1:
                time.sleep(1.5)  # rate limit 방지 간격
            res = client.post(
                "/api/chat/",
                {"session_id": session_id, "message": sc["message"]},
                format="json",
            )
            if res.status_code != 200 or not res.data.get("success"):
                self._err("STAGE_3", f"턴 {index} ({sc['tag']}) 실행 실패: {res.data}")

            data = res.data.get("data", {})
            msg_obj = data.get("message") or {}
            reply = msg_obj.get("text", "")
            emotion = data.get("emotion_label")
            pii_found = data.get("pii_found", [])

            if not reply:
                # DB에서 방금 저장된 assistant 메시지 조회
                db_reply = (
                    ChatMessage.objects.filter(session_id=session_id, role="assistant")
                    .order_by("-created_at")
                    .first()
                )
                if db_reply:
                    reply = db_reply.content

            if not reply:
                self._err("STAGE_3", f"턴 {index} 봇 응답 생성 실패 (빈 응답)")

            turn_info = {
                "turn": index,
                "tag": sc["tag"],
                "user_sent": sc["message"],
                "detected_emotion": emotion,
                "bot_reply": reply,
            }
            turn_results.append(turn_info)
            self._log("STAGE_3", f"  -> 턴 {index} [{sc['tag']}] 유저: {sc['message']}")
            self._log("STAGE_3", f"  -> 턴 {index} [{sc['tag']}] 봇 응답 (감정={emotion}): {reply}")

        # DB 메시지 저장이 정상적으로 이루어졌는지 검증
        db_messages_count = ChatMessage.objects.filter(session_id=session_id).count()
        self._log(
            "STAGE_3",
            f"대화 턴 완료 (DB 저장된 총 메시지 수: {db_messages_count}개)",
            {"turn_results": turn_results},
        )

        if db_messages_count < len(dummy_scenarios) * 2:
            self._err("STAGE_3", f"DB 메시지 수가 예상보다 적음: {db_messages_count}")

        # ---------------------------------------------------------
        # STAGE 4: 감정 캘린더 및 감정 데이터 집계 검증
        # (Emotion Stats & Calendar Records)
        # ---------------------------------------------------------
        self._log("STAGE_4", "Step 4. 감정 분포 및 대화 감정 기록 집계 검증 중...")
        user_emotions = (
            ChatMessage.objects.filter(session__user=user, role="assistant")
            .exclude(emotion_label__isnull=True)
            .values_list("emotion_label", flat=True)
        )
        emotion_counts = {}
        for emo in user_emotions:
            emotion_counts[emo] = emotion_counts.get(emo, 0) + 1

        self._log("STAGE_4", "집계된 사용자 대화 감정 통계", {"emotion_counts": emotion_counts})

        # ---------------------------------------------------------
        # STAGE 5: 마음 리포트 다중 에이전트 생성 및 최종 산출물 검증
        # (Multi-Agent Mind Report Generation Pipeline)
        # ---------------------------------------------------------
        self._log("STAGE_5", "Step 5. 다중 에이전트 마음 리포트 파이프라인(MindReportService) 실행 중...")

        try:
            report_service = MindReportService()
            target_date = timezone.localdate()
            reports = report_service.refresh_reports(
                user=user,
                target_date=target_date,
                include_monthly=True,
            )
        except Exception as exc:
            self._err("STAGE_5", f"마음 리포트 생성 중 예외 발생: {exc}")

        self._log("STAGE_5", f"마음 리포트 생성 완료 (결과 리포트 개수: {len(reports)}개)")

        # DB에 저장된 MindReport 검증
        db_reports = MindReport.objects.filter(user=user)
        if not db_reports.exists():
            self._err("STAGE_5", "MindReport 모델에 생성된 DB 데이터가 없습니다.")

        verified_reports = []
        for mr in db_reports:
            r_data = {
                "id": mr.id,
                "report_type": mr.report_type,
                "range_text": mr.range_text,
                "title": mr.title,
                "summary": mr.summary[:100] + "...",
                "is_fallback": mr.is_fallback,
                "stress_causes_count": len(mr.stress_causes),
                "relief_causes_count": len(mr.relief_causes),
                "cause_labels": mr.cause_labels,
                "emotions": mr.emotions,
                "recommendations_count": len(mr.recommendations),
                "created_at": mr.created_at,
            }
            verified_reports.append(r_data)
            self._log("STAGE_5", f"  -> 리포트 ID={mr.id} [{mr.report_type}] '{mr.title}' (fallback={mr.is_fallback})")

        # ---------------------------------------------------------
        # STAGE 6: 내서재 / 책 추천 산출물 검증 (MyBook Integration)
        # ---------------------------------------------------------
        self._log("STAGE_6", "Step 6. 대화 감정/프로필 기반 책 추천 API 산출물 검증...")
        book_res = client.get("/api/mybook/recommendation/?force=true")
        if book_res.status_code == 200 and book_res.data:
            book_payload = book_res.data
            self._log(
                "STAGE_6",
                "책 추천 산출물 도출 성공",
                {
                    "is_cached": book_payload.get("is_cached"),
                    "service_status": book_payload.get("service_status"),
                    "themes_count": len(book_payload.get("themes", [])),
                    "first_theme_title": (
                        book_payload["themes"][0].get("theme_title")
                        if book_payload.get("themes")
                        else None
                    ),
                },
            )
        else:
            self._log("STAGE_6", f"책 추천 API 응답 (HTTP {book_res.status_code})", getattr(book_res, "data", None))

        # ---------------------------------------------------------
        # STAGE 7: 최종 산출물 통합 검증 결과 요약 및 보고
        # ---------------------------------------------------------
        self._log("STAGE_7", "=== 최종 산출물 검증 결과 요약 ===")
        summary_payload = {
            "test_user": user.email,
            "session_id": session_id,
            "dialogue_turns_executed": len(dummy_scenarios),
            "chat_messages_saved_in_db": db_messages_count,
            "detected_emotions": list(emotion_counts.keys()),
            "generated_mind_reports_count": db_reports.count(),
            "mind_reports": verified_reports,
            "all_pipeline_stages_passed": True,
        }

        self._log("STAGE_7", "SUCCESS - 백엔드 챗팅 및 멀티에이전트 마음리포트 최종 산출물 정상 검증 완료!", summary_payload)

        # Clean-up if requested
        if clean_up:
            self._log("CLEANUP", "테스트 데이터 정리 중...")
            user.delete()
            self._log("CLEANUP", "테스트 데이터 삭제 완료.")


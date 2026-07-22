from __future__ import annotations

import json
import os
from datetime import datetime

from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone
from rest_framework.test import APIClient

from chat.models import ChatSession, MbtiAnswer
from mbti.constants import MBTI_AXES, MBTI_AXIS_QUESTION_DATA
from mbti.models import (
    MbtiMonthlyAnalysisJob,
    MbtiMonthlyAxisResult,
    MbtiMonthlyReport,
    MbtiMonthlyResultRecord,
    MbtiQuestionResponse,
    MbtiResponseScore,
)
from mbti.services.job_service import process_next_job
from mbti.services.qna_service import current_period_key
from user.models import User


AXIS_ANSWERS = {
    "IE": (
        "최근에는 약속이 없는 날 혼자 책을 읽고 산책할 때 가장 충전됐어. 여러 사람을 만나고 나면 혼자 조용히 쉬어야 기운이 돌아와.",
        "낯선 모임에서는 먼저 나서기보다 분위기를 살피고, 한두 명과 깊게 이야기하는 편이 훨씬 편해.",
        "힘든 일이 있으면 바로 연락하기보다 혼자 생각을 정리한 다음 정말 가까운 사람에게만 이야기해.",
        "사람들과 오래 어울린 다음에는 즐거워도 에너지가 빠져서 집에서 혼자 쉬는 시간이 꼭 필요해.",
        "아무 방해 없는 하루가 생기면 혼자 음악을 듣고 글을 읽으며 천천히 보내고 싶어.",
    ),
    "SN": (
        "새 소식을 들으면 사실 자체보다 앞으로 어떤 가능성이 열릴지와 숨은 의미를 먼저 상상하는 편이야.",
        "세부 장면보다는 그 경험이 내게 어떤 의미였는지와 전체적인 분위기가 더 오래 기억나.",
        "새로운 일을 배울 때 세부 순서부터 외우기보다 큰 그림과 원리를 먼저 이해해야 흥미가 생겨.",
        "현실적인 제약을 바로 따지기보다 여러 아이디어를 자유롭게 연결하며 새로운 방법을 떠올리는 걸 좋아해.",
        "익숙한 방식만 반복하기보다 아직 해보지 않은 가능성을 상상하고 실험하는 쪽이 더 설레.",
    ),
    "TF": (
        "친구가 고민을 말하면 해결책을 제시하기 전에 그 사람이 어떤 마음이었을지 충분히 듣고 공감하려고 해.",
        "결정할 때 논리만 맞는지보다 그 선택이 주변 사람들에게 어떤 감정을 남길지를 중요하게 생각해.",
        "누군가 실수했을 때 바로 지적하기보다 상처받지 않게 상황과 말투를 살펴서 이야기하는 편이야.",
        "성과를 인정받는 것도 좋지만 내 마음과 노력을 알아줬다는 말을 들을 때 더 크게 힘이 나.",
        "토론에서 결론을 이기는 것보다 서로 존중받았다고 느끼며 관계를 지키는 게 더 중요해.",
    ),
    "JP": (
        "계획을 촘촘히 고정하기보다 그날의 상황과 기분에 맞춰 선택할 수 있도록 여지를 두는 편이야.",
        "갑자기 계획이 바뀌어도 스트레스받기보다 새로 생긴 선택지를 재미있게 받아들이는 경우가 많아.",
        "여행 준비는 꼭 필요한 것만 생각해 두고, 세부 일정은 현지에서 끌리는 대로 정하는 게 좋아.",
        "할 일 목록을 엄격히 지키기보다 우선순위를 보면서 그때 가장 필요한 일을 유연하게 처리해.",
        "마감이 가까워질수록 집중력이 올라오는 편이라 초반에는 여러 가능성을 열어 두고 천천히 시작해.",
    ),
}


class Command(BaseCommand):
    help = "실제 PostgreSQL과 LLM을 사용해 채팅 질문부터 월간 MBTI 리포트까지 검증합니다."

    def add_arguments(self, parser):
        parser.add_argument("--email")
        parser.add_argument("--period-key")
        parser.add_argument("--chat-max-turns", type=int, default=9)

    def _emit(self, stage: str, payload) -> None:
        self.stdout.write(
            json.dumps({"stage": stage, "payload": payload}, ensure_ascii=False, default=str)
        )

    @staticmethod
    def _payload(response):
        return getattr(response, "data", None)

    def _require_status(self, response, allowed: set[int], stage: str):
        if response.status_code not in allowed:
            raise CommandError(
                f"{stage} failed: HTTP {response.status_code} {self._payload(response)!r}"
            )
        return self._payload(response)

    def handle(self, *args, **options):
        due_job = (
            MbtiMonthlyAnalysisJob.objects
            .filter(status="pending", scheduled_at__lte=timezone.now())
            .order_by("scheduled_at", "id")
            .first()
        )
        if due_job is not None:
            raise CommandError(
                "다른 사용자의 대기 작업이 있어 검증 명령을 중단합니다: "
                f"job_id={due_job.id}, user_id={due_job.user_id}"
            )

        run_stamp = timezone.localtime().strftime("%Y%m%d%H%M%S")
        email = options.get("email") or f"codex.mbti.e2e.{run_stamp}@example.com"
        period_key = options.get("period_key") or current_period_key()
        if period_key != current_period_key():
            raise CommandError(
                "Q&A API는 현재 월로 저장되므로 --period-key는 현재 월만 사용할 수 있습니다."
            )

        user = User.objects.create_user(
            email=email,
            password="CodexMbtiE2E!",
            nickname=f"MBTI검증{run_stamp[-6:]}",
            onboarding_done=True,
        )
        client = APIClient()
        client.force_authenticate(user=user)
        self._emit("user_created", {"user_id": user.id, "email": user.email})

        onboarding = self._require_status(
            client.post(
                "/api/mbti/onboarding/",
                {"mbti_type": "INFP"},
                format="json",
            ),
            {200},
            "onboarding",
        )
        self._emit("onboarding_saved", onboarding)

        original_gap = os.environ.get("MBTI_MIN_GAP")
        os.environ["MBTI_MIN_GAP"] = "3"
        try:
            started = self._require_status(
                client.post(
                    "/api/session/start/",
                    {"character_id": "pori", "is_secret": False, "tts": False},
                    format="json",
                ),
                {201},
                "session_start",
            )
            session_id = started["data"]["session_id"]
            self._emit(
                "chat_session_started",
                {"session_id": session_id, "opener": started["data"]["opener"]},
            )

            probe_text = None
            chat_messages = (
                "오늘은 아침에 산책하고 커피를 마셔서 기분이 꽤 좋아.",
                "점심에는 읽고 싶던 책을 조금 읽었는데 마음이 편안해졌어.",
                "저녁에는 집에서 음악을 들으면서 쉬려고 해. 이런 여유가 참 좋아.",
                "요즘 작은 일상을 천천히 즐기는 재미를 알아가는 중이야.",
                "오늘 좋았던 일을 기록해 두니 다시 봐도 기분이 좋아지더라.",
                "주말에도 무리하지 않고 내가 좋아하는 일을 하며 보내고 싶어.",
                "친구와 맛있는 걸 먹고 즐겁게 이야기했어.",
                "집에 돌아와서는 조용히 쉬니까 더 편안해졌어.",
                "내일도 가벼운 산책으로 하루를 시작해 보려고 해.",
            )
            for turn_no, message in enumerate(
                chat_messages[: max(3, options["chat_max_turns"])], start=1
            ):
                turn = self._require_status(
                    client.post(
                        "/api/chat/",
                        {"session_id": session_id, "message": message, "tts": False},
                        format="json",
                    ),
                    {200},
                    f"chat_turn_{turn_no}",
                )
                data = turn["data"]
                self._emit(
                    "chat_turn",
                    {
                        "turn": turn_no,
                        "emotion_label": data.get("emotion_label"),
                        "assistant": data.get("message", {}).get("text"),
                        "mbti_probe": data.get("mbti_probe"),
                    },
                )
                if data.get("mbti_probe"):
                    probe_text = data["mbti_probe"]["text"]
                    break

            if not probe_text:
                raise CommandError("자연 대화 턴에서 MBTI 질문이 생성되지 않았습니다.")

            session = ChatSession.objects.get(id=session_id)
            question_code = session.mbti_last_question_code
            axis = question_code[:2]
            answer_text = AXIS_ANSWERS[axis][0]
            answer_turn = self._require_status(
                client.post(
                    "/api/chat/",
                    {"session_id": session_id, "message": answer_text, "tts": False},
                    format="json",
                ),
                {200},
                "chat_mbti_answer",
            )
            chat_answer = MbtiAnswer.objects.filter(
                user=user, question_code=question_code
            ).order_by("-id").first()
            pipeline_answer = MbtiQuestionResponse.objects.filter(
                user_id=user.id,
                conversation_id=session_id,
                target_axis=axis,
            ).order_by("-id").first()
            if chat_answer is None or pipeline_answer is None:
                raise CommandError("채팅 MBTI 답변의 이중 DB 저장이 확인되지 않았습니다.")
            if pipeline_answer.question_text != probe_text:
                raise CommandError(
                    "DB에 저장된 질문이 실제 표시 질문과 다릅니다: "
                    f"displayed={probe_text!r}, stored={pipeline_answer.question_text!r}"
                )
            if pipeline_answer.answer_text != answer_text:
                raise CommandError("DB에 저장된 답변이 실제 입력 답변과 다릅니다.")
            self._emit(
                "chat_mbti_answer_saved",
                {
                    "question_code": question_code,
                    "axis": axis,
                    "displayed_question": probe_text,
                    "chat_mbti_answer_id": chat_answer.id,
                    "pipeline_response_id": pipeline_answer.id,
                    "answer_ack": answer_turn["data"]["message"]["text"],
                },
            )
        finally:
            if original_gap is None:
                os.environ.pop("MBTI_MIN_GAP", None)
            else:
                os.environ["MBTI_MIN_GAP"] = original_gap

        bank_by_axis = {
            axis: [(qid, text) for qid, row_axis, text in MBTI_AXIS_QUESTION_DATA if row_axis == axis]
            for axis in MBTI_AXES
        }
        generated_questions = {}
        for axis in MBTI_AXES:
            question_data = self._require_status(
                client.get(f"/api/mbti/mock-qna/question/?axis={axis}"),
                {200},
                f"question_{axis}",
            )
            generated = question_data["question"]
            if not generated["text"].rstrip().endswith("?"):
                raise CommandError(f"{axis} 생성 질문이 물음표로 끝나지 않습니다.")
            generated_questions[axis] = generated
            current_count = question_data["axis_counts"][axis]
            needed = 5 - current_count
            questions = [(None, generated["text"])] + bank_by_axis[axis]
            for offset in range(needed):
                _, question_text = questions[offset]
                answer_text = AXIS_ANSWERS[axis][offset % len(AXIS_ANSWERS[axis])]
                saved = self._require_status(
                    client.post(
                        "/api/mbti/mock-qna/answer/",
                        {
                            "target_axis": axis,
                            "question_text": question_text,
                            "answer_text": answer_text,
                        },
                        format="json",
                    ),
                    {200},
                    f"answer_{axis}_{offset + 1}",
                )
                current_count = saved["axis_counts"][axis]
            if current_count != 5:
                raise CommandError(f"{axis} 응답 수가 5개가 아닙니다: {current_count}")

        counts = {
            axis: MbtiQuestionResponse.objects.filter(
                user_id=user.id, period_key=period_key, target_axis=axis
            ).count()
            for axis in MBTI_AXES
        }
        self._emit(
            "qna_collection_complete",
            {"axis_counts": counts, "generated_questions": generated_questions},
        )

        enqueue = self._require_status(
            client.post(
                "/api/mbti/monthly-analysis/",
                {"period_key": period_key},
                format="json",
            ),
            {200, 202},
            "enqueue_monthly_analysis",
        )
        self._emit("analysis_enqueued", enqueue)

        job_id = enqueue["analysis_job"]["id"]
        processed = process_next_job(max_retries=0, retry_delay_seconds=1)
        if processed is None or processed.id != job_id:
            raise CommandError(
                f"방금 생성한 작업이 처리되지 않았습니다: expected={job_id}, "
                f"processed={getattr(processed, 'id', None)}"
            )
        processed.refresh_from_db()
        self._emit(
            "analysis_processed",
            {
                "job_id": processed.id,
                "status": processed.status,
                "retry_count": processed.retry_count,
                "error_message": processed.error_message,
            },
        )
        if processed.status != "completed":
            raise CommandError(
                f"월간 분석 작업이 완료되지 않았습니다: {processed.status} "
                f"{processed.error_message or ''}"
            )

        dashboard = self._require_status(
            client.get(f"/api/mbti/monthly-demo/?period_key={period_key}"),
            {200},
            "monthly_dashboard",
        )
        monthly = MbtiMonthlyResultRecord.objects.get(
            user_id=user.id, period_key=period_key
        )
        axis_rows = list(
            MbtiMonthlyAxisResult.objects.filter(monthly_result=monthly)
            .order_by("axis")
            .values(
                "axis",
                "qna_count",
                "scored_count",
                "axis_avg",
                "axis_ratios_json",
                "selected_letter",
                "data_status",
            )
        )
        report = MbtiMonthlyReport.objects.get(monthly_result=monthly)
        score_rows = list(
            MbtiResponseScore.objects.filter(user_id=user.id, period_key=period_key)
            .order_by("axis", "question_response_id")
            .values(
                "question_response_id",
                "axis",
                "score",
                "direction",
                "coding_status",
                "reason",
                "model",
            )
        )
        self._emit(
            "final_result",
            {
                "run_at": datetime.now().astimezone().isoformat(),
                "user_id": user.id,
                "email": user.email,
                "period_key": period_key,
                "job": {
                    "id": processed.id,
                    "status": processed.status,
                    "scoring_model": processed.scoring_model,
                },
                "monthly_result": {
                    "id": monthly.id,
                    "status": monthly.status,
                    "estimated_mbti_type": monthly.estimated_mbti_type,
                    "previous_estimated_mbti_type": monthly.previous_estimated_mbti_type,
                    "changed_axes": monthly.changed_axes_json,
                },
                "axis_results": axis_rows,
                "response_scores": score_rows,
                "report": {
                    "id": report.id,
                    "sections": report.report_sections_json,
                    "evidence_items": report.evidence_items_json,
                },
                "dashboard": dashboard,
            },
        )

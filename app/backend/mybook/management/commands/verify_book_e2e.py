from __future__ import annotations

import json

from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone
from rest_framework.test import APIClient

from chat.models import ChatMessage, ChatSession
from mybook.constants import SUPPORTED_THEME_IDS
from mybook.models import DailyBookRecommendation
from mybook.services.profile_service import build_user_profile
from mybook.services.recommendation_service import payload_has_real_books
from user.models import User, UserProfile


class Command(BaseCommand):
    help = "실제 PostgreSQL·Kakao 도서 검색·OpenAI를 사용해 책 추천 전체 흐름을 검증합니다."

    def add_arguments(self, parser):
        parser.add_argument("--email")

    def _emit(self, stage: str, payload) -> None:
        self.stdout.write(
            json.dumps(
                {"stage": stage, "payload": payload},
                ensure_ascii=False,
                default=str,
            )
        )

    @staticmethod
    def _response_payload(response):
        return getattr(response, "data", None)

    def _require_status(self, response, allowed: set[int], stage: str):
        payload = self._response_payload(response)
        if response.status_code not in allowed:
            raise CommandError(
                f"{stage} failed: HTTP {response.status_code} {payload!r}"
            )
        return payload

    def handle(self, *args, **options):
        run_stamp = timezone.localtime().strftime("%Y%m%d%H%M%S")
        email = options.get("email") or f"codex.book.e2e.{run_stamp}@example.com"
        if User.objects.filter(email=email).exists():
            raise CommandError(f"이미 존재하는 테스트 이메일입니다: {email}")

        user = User.objects.create_user(
            email=email,
            password="CodexBookE2E!",
            nickname=f"책추천검증{run_stamp[-6:]}",
            character="pori",
            onboarding_done=True,
        )
        UserProfile.objects.create(
            user=user,
            age=29,
            gender="여성",
            interests=["심리학", "천문학"],
            hobbies=["사진 찍기", "요리"],
        )
        session = ChatSession.objects.create(
            user=user,
            character="pori",
            is_secret=False,
            cold_start_done=True,
        )
        for index, emotion in enumerate(("joy", "normal", "joy"), start=1):
            ChatMessage.objects.create(
                session=session,
                role="assistant",
                content=f"책 추천 감정 검증 메시지 {index}",
                emotion_label=emotion,
            )
        self._emit(
            "dummy_data_created",
            {
                "user_id": user.id,
                "email": user.email,
                "profile": {
                    "age": 29,
                    "gender": "여성",
                    "interests": ["심리학", "천문학"],
                    "hobbies": ["사진 찍기", "요리"],
                },
                "assistant_emotions": ["joy", "normal", "joy"],
            },
        )

        profile = build_user_profile(user)
        expected_profile = {
            "age": 29,
            "gender": "여성",
            "interests": ["심리학", "천문학"],
            "hobbies": ["사진 찍기", "요리"],
            "today_emotion": "기쁨",
        }
        if profile != expected_profile:
            raise CommandError(
                f"추천 입력 프로필이 예상과 다릅니다: {profile!r}"
            )
        self._emit("profile_built", profile)

        client = APIClient()
        client.force_authenticate(user=user)
        generated = self._require_status(
            client.get("/api/mybook/recommendation/?force=true"),
            {200},
            "generate_recommendation",
        )
        if not payload_has_real_books(generated):
            raise CommandError("추천 응답이 완전한 실제 도서 payload가 아닙니다.")
        if generated.get("is_cached") or generated.get("is_stale"):
            raise CommandError("최초 생성 응답이 캐시 또는 stale 상태로 표시됐습니다.")
        if (generated.get("service_status") or {}).get("state") != "healthy":
            raise CommandError("최초 생성 응답의 서비스 상태가 healthy가 아닙니다.")

        themes = generated.get("themes") or []
        books = generated.get("books") or []
        theme_ids = [theme.get("id") for theme in themes]
        book_theme_ids = [book.get("theme_id") for book in books]
        if theme_ids != list(SUPPORTED_THEME_IDS):
            raise CommandError(f"테마 순서 또는 구성이 잘못됐습니다: {theme_ids!r}")
        if book_theme_ids != list(SUPPORTED_THEME_IDS):
            raise CommandError(f"테마별 추천 도서가 완전하지 않습니다: {book_theme_ids!r}")

        for book in books:
            required_text = {
                "title": book.get("title"),
                "author": book.get("author"),
                "isbn": book.get("isbn"),
                "review": (book.get("ai_curation") or {}).get("review"),
            }
            missing = [key for key, value in required_text.items() if not str(value or "").strip()]
            if missing:
                raise CommandError(
                    f"{book.get('theme_id')} 도서 필수값 누락: {missing!r}"
                )
            provider_id = ((book.get("source_provider") or {}).get("id"))
            if provider_id != "kakao_daum_book_search":
                raise CommandError(
                    f"예상하지 못한 도서 제공처입니다: {provider_id!r}"
                )

        record = DailyBookRecommendation.objects.get(
            user=user,
            recommendation_date=timezone.localdate(),
        )
        if record.profile_basis != {
            "today_emotion": "기쁨",
            "interests": ["심리학", "천문학"],
            "hobbies": ["사진 찍기", "요리"],
        }:
            raise CommandError(
                f"DB profile_basis가 입력 프로필과 다릅니다: {record.profile_basis!r}"
            )
        if not payload_has_real_books(record.payload):
            raise CommandError("DB에 저장된 추천 payload가 유효하지 않습니다.")
        self._emit(
            "recommendation_generated_and_saved",
            {
                "record_id": record.id,
                "recommendation_date": record.recommendation_date,
                "engine": generated.get("recommendation_engine"),
                "themes": themes,
                "books": books,
                "service_status": generated.get("service_status"),
                "source_disclosure": generated.get("source_disclosure"),
            },
        )

        cached = self._require_status(
            client.get("/api/mybook/recommendation/"),
            {200},
            "load_cached_recommendation",
        )
        if not cached.get("is_cached") or cached.get("is_stale"):
            raise CommandError("동일 날짜 재조회가 정상 캐시 응답이 아닙니다.")
        generated_identity = [
            (book.get("theme_id"), book.get("isbn"), book.get("title"))
            for book in books
        ]
        cached_identity = [
            (book.get("theme_id"), book.get("isbn"), book.get("title"))
            for book in (cached.get("books") or [])
        ]
        if generated_identity != cached_identity:
            raise CommandError("생성 응답과 캐시 응답의 도서 목록이 다릅니다.")

        self._emit(
            "cache_verified",
            {
                "is_cached": cached.get("is_cached"),
                "is_stale": cached.get("is_stale"),
                "content_date": cached.get("content_date"),
                "record_count": DailyBookRecommendation.objects.filter(user=user).count(),
                "books": cached_identity,
            },
        )


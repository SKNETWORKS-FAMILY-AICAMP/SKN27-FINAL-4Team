import json
import hashlib
import html
import math
import os
import re
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from urllib.parse import urlencode, urlparse

import requests
from django.core.cache import cache
from django.utils import timezone
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate


NLK_BOOK_API_URL = os.environ.get(
    "NLK_BOOK_API_URL",
    "https://apis.data.go.kr/1371029/BookInformationService_v2/getbookList_v2",
)
NLK_BOOK_TIMEOUT_SECONDS = float(os.environ.get("NLK_BOOK_TIMEOUT_SECONDS", "5"))
NLK_BOOK_RETRY_COUNT = max(0, int(os.environ.get("NLK_BOOK_RETRY_COUNT", "1")))
NLK_BOOK_PAGE_SIZE = min(20, max(1, int(os.environ.get("NLK_BOOK_PAGE_SIZE", "20"))))
NLK_BOOK_QUERY_LIMIT = min(
    6,
    max(2, int(os.environ.get("NLK_BOOK_QUERY_LIMIT", "4"))),
)
NLK_BOOK_MAX_PROBE_PAGES = min(
    2,
    max(0, int(os.environ.get("NLK_BOOK_MAX_PROBE_PAGES", "1"))),
)
KAKAO_BOOK_API_URL = os.environ.get(
    "KAKAO_BOOK_API_URL",
    "https://dapi.kakao.com/v3/search/book",
)
KAKAO_BOOK_TIMEOUT_SECONDS = float(os.environ.get("KAKAO_BOOK_TIMEOUT_SECONDS", "5"))
KAKAO_BOOK_RETRY_COUNT = max(0, int(os.environ.get("KAKAO_BOOK_RETRY_COUNT", "1")))
KAKAO_BOOK_PAGE_SIZE = min(50, max(10, int(os.environ.get("KAKAO_BOOK_PAGE_SIZE", "20"))))
KAKAO_BOOK_QUERY_LIMIT = min(5, max(2, int(os.environ.get("KAKAO_BOOK_QUERY_LIMIT", "4"))))
RECOMMENDATION_ENGINE_VERSION = "kakao_books_v1"
BOOK_COVER_TIMEOUT_SECONDS = float(os.environ.get("BOOK_COVER_TIMEOUT_SECONDS", "3"))
BOOK_COVER_CACHE_SECONDS = max(
    3600,
    int(os.environ.get("BOOK_COVER_CACHE_SECONDS", str(60 * 60 * 24 * 7))),
)
MAX_BOOK_AGE_YEARS = 10
BASIS_TOKEN_ALIASES = {
    "사진": ("카메라", "촬영", "사진술", "포토"),
    "찍기": ("카메라", "촬영"),
    "산책": ("걷기", "보행", "트레킹"),
    "음악": ("작곡", "연주", "음향", "뮤지션", "음악사"),
    "심리": ("인지", "정서", "심리학"),
    "요리": ("레시피", "조리", "식재료"),
    "운동": ("체력", "트레이닝", "피트니스"),
    "독서": ("읽기", "문학", "서평"),
    "영화": ("시네마", "영화사", "감독"),
    "드라마": ("극본", "연출", "텔레비전"),
    "그림": ("드로잉", "회화", "미술"),
    "필사": ("쓰기", "문장", "손글씨"),
    "요가": ("명상", "호흡", "스트레칭"),
    "패션": ("스타일", "복식", "의류", "디자인"),
    "팝업스토어": ("팝업", "브랜드", "전시", "공간"),
    "맛집": ("미식", "식문화", "음식", "외식"),
    "탐방": ("여행", "답사", "기행"),
}
NLK_PROVIDER_INFO = {
    "id": "nlk_national_bibliography_lod",
    "label": "국립중앙도서관 국가서지 LOD",
    "short_label": "국가서지 LOD",
    "portal_url": "https://www.data.go.kr/data/15154402/openapi.do",
    "detail_url": "https://www.nl.go.kr/NL/contents/N11000000000.do",
    "license": "공공누리 제1유형 · CC0 1.0",
    "attribution": "출처: 문화체육관광부 국립중앙도서관 국가서지 LOD",
}
KAKAO_BOOK_PROVIDER_INFO = {
    "id": "kakao_daum_book_search",
    "label": "Kakao Daum 책 검색",
    "short_label": "Kakao 도서정보",
    "detail_url": "https://developers.kakao.com/docs/latest/ko/daum-search/dev-guide#search-book",
    "attribution": "책 상세·표지: Kakao Daum 책 검색",
}
OPEN_LIBRARY_COVER_PROVIDER_INFO = {
    "id": "open_library_covers",
    "label": "Open Library Covers",
    "short_label": "Open Library 표지",
    "detail_url": "https://openlibrary.org/dev/docs/api/covers",
    "attribution": "표지: Open Library Covers",
}


FALLBACK_KEYWORDS = {
    "emotion": ("마음 위로 소설", "오늘 감정이 좋다면 유지하고, 무겁다면 덜어내는 독서 방향입니다."),
    "interests": ("교양 입문", "프로필 관심사 자체를 더 깊이 읽을 수 있는 방향입니다."),
    "hobbies": ("취미 실용", "프로필 취미를 실제로 즐기고 넓히는 방향입니다."),
}


THEME_DEFINITIONS = [
    {
        "id": "emotion",
        "name": "오늘의 감정 추천",
        "basis_key": "today_emotion",
        "basis_label": "오늘의 주된 감정",
    },
    {
        "id": "interests",
        "name": "관심사 기반 추천",
        "basis_key": "interests",
        "basis_label": "프로필 관심사",
    },
    {
        "id": "hobbies",
        "name": "취미 기반 추천",
        "basis_key": "hobbies",
        "basis_label": "프로필 취미",
    },
]


class BookRecommendationUnavailable(RuntimeError):
    """Raised when a trustworthy general-book recommendation cannot be built."""

    def __init__(self, message, *, code="BOOK_RECOMMENDATION_UNAVAILABLE"):
        super().__init__(message)
        self.code = code


class BookRecommendationAgent:
    @staticmethod
    def recommend(user_profile, force_theme=None, cached_data=None, excluded_isbns=None):
        cached_books = {}
        cached_themes = {}
        if isinstance(cached_data, dict):
            for book in cached_data.get("books", []):
                if isinstance(book, dict) and "theme_id" in book:
                    cached_books[book["theme_id"]] = book
            for th in cached_data.get("themes", []):
                if isinstance(th, dict) and "id" in th:
                    cached_themes[th["id"]] = th

        themes = BookRecommendationAgent._build_themes(user_profile)
        excluded_by_theme = excluded_isbns if isinstance(excluded_isbns, dict) else {}
        for theme in themes:
            theme["excluded_isbns"] = excluded_by_theme.get(theme["id"], [])

        themes_to_process = []
        for theme in themes:
            theme_id = theme["id"]
            if force_theme and theme_id != force_theme and theme_id in cached_books and theme_id in cached_themes:
                theme["candidates"] = []
                cached_theme_info = cached_themes[theme_id]
                theme["keyword"] = cached_theme_info.get("keyword", theme.get("keyword"))
                theme["reason"] = cached_theme_info.get("reason", theme.get("reason"))
                theme["keyword_basis"] = cached_theme_info.get("keyword_basis", theme.get("keyword_basis"))
                theme["skip_process"] = True
            else:
                theme["skip_process"] = False
                themes_to_process.append(theme)

        if themes_to_process:
            with ThreadPoolExecutor(max_workers=len(themes_to_process)) as executor:
                future_to_theme = {
                    executor.submit(BookRecommendationAgent._search_theme_candidates, theme): theme
                    for theme in themes_to_process
                }
                success_count = 0
                errors = []
                for future in as_completed(future_to_theme):
                    t = future_to_theme[future]
                    try:
                        future.result()
                        if t.get("candidates"):
                            success_count += 1
                    except Exception as exc:
                        print(f"[BookAgent] Theme {t['id']} candidate search failed: {exc}")
                        t["candidates"] = []
                        t["error"] = str(exc)
                        errors.append(exc)

                if len(themes_to_process) == len(themes) and success_count == 0:
                    if errors:
                        raise errors[0]
                    else:
                        raise BookRecommendationUnavailable(
                            "일반 단행본 후보를 찾지 못했습니다.",
                            code="GENERAL_BOOK_CANDIDATES_NOT_FOUND",
                        )

        books = BookRecommendationAgent._generate_reviews(user_profile, themes, cached_books=cached_books)

        return {
            "recommendation_engine": RECOMMENDATION_ENGINE_VERSION,
            "is_fallback": False,
            "selection_policy": {
                "general_books_only": True,
                "candidate_source": "Kakao Daum 책 검색",
                "candidate_metadata": [
                    "책 소개", "저자", "번역자", "출판사", "출간일",
                    "ISBN", "가격", "판매상태", "표지", "상세 URL",
                ],
                "ranking": "개인화 검색어별 Kakao 후보 중 AI가 전체 서지정보를 비교해 가장 적합한 책을 선정",
            },
            "themes": [
                {
                    "id": theme["id"],
                    "name": theme["name"],
                    "keyword": theme["keyword"],
                    "search_terms": theme.get("search_terms", []),
                    "content_terms": theme.get("content_terms", []),
                    "selected_basis": theme.get("selected_basis", ""),
                    "reason": theme["reason"],
                    "keyword_basis": theme.get("keyword_basis", ""),
                    "basis_label": theme["basis_label"],
                    "basis_values": theme["basis_values"],
                    "candidate_count": len(theme.get("candidates", [])),
                    "search_fallback_used": bool(theme.get("search_fallback_used")),
                }
                for theme in themes
            ],
            "books": books,
            "source_disclosure": {
                "book_metadata": "Kakao Daum 책 검색",
                "cover_metadata": "Kakao Daum 책 검색 표지",
                "curation": "OpenAI를 이용해 생성한 맞춤 추천 AI 추천사",
                "display_policy": "도서 검색 결과와 AI 생성 추천을 구분해 표시합니다.",
                "providers": [KAKAO_BOOK_PROVIDER_INFO],
            },
        }

    @staticmethod
    def _enrich_book_covers(books):
        """Attach Kakao/Daum detail links and non-NLK covers as soft dependencies."""
        pending = {}
        for book in books or []:
            title = str(book.get("title") or "").strip()
            author = str(book.get("author") or "").strip()
            if not title or _safe_http_url(book.get("image", "")):
                continue
            lookup_key = (_normalize_book_title(title), _normalize_book_author(author))
            pending.setdefault(lookup_key, []).append(book)

        if not pending:
            return

        with ThreadPoolExecutor(max_workers=min(3, len(pending))) as executor:
            futures = {
                executor.submit(
                    _cached_external_book_info,
                    pending[lookup_key][0].get("title", ""),
                    pending[lookup_key][0].get("author", ""),
                    _normalize_isbn([pending[lookup_key][0].get("isbn", "")]),
                ): lookup_key
                for lookup_key in pending
            }
            for future in as_completed(futures):
                lookup_key = futures[future]
                try:
                    external_info = future.result()
                except Exception as exc:
                    print(
                        "[BookAgent] External cover lookup failed for title "
                        f"'{pending[lookup_key][0].get('title', '')}': {exc}"
                    )
                    continue
                if not isinstance(external_info, dict):
                    continue
                cover_url = external_info.get("image", "")
                detail_url = external_info.get("link", "")
                cover_provider = external_info.get("cover_provider")
                link_provider = external_info.get("link_provider")
                for book in pending[lookup_key]:
                    if cover_url:
                        book["image"] = cover_url
                        book["cover_provider"] = cover_provider
                    if detail_url:
                        book["link"] = detail_url
                        book["link_provider"] = link_provider
                    source_result = book.get("source_result")
                    if isinstance(source_result, dict):
                        if cover_url:
                            source_result["image"] = cover_url
                            source_result["cover_provider"] = cover_provider
                        if detail_url:
                            source_result["link"] = detail_url
                            source_result["link_provider"] = link_provider

    @staticmethod
    def _search_theme_candidates(theme):
        search_options = {
            "display": 8,
            "basis_values": theme["basis_values"],
            "content_terms": theme.get("content_terms"),
            "theme_id": theme["id"],
            "excluded_isbns": theme.get("excluded_isbns"),
        }
        if theme.get("search_terms"):
            search_options["search_terms"] = theme["search_terms"]
        theme["candidates"] = BookRecommendationAgent._search_kakao_books(
            theme["keyword"],
            **search_options,
        )
        if not theme["candidates"]:
            fallback_keyword = BookRecommendationAgent._fallback_search_keyword(
                theme["id"],
                theme["basis_values"],
                FALLBACK_KEYWORDS[theme["id"]][0],
            )
            theme["search_fallback_used"] = True
            theme["candidates"] = BookRecommendationAgent._search_kakao_books(
                fallback_keyword,
                display=8,
                basis_values=theme["basis_values"],
                content_terms=BookRecommendationAgent._fallback_content_terms(
                    theme["id"],
                    theme["basis_values"],
                    fallback_keyword,
                ),
                search_terms=_book_search_terms(
                    [],
                    selected_basis=(theme.get("selected_basis") or (
                        theme["basis_values"][0] if theme["basis_values"] else ""
                    )),
                    keyword=fallback_keyword,
                ),
                theme_id=theme["id"],
                excluded_isbns=theme.get("excluded_isbns"),
            )

    @staticmethod
    def _build_themes(user_profile):
        def build_theme(definition):
            theme_id = definition["id"]
            fallback_keyword, fallback_reason = FALLBACK_KEYWORDS[theme_id]
            basis_values = BookRecommendationAgent._basis_values(
                user_profile,
                definition["basis_key"],
            )

            return {
                **definition,
                "basis_values": basis_values,
                **BookRecommendationAgent._build_search_intent(
                    user_profile,
                    definition,
                    basis_values,
                    fallback_keyword,
                    fallback_reason,
                ),
            }

        with ThreadPoolExecutor(max_workers=len(THEME_DEFINITIONS)) as executor:
            return list(executor.map(build_theme, THEME_DEFINITIONS))

    @staticmethod
    def _build_search_intent(user_profile, definition, basis_values, fallback_keyword, fallback_reason):
        try:
            response = _get_llm(temperature=0.25, max_tokens=220).invoke([
                (
                    "system",
                    "당신은 책 제목의 문구가 아니라 책이 실제로 다루는 내용을 기준으로 "
                    "개인 맞춤 Kakao Daum 도서 검색어를 설계하는 큐레이터입니다. "
                    "온라인 서점 검색에서 실제 책 후보가 충분히 나오는 한국어 검색어와 추천 의도를 JSON으로만 작성하세요.",
                ),
                ("user", BookRecommendationAgent._keyword_prompt(user_profile, definition, basis_values)),
            ])
            data = BookRecommendationAgent._parse_json(response.content)
            keyword = _clean_keyword(data.get("keyword"))
            selected_basis = BookRecommendationAgent._selected_basis_value(
                data.get("selected_basis"),
                basis_values,
            )
            content_terms = _clean_content_terms(data.get("content_terms"), keyword)
            keyword, content_terms = BookRecommendationAgent._anchor_profile_topic(
                definition["id"],
                keyword,
                content_terms,
                selected_basis,
            )
            search_terms = _book_search_terms(
                data.get("search_terms"),
                selected_basis=selected_basis,
                keyword=keyword,
            )
            reason = str(data.get("reason") or "").strip()
            if keyword:
                return {
                    "keyword": keyword,
                    "content_terms": content_terms,
                    "search_terms": search_terms,
                    "selected_basis": selected_basis,
                    "reason": reason or fallback_reason,
                    "keyword_basis": definition["basis_label"],
                }
        except Exception as exc:
            print(f"[BookAgent] Keyword generation failed for {definition['id']}: {exc}")

        keyword = BookRecommendationAgent._fallback_search_keyword(
            definition["id"],
            basis_values,
            fallback_keyword,
        )
        return {
            "keyword": keyword,
            "content_terms": BookRecommendationAgent._fallback_content_terms(
                definition["id"],
                basis_values,
                fallback_keyword,
            ),
            "search_terms": _book_search_terms(
                [],
                selected_basis=(str(basis_values[0]).strip() if basis_values else ""),
                keyword=keyword,
            ),
            "selected_basis": str(basis_values[0]).strip() if basis_values else "",
            "reason": fallback_reason,
            "keyword_basis": definition["basis_label"],
        }

    @staticmethod
    def _selected_basis_value(value, basis_values):
        available = [str(item).strip() for item in basis_values if str(item).strip()]
        requested = str(value or "").strip()
        return next((item for item in available if item == requested), available[0] if available else "")

    @staticmethod
    def _anchor_profile_topic(theme_id, keyword, content_terms, selected_basis):
        """Keep an interest/hobby label visible in the actual catalog queries."""
        if theme_id not in {"interests", "hobbies"} or not selected_basis:
            return keyword, content_terms

        anchored_keyword = keyword
        if selected_basis not in keyword:
            anchored_keyword = _clean_keyword(f"{selected_basis} {keyword}")

        anchored_terms = list(content_terms or [])
        if not any(selected_basis in term for term in anchored_terms):
            anchored_terms.insert(0, selected_basis)
        return anchored_keyword, _clean_content_terms(anchored_terms, anchored_keyword)

    @staticmethod
    def _keyword_prompt(user_profile, definition, basis_values):
        basis_text = ", ".join(str(value) for value in basis_values if str(value).strip()) or "미상"
        guide_by_theme = {
            "emotion": (
                "오늘의 주된 감정이 기쁨, 평온 등 좋은 감정이면 그 긍정적인 마음 상태를 그대로 유지하고 더욱 깊이 음미하게 돕는 도서, "
                "슬픔, 분노 등 나쁜 감정이면 그 무겁고 어두운 감정을 가볍고 자연스럽게 해소하여 기분을 환기할 수 있는 도서 검색어를 만드세요. "
                "마음리포트처럼 원인 분석, 감정 진단, 하루 요약을 하는 방향과 겹치면 안 됩니다."
            ),
            "interests": (
                "프로필 관심사 분야를 더욱 자세하고 깊이 있게 파고들어 깊은 교양과 지식을 제공하는 도서 검색어를 만드세요. "
                "가벼운 힐링 서적이 아닌, 해당 분야의 정교한 입문서, 교양서, 전문 평론서 등을 타겟팅해야 합니다."
            ),
            "hobbies": (
                "프로필 취미를 실제로 즐기는 사람이 취미 활동을 더욱 전문화하고 실력을 한 단계 발전시킬 수 있는 도서 검색어를 만드세요. "
                "일반적인 에세이를 배제하고, 구체적인 고급 기술, 장비 루틴, 훈련 가이드, 역사적 감상 등 실질적으로 전문성을 향상시키는 실용 도서 중심이어야 합니다."
            ),
        }
        return f"""
[추천 유형]
- id: {definition['id']}
- 이름: {definition['name']}
- 핵심 기준: {definition['basis_label']}
- 핵심 값: {basis_text}

[해야 할 일]
{guide_by_theme.get(definition['id'], '핵심 기준을 읽고 책 검색어를 만드세요.')}

[검색 키워드 작성 규칙]
- search_terms는 Kakao Daum 책 검색 API에 각각 독립적으로 넣을 탐색어입니다. 문장이나 가상의 책 제목이 아니라 실제 온라인 서점에서 관련 책을 찾기 좋은 1~4어절의 한국어 검색어로 작성하세요.
- 관심사·취미 유형에서는 핵심 값 중 정확히 하나를 이번 검색의 selected_basis로 고르세요. selected_basis는 반드시 입력된 핵심 값의 원문과 완전히 같아야 합니다.
- keyword의 첫 부분에는 selected_basis 원문을 그대로 포함하세요. 원래 주제를 다른 분야, 넓은 교양어, 감정 상태로 치환하지 마세요.
- selected_basis가 '패션'이면 '패션', '사진 찍기'이면 '사진 찍기'가 keyword에 직접 보여야 합니다. '라이프스타일', '창의성', '힐링'만 남기는 식의 일반화는 금지합니다.
- 여러 핵심 값을 억지로 한 검색어에 섞지 말고, 한 가지 주제를 선명하게 고른 뒤 그 주제의 하위 분야·기술·역사·비평 관점으로 구체화하세요.
- 입력 문구와 비슷한 제목을 찾는 것이 아니라, 선택한 주제를 실제 본문에서 중심적으로 다루는 책을 찾을 검색어를 만드세요.
- keyword는 그 내용 전체를 대표하는 한국어 검색 의도 1개를 2~5어절로 작성하세요.
- content_terms는 책의 주제 분류나 초록에 나타날 법한 핵심 개념 2~4개를 각각 1~3어절로 작성하세요.
- content_terms 중 하나 이상에도 selected_basis 원문 또는 그 주제의 직접적인 하위 개념을 넣으세요.
- search_terms의 첫 항목은 selected_basis를 직접 반영하면서도 가장 구체적인 탐색어로 작성하세요. 예: '사진 찍기'→'사진 촬영', '드라마 보기'→'드라마 극본', '패션'→'패션 스타일링'.
- 프로필 표현이 서점에서 잘 쓰이지 않는 구어라면 출판·서점에서 통용되는 동의어를 반드시 별도 search_terms에 포함하세요. 예: '헬스'→'근력 운동', '웨이트 트레이닝', '피트니스 운동'.
- 나머지 search_terms는 같은 주제의 실용·입문·역사·비평 등 서로 다른 검색 관점 2~3개로 작성하세요. 서로 다른 관심사나 취미를 절대 섞지 마세요.
- keyword와 content_terms를 가상의 책 제목이나 감성적인 문장처럼 만들지 마세요.
- '책', '도서', '추천', '관련', '취미 생활', '관심 분야'처럼 검색 결과를 흐리는 일반어는 keyword에 넣지 마세요.
- 선택한 주제는 보존하되, 그 뒤를 검색 가능한 하위 주제·방법·관점으로 구체화하세요.
- 책 장르나 독서 목적이 드러나게 만드세요. 단, 에세이로 고정하지 마세요.
- 후보 장르는 소설, 인문, 심리, 교양, 실용서, 예술서, 만화, 자기계발, 에세이 중 맥락에 맞게 고르세요.
- 예: 마음 회복 소설, 커리어 인문학, 사진 실용서, 영화 심리 교양, 요리 레시피북.
- 감정 추천 검색어는 감정 유지/해소를 위한 독서 경험에 집중하고, 마음리포트·감정분석·자가진단처럼 보이는 단어는 피하세요.
- 관심사 추천 검색어는 관심사 명칭이 핵심 주제로 드러나야 하며, 막연한 위로/힐링 도서로 바꾸지 마세요.
- 취미 추천 검색어는 취미 활동을 직접 다루는 실용/입문/감상/역사/기술 맥락을 우선하세요.
- 검색에 필요하지 않은 인구통계 정보는 사용하지 마세요.

Below output JSON only.
{{
  "selected_basis": "핵심 값에서 원문 그대로 고른 한 항목",
  "keyword": "도서 검색 키워드",
  "search_terms": ["Kakao 책 검색어", "서점 동의어", "다른 검색 관점"],
  "content_terms": ["책이 다룰 핵심 주제", "관련 방법 또는 관점"],
  "reason": "이 기준으로 검색어를 만든 이유를 45자 안팎으로 설명",
  "keyword_basis": "{definition['basis_label']}"
}}
""".strip()

    @staticmethod
    def _fallback_search_keyword(theme_id, basis_values, fallback_keyword):
        values = [str(value).strip() for value in basis_values if str(value).strip()]
        if not values:
            return fallback_keyword
        if theme_id == "emotion":
            return f"{values[0]} 마음 소설"
        if theme_id == "interests":
            return " ".join(values[:2])
        if theme_id == "hobbies":
            return f"{' '.join(values[:2])} 실용"
        return " ".join(values[:2]) or fallback_keyword

    @staticmethod
    def _fallback_content_terms(theme_id, basis_values, fallback_keyword):
        values = [str(value).strip() for value in basis_values if str(value).strip()]
        theme_terms = {
            "emotion": ["마음 회복", "감정 치유", "휴식"],
            "interests": ["교양", "역사", "비평"],
            "hobbies": ["방법", "기술", "활용"],
        }
        return _clean_content_terms(
            [*values[:2], *theme_terms.get(theme_id, []), fallback_keyword],
            fallback_keyword,
        )

    @staticmethod
    def _search_kakao_books(
        keyword,
        display=8,
        basis_values=None,
        content_terms=None,
        search_terms=None,
        theme_id="",
        excluded_isbns=None,
    ):
        service_key = _kakao_rest_api_key()
        if not service_key:
            raise BookRecommendationUnavailable(
                "Kakao Daum 책 검색 API 인증키가 설정되지 않았습니다.",
                code="KAKAO_CREDENTIALS_MISSING",
            )

        queries = _kakao_search_queries(
            keyword,
            search_terms=search_terms,
            basis_values=basis_values,
            content_terms=content_terms,
        )[:KAKAO_BOOK_QUERY_LIMIT]
        books = []
        books_by_identity = {}
        books_by_title_author = {}
        successful_requests = 0
        request_errors = []

        for query_index, query in enumerate(queries):
            try:
                payload = _request_kakao_book_search(
                    service_key,
                    query,
                    size=KAKAO_BOOK_PAGE_SIZE,
                )
                successful_requests += 1
            except Exception as exc:
                request_errors.append(exc)
                print(f"[BookAgent] Kakao book search failed for '{query}': {exc}")
                continue

            for result_index, document in enumerate(payload.get("documents") or []):
                if not isinstance(document, dict):
                    continue
                book = BookRecommendationAgent._normalize_kakao_book_document(
                    len(books) + 1,
                    document,
                    query=query,
                    query_index=query_index,
                    result_index=result_index,
                )
                title_identity = _normalize_book_title(book.get("title"))
                author_identity = _normalize_book_author(book.get("author"))
                identity = book.get("isbn") or f"{title_identity}|{author_identity}"
                title_author_identity = f"{title_identity}|{author_identity}"
                if (
                    not book.get("title")
                    or not identity.strip("|")
                    or any(marker in book["title"] for marker in ("체험판", "미리보기", "요약본"))
                ):
                    continue
                existing = (
                    books_by_identity.get(identity)
                    or books_by_title_author.get(title_author_identity)
                )
                if existing:
                    if query not in existing["matched_queries"]:
                        existing["matched_queries"].append(query)
                    continue
                books_by_identity[identity] = book
                books_by_title_author[title_author_identity] = book
                books.append(book)

        if successful_requests == 0 and request_errors:
            raise BookRecommendationUnavailable(
                "Kakao Daum 책 검색 서비스를 현재 이용할 수 없습니다.",
                code="KAKAO_SERVICE_UNAVAILABLE",
            ) from request_errors[-1]

        ranked_books = _rank_kakao_books(
            books,
            keyword=keyword,
            basis_values=basis_values or [],
            content_terms=content_terms or [],
            search_terms=search_terms or [],
            theme_id=theme_id,
        )
        ranked_books = _without_excluded_books(ranked_books, excluded_isbns)[:display]
        for index, book in enumerate(ranked_books, start=1):
            book["candidate_id"] = f"book_{index}"
        return ranked_books

    @staticmethod
    def _normalize_kakao_book_document(
        index,
        document,
        *,
        query="",
        query_index=0,
        result_index=0,
    ):
        title = _clean_kakao_text(document.get("title"))
        description = _clean_kakao_text(document.get("contents"))
        authors = _clean_string_list(document.get("authors"))
        translators = _clean_string_list(document.get("translators"))
        published_at = str(document.get("datetime") or "").strip()
        issued_match = re.search(r"(?:19|20)\d{2}", published_at)
        isbn = _normalize_isbn(str(document.get("isbn") or "").split())
        link = _safe_daum_book_url(document.get("url")) or _daum_book_search_url(title=title)
        image = _safe_external_cover_url(document.get("thumbnail"))
        return {
            "candidate_id": f"book_{index}",
            "title": title,
            "author": ", ".join(authors),
            "authors": authors,
            "translators": translators,
            "publisher": _clean_kakao_text(document.get("publisher")),
            "description": description,
            "image": image,
            "link": link,
            "isbn": isbn,
            "raw_isbn": str(document.get("isbn") or "").strip(),
            "subjects": [],
            "bibliographic_id": "",
            "published_at": published_at,
            "issued_year": int(issued_match.group(0)) if issued_match else None,
            "price": _safe_int(document.get("price")),
            "sale_price": _safe_int(document.get("sale_price")),
            "status": str(document.get("status") or "").strip(),
            "matched_queries": [query] if query else [],
            "query_index": query_index,
            "result_index": result_index,
            "general_book_verified": True,
            "recent_book_verified": False,
            "source_provider": KAKAO_BOOK_PROVIDER_INFO,
            "cover_provider": KAKAO_BOOK_PROVIDER_INFO if image else None,
            "link_provider": KAKAO_BOOK_PROVIDER_INFO,
        }

    @staticmethod
    def _search_nlk_books(
        keyword,
        display=4,
        basis_values=None,
        content_terms=None,
        catalog_terms=None,
        theme_id="",
        excluded_isbns=None,
    ):
        service_key = _nlk_service_key()
        if not service_key:
            raise BookRecommendationUnavailable(
                "국립중앙도서관 서지정보 API 인증키가 설정되지 않았습니다.",
                code="NLK_CREDENTIALS_MISSING",
            )

        books = []
        seen_identifiers = set()
        seen_titles = set()
        successful_requests = 0
        request_errors = []
        search_terms = _semantic_search_terms(
            keyword,
            content_terms,
            basis_values,
            catalog_terms,
        )[:NLK_BOOK_QUERY_LIMIT]

        for term_index, search_term in enumerate(search_terms):
            try:
                first_payload = _request_nlk_books(
                    service_key,
                    search_term,
                    NLK_BOOK_PAGE_SIZE,
                    page_no=1,
                )
                successful_requests += 1
                def collect_payload(payload):
                    for item in _nlk_items(payload):
                        book = BookRecommendationAgent._normalize_nlk_book_item(
                            len(books) + 1,
                            item,
                        )
                        if not _is_general_book(item, book) or not _is_recent_book(book):
                            continue
                        book["general_book_verified"] = True
                        book["recent_book_verified"] = True
                        identity = book.get("isbn") or book.get("bibliographic_id")
                        title_identity = re.sub(
                            r"\s+",
                            "",
                            book.get("title") or "",
                        ).lower()
                        if (
                            not book.get("title")
                            or not identity
                            or identity in seen_identifiers
                            or title_identity in seen_titles
                        ):
                            continue
                        seen_identifiers.add(identity)
                        seen_titles.add(title_identity)
                        books.append(book)

                collect_payload(first_payload)
                for page_no in _nlk_probe_page_numbers(first_payload)[:NLK_BOOK_MAX_PROBE_PAGES]:
                    try:
                        collect_payload(
                            _request_nlk_books(
                                service_key,
                                search_term,
                                NLK_BOOK_PAGE_SIZE,
                                page_no=page_no,
                            )
                        )
                    except Exception as exc:
                        print(
                            f"[BookAgent] NLK probe page {page_no} failed "
                            f"for '{search_term}': {exc}"
                        )

            except Exception as exc:
                request_errors.append(exc)
                print(f"[BookAgent] NLK LOD search failed for '{search_term}': {exc}")

        if successful_requests == 0 and request_errors:
            raise BookRecommendationUnavailable(
                "국립중앙도서관 서지정보 서비스를 현재 이용할 수 없습니다.",
                code="NLK_SERVICE_UNAVAILABLE",
            ) from request_errors[-1]

        ranked_books = _rank_personalized_books(
            books,
            keyword=keyword,
            basis_values=basis_values or [],
            content_terms=content_terms or [],
            theme_id=theme_id,
        )
        ranked_books = _without_excluded_books(ranked_books, excluded_isbns)[:display]
        for index, book in enumerate(ranked_books, start=1):
            book["candidate_id"] = f"book_{index}"
        return ranked_books

    @staticmethod
    def _normalize_nlk_book_item(index, item):
        title = _first_text(item, "DCTERMS_title", "RDFS_label", "label")
        description = _first_text(item, "DCTERMS_abstract", "DCTERMS_description")
        subjects = _text_values(item, "DCTERMS_subject", "NLON_keyword")
        material_types = _text_values(item, "RDF_type", "DC_type")
        raw_isbn = _normalize_isbn(_text_values(item, "BIBO_isbn"))
        link = _daum_book_search_url(title=title)
        return {
            "candidate_id": f"book_{index}",
            "title": title,
            "author": _first_text(item, "DC_creator", "DCTERMS_creator"),
            "publisher": _first_text(item, "DC_publisher"),
            "description": description,
            "image": "",
            "link": link,
            "isbn": raw_isbn,
            "subjects": subjects,
            "bibliographic_id": _first_text(item, "BIBLIO_ID"),
            "issued_year": _issued_year(item),
            "material_types": material_types,
            "general_book_verified": False,
            "source_provider": NLK_PROVIDER_INFO,
        }

    @staticmethod
    def _generate_reviews(user_profile, themes, cached_books=None):
        if cached_books is None:
            cached_books = {}

        results = [None] * len(themes)

        def process_theme(index, theme):
            theme_id = theme["id"]
            if theme.get("skip_process") and theme_id in cached_books:
                return index, cached_books[theme_id]

            if not theme.get("candidates"):
                return index, {
                    "theme": theme["name"],
                    "theme_id": theme_id,
                    "theme_reason": theme.get("reason", ""),
                    "keyword": theme.get("keyword", ""),
                    "keyword_basis": theme.get("keyword_basis", ""),
                    "title": "",
                }

            try:
                return index, BookRecommendationAgent._generate_single_review(user_profile, theme)
            except Exception as exc:
                print(f"[BookAgent] Review generation failed for {theme['id']}: {exc}")
                return index, BookRecommendationAgent._fallback_review(theme)

        with ThreadPoolExecutor(max_workers=len(themes)) as executor:
            futures = [
                executor.submit(process_theme, index, theme)
                for index, theme in enumerate(themes)
            ]
            for future in as_completed(futures):
                index, result = future.result()
                results[index] = result

        return [r for r in results if r is not None]

    @staticmethod
    def _generate_single_review(user_profile, theme):
        chain = (
            ChatPromptTemplate.from_messages(
                [
                    (
                        "system",
                        "당신은 개인 맞춤 도서 큐레이터입니다. "
                        "출력 형식을 지키고, 제공된 candidate_id 중에서만 고르세요.",
                    ),
                    ("user", BookRecommendationAgent._single_review_prompt(user_profile, theme)),
                ]
            )
            | _get_llm(temperature=0.45, max_tokens=360)
            | StrOutputParser()
        )
        raw_result = chain.invoke({})
        selected_id, genre, review = _parse_review_result(raw_result)
        selected_book = _find_candidate(theme["candidates"], selected_id)
        if selected_book is None:
            selected_book = theme["candidates"][0]

        return BookRecommendationAgent._book_payload(
            theme,
            selected_book,
            review or _compose_fallback_review(theme, selected_book),
            genre=genre,
        )

    @staticmethod
    def _single_review_prompt(user_profile, theme):
        basis_text = ", ".join(theme["basis_values"]) or "미상"
        candidate_lines = []
        for book in theme.get("candidates", []):
            candidate_lines.append(
                "- "
                f"candidate_id: {book['candidate_id']}\n"
                f"  제목: {book['title']}\n"
                f"  저자: {book['author']}\n"
                f"  번역자: {', '.join(book.get('translators') or []) or '없음/미제공'}\n"
                f"  출판사: {book['publisher']}\n"
                f"  출간일: {(book.get('published_at') or '')[:10] or '미제공'}\n"
                f"  ISBN: {book.get('isbn') or '미제공'}\n"
                f"  정가/판매가: {book.get('price') or '미제공'} / {book.get('sale_price') or '미제공'}\n"
                f"  판매상태: {book.get('status') or '미제공'}\n"
                f"  일치한 검색어: {', '.join(book.get('matched_queries') or [])}\n"
                f"  책 소개: {book['description'][:260]}"
            )

        return f"""
[개인화 정보]
- 오늘의 주된 감정: {user_profile.get("today_emotion") or "평온"}
- 프로필 관심사: {_join_values(user_profile.get("interests")) or "미상"}
- 프로필 취미: {_join_values(user_profile.get("hobbies")) or "미상"}

[추천 조합]
- 실제 고려 기준: {theme['basis_label']}
- 참고 맥락: {theme['basis_label']} {basis_text}
- 검색 키워드: {theme.get('keyword') or '미상'}
- 책에서 다루길 바라는 핵심 내용: {', '.join(theme.get('content_terms') or []) or '미상'}
- 검색 키워드 생성 의도: {theme.get('reason') or '사용자 맥락에 맞는 책 후보를 찾기 위한 검색어입니다.'}

[검증된 개인화 상위 후보]
{chr(10).join(candidate_lines)}

후보 중 현재 사용자 맥락에 가장 적합한 책 1권을 고르고, 그 책에 대한 ３～４문장의 추천 서평을 작성하세요.
제목이 입력 문구와 비슷하다는 이유만으로 고르지 말고, Kakao가 제공한 책 소개, 저자·번역자 구성, 출판사, 출간 시점, 판매상태, ISBN과 검색어 일치 맥락을 함께 비교하세요.
책 소개가 짧더라도 저자·출판사·출간정보 등 제공된 다른 서지정보를 활용해 선택하되, 후보 정보에 없는 사실은 만들지 마세요.
서평은 이 책을 고른 이유가 분명히 느껴지도록, 책의 주제/분위기/현재 맥락과 맞는 지점을 자연스럽게 포함하세요.
참고 맥락은 책을 고르고 문장의 톤을 잡는 데 사용하세요.
유형별 기준을 반드시 지키세요.
- 감정 추천: 오늘의 감정이 기쁨, 평온, 만족, 설렘처럼 긍정적이면 그 감정을 유지하거나 더 선명하게 느끼게 하는 책을 고르세요. 슬픔, 불안, 분노, 외로움, 지침, 스트레스처럼 무거운 감정이면 감정을 해소하거나 숨을 고르게 하는 책을 고르세요. 마음리포트처럼 감정의 원인, 패턴, 진단, 하루 분석을 설명하지 말고 독서 경험만 말하세요.
- 관심사 추천: 관심사 자체를 실제 주제로 다루는 책을 고르세요. 예를 들어 음악이면 음악 감상, 음악사, 뮤지션, 악기, 장르 해설처럼 그 관심사에 대해 읽을 내용이 있어야 합니다. 관심사를 막연한 위로 문장으로 바꾸지 마세요.
- 취미 추천: 취미를 실제로 즐기는 사람에게 도움이 되는 책을 고르세요. 방법, 기술, 도구, 작품 감상, 문화, 역사, 루틴처럼 취미 관점이 드러나야 하며, 취미를 소재로 한 일반 감성 에세이에 치우치지 마세요.
도서 장르는 후보 도서의 실제 성격을 따르세요. 에세이, 소설, 인문서, 실용서, 예술서, 만화 등 특정 장르를 사전에 우대하지 마세요.
서평 본문에 "관심사가 있어서", "취미가 있어서", "검색어", "키워드", "근거", "데이터", "마음리포트", "분석 결과"처럼 추천 로직이나 리포트 맥락이 직접 드러나는 표현을 쓰지 마세요.
후보에 없는 책을 새로 고르거나 만들면 안 됩니다.
genre는 선택한 책의 장르를 2~8자 정도로 짧게 쓰세요. 예: 소설, 심리, 인문, 실용서, 예술서, 만화, 자기계발, 에세이.

아래 형식만 지키세요.
candidate_id: 선택한 후보 ID
genre: 장르
review: 추천 서평
""".strip()

    @staticmethod
    def _merge_reviews(llm_results, themes):
        if not isinstance(llm_results, list):
            return BookRecommendationAgent._fallback_reviews(themes)

        results_by_theme = {}
        for item in llm_results:
            if not isinstance(item, dict):
                continue
            theme_id = item.get("theme_id")
            if theme_id:
                results_by_theme[theme_id] = item

        # Some models return an array in theme order without theme_id. Keep those
        # reviews instead of dropping them, because each tab needs its own review.
        ordered_results = [item for item in llm_results if isinstance(item, dict)]
        final_results = []

        for index, theme in enumerate(themes):
            result = results_by_theme.get(theme["id"]) or (
                ordered_results[index] if index < len(ordered_results) else {}
            )
            selected_book = _find_candidate(
                theme.get("candidates", []),
                result.get("candidate_id"),
            )
            if selected_book is None:
                selected_book = theme["candidates"][0]

            final_results.append(
                {
                    "theme": theme["name"],
                    "theme_id": theme["id"],
                    "theme_reason": theme.get("reason", ""),
                    "keyword": theme.get("keyword", ""),
                    "keyword_basis": theme.get("keyword_basis", ""),
                    "genre": result.get("genre") or _infer_genre(selected_book, theme),
                    "title": selected_book.get("title", ""),
                    "author": selected_book.get("author", ""),
                    "publisher": selected_book.get("publisher", ""),
                    "image": selected_book.get("image", ""),
                    "link": selected_book.get("link", ""),
                    "isbn": selected_book.get("isbn", ""),
                    "data_used": _visible_data_used(theme, result.get("data_used")),
                    "review": result.get("review")
                    or _compose_fallback_review(theme, selected_book),
                }
            )

        return final_results

    @staticmethod
    def _fallback_reviews(themes):
        results = []
        for theme in themes:
            if not theme.get("candidates"):
                continue
            book = theme["candidates"][0]
            results.append(BookRecommendationAgent._fallback_review(theme))
        return results

    @staticmethod
    def _fallback_review(theme):
        book = theme["candidates"][0]
        return BookRecommendationAgent._book_payload(
            theme,
            book,
            _compose_fallback_review(theme, book),
            genre=_infer_genre(book, theme),
        )

    @staticmethod
    def _book_payload(theme, book, review, genre=None):
        source_result = {
            "title": book.get("title", ""),
            "author": book.get("author", ""),
            "publisher": book.get("publisher", ""),
            "description": book.get("description", ""),
            "image": book.get("image", ""),
            "link": book.get("link", ""),
            "isbn": book.get("isbn", ""),
            "subjects": book.get("subjects", []),
            "authors": book.get("authors", []),
            "translators": book.get("translators", []),
            "published_at": book.get("published_at", ""),
            "price": book.get("price", 0),
            "sale_price": book.get("sale_price", 0),
            "status": book.get("status", ""),
            "matched_queries": book.get("matched_queries", []),
            "bibliographic_id": book.get("bibliographic_id", ""),
            "issued_year": book.get("issued_year"),
            "general_book_verified": bool(book.get("general_book_verified")),
            "recent_book_verified": bool(book.get("recent_book_verified")),
            "provider": book.get("source_provider") or KAKAO_BOOK_PROVIDER_INFO,
            "cover_provider": book.get("cover_provider"),
            "link_provider": book.get("link_provider"),
        }
        ai_curation = {
            "genre": genre or _infer_genre(book, theme),
            "review": review,
            "theme": theme["name"],
            "theme_reason": theme.get("reason", ""),
        }
        return {
            "theme": theme["name"],
            "theme_id": theme["id"],
            "theme_reason": theme.get("reason", ""),
            "keyword": theme.get("keyword", ""),
            "keyword_basis": theme.get("keyword_basis", ""),
            "genre": ai_curation["genre"],
            "title": book.get("title", ""),
            "author": book.get("author", ""),
            "publisher": book.get("publisher", ""),
            "image": book.get("image", ""),
            "link": book.get("link", ""),
            "isbn": book.get("isbn", ""),
            "description": book.get("description", ""),
            "subjects": book.get("subjects", []),
            "authors": book.get("authors", []),
            "translators": book.get("translators", []),
            "published_at": book.get("published_at", ""),
            "price": book.get("price", 0),
            "sale_price": book.get("sale_price", 0),
            "status": book.get("status", ""),
            "matched_queries": book.get("matched_queries", []),
            "bibliographic_id": book.get("bibliographic_id", ""),
            "issued_year": book.get("issued_year"),
            "general_book_verified": bool(book.get("general_book_verified")),
            "recent_book_verified": bool(book.get("recent_book_verified")),
            "personalization_score": book.get("personalization_score", 0),
            "match_terms": book.get("match_terms", []),
            "source_provider": source_result["provider"],
            "cover_provider": book.get("cover_provider"),
            "link_provider": book.get("link_provider"),
            "source_result": source_result,
            "ai_curation": ai_curation,
            "data_used": _visible_data_used(theme),
            "review": review,
        }

    @staticmethod
    def _basis_values(user_profile, key):
        value = user_profile.get(key)
        if key == "today_emotion" and not value:
            value = "평온"
        if isinstance(value, list):
            return [str(item) for item in value if item]
        if value:
            return [str(value)]
        return []

    @staticmethod
    def _parse_json(content):
        text = str(content).strip()
        if text.startswith("```"):
            text = re.sub(r"^```(?:json)?\s*", "", text)
            text = re.sub(r"\s*```$", "", text)
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            match = re.search(r"(\{.*\}|\[.*\])", text, re.DOTALL)
            if not match:
                raise
            return json.loads(match.group(0))


def _get_llm(temperature=0.4, max_tokens=1000):
    from langchain_openai import ChatOpenAI

    return ChatOpenAI(
        model=os.environ.get("MYBOOK_OPENAI_MODEL", "gpt-5.4-mini"),
        temperature=temperature,
        max_tokens=max_tokens,
        api_key=os.environ.get("OPENAI_API_KEY"),
    )


def _visible_data_used(theme, llm_values=None):
    values = []
    if isinstance(llm_values, list):
        values.extend(str(item) for item in llm_values if item)

    for value in theme.get("basis_values", []):
        label_value = f"{theme['basis_label']} {value}"
        if label_value not in values:
            values.append(label_value)

    blocked_patterns = ("나이", "성별", "남성", "여성")
    return [
        value
        for value in values
        if not any(pattern in value for pattern in blocked_patterns)
        and not re.search(r"\d+\s*세", value)
    ][:4]


def _nlk_service_key():
    return (
        os.environ.get("NLK_BIBLIO_SERVICE_KEY")
        or os.environ.get("DATA_GO_KR_SERVICE_KEY")
        or ""
    ).strip()


def _kakao_rest_api_key():
    return (
        os.environ.get("KAKAO_REST_API_KEY")
        or os.environ.get("KAKAO_CLIENT_ID")
        or ""
    ).strip()


def _cached_external_book_info(title, author="", isbn=""):
    title = str(title or "").strip()
    author = str(author or "").strip()
    normalized_isbn = _normalize_isbn([isbn])
    cache_identity = f"{_normalize_book_title(title)}|{_normalize_book_author(author)}"
    cache_key = "mybook:external-book:v4:" + hashlib.sha256(
        cache_identity.encode("utf-8")
    ).hexdigest()
    cached = cache.get(cache_key)
    if (
        isinstance(cached, dict)
        and _safe_external_cover_url(cached.get("image"))
        and _safe_daum_book_url(cached.get("link"))
    ):
        return cached

    kakao_info = {}
    service_key = _kakao_rest_api_key()
    if service_key:
        try:
            kakao_info = _request_kakao_book_info(service_key, title, author)
        except (requests.RequestException, RuntimeError, ValueError) as exc:
            print(f"[BookAgent] Kakao book lookup unavailable for title '{title}': {exc}")

    kakao_cover = _safe_external_cover_url(kakao_info.get("image"))
    kakao_link = _safe_daum_book_url(kakao_info.get("link"))
    result = {
        "image": kakao_cover or (
            _open_library_cover_url(normalized_isbn) if normalized_isbn else ""
        ),
        "link": kakao_link or _daum_book_search_url(title=title),
        "cover_provider": (
            KAKAO_BOOK_PROVIDER_INFO
            if kakao_cover
            else OPEN_LIBRARY_COVER_PROVIDER_INFO
        ),
        "link_provider": KAKAO_BOOK_PROVIDER_INFO,
    }
    cache.set(cache_key, result, timeout=BOOK_COVER_CACHE_SECONDS)
    return result


def _request_kakao_book_search(service_key, query, *, size=20, page=1, sort="accuracy"):
    response = None
    for attempt in range(KAKAO_BOOK_RETRY_COUNT + 1):
        try:
            response = requests.get(
                KAKAO_BOOK_API_URL,
                params={
                    "query": str(query or "").strip(),
                    "sort": sort,
                    "page": max(1, min(50, int(page))),
                    "size": max(1, min(50, int(size))),
                },
                headers={
                    "Accept": "application/json",
                    "Authorization": f"KakaoAK {service_key}",
                },
                timeout=KAKAO_BOOK_TIMEOUT_SECONDS,
            )
        except (requests.Timeout, requests.ConnectionError):
            if attempt < KAKAO_BOOK_RETRY_COUNT:
                time.sleep(0.25 * (2 ** attempt))
                continue
            raise
        if response.status_code not in {429, 500, 502, 503, 504}:
            response.raise_for_status()
            try:
                payload = response.json()
            except ValueError as exc:
                raise RuntimeError("Kakao book API returned a non-JSON response") from exc
            if not isinstance(payload, dict) or not isinstance(payload.get("documents", []), list):
                raise RuntimeError("Kakao book API returned an invalid response")
            return payload
        if attempt < KAKAO_BOOK_RETRY_COUNT:
            time.sleep(0.25 * (2 ** attempt))

    response.raise_for_status()
    return response.json()


def _request_kakao_book_info(service_key, title, author=""):
    title = str(title or "").strip()
    if not title:
        return {}
    response = requests.get(
        KAKAO_BOOK_API_URL,
        params={
            "query": title,
            "target": "title",
            "size": 10,
        },
        headers={
            "Accept": "application/json",
            "Authorization": f"KakaoAK {service_key}",
        },
        timeout=BOOK_COVER_TIMEOUT_SECONDS,
    )
    response.raise_for_status()
    try:
        payload = response.json()
    except ValueError as exc:
        raise RuntimeError("Kakao book API returned a non-JSON response") from exc

    if not isinstance(payload, dict):
        raise RuntimeError("Kakao book API returned an invalid response")

    ranked_documents = []
    normalized_title = _normalize_book_title(title)
    normalized_author = _normalize_book_author(author)
    for index, document in enumerate(payload.get("documents") or []):
        if not isinstance(document, dict):
            continue
        document_title = _normalize_book_title(document.get("title"))
        if not document_title or not (
            document_title == normalized_title
            or document_title in normalized_title
            or normalized_title in document_title
        ):
            continue
        document_authors = _normalize_book_author(
            " ".join(str(value) for value in document.get("authors") or [])
        )
        title_score = 4 if document_title == normalized_title else 2
        author_score = (
            3 if normalized_author and normalized_author in document_authors else 0
        )
        cover_score = 1 if _safe_external_cover_url(document.get("thumbnail")) else 0
        ranked_documents.append(
            (title_score + author_score + cover_score, -index, document)
        )

    if ranked_documents:
        document = max(ranked_documents, key=lambda item: (item[0], item[1]))[2]
        return {
            "image": _safe_external_cover_url(document.get("thumbnail")),
            "link": _daum_book_search_url(title=title),
        }
    return {}


def _request_nlk_books(service_key, keyword, display, page_no=1):
    response = None
    for attempt in range(NLK_BOOK_RETRY_COUNT + 1):
        try:
            response = requests.get(
                NLK_BOOK_API_URL,
                params={
                    "serviceKey": service_key,
                    "pageNo": max(1, int(page_no)),
                    "numOfRows": min(NLK_BOOK_PAGE_SIZE, max(1, int(display))),
                    "type": "json",
                    "label": keyword,
                },
                headers={"Accept": "application/json"},
                timeout=NLK_BOOK_TIMEOUT_SECONDS,
            )
        except (requests.Timeout, requests.ConnectionError):
            if attempt < NLK_BOOK_RETRY_COUNT:
                time.sleep(0.25 * (2 ** attempt))
                continue
            raise
        if response.status_code not in {429, 500, 502, 503, 504}:
            response.raise_for_status()
            try:
                return response.json()
            except ValueError as exc:
                raise RuntimeError("NLK API returned a non-JSON response") from exc
        if attempt < NLK_BOOK_RETRY_COUNT:
            time.sleep(0.25 * (2 ** attempt))

    response.raise_for_status()
    return response.json()


def _nlk_probe_page_numbers(first_payload):
    total_count, rows_per_page = _nlk_page_info(first_payload)
    if total_count <= rows_per_page:
        return []

    last_page = max(1, math.ceil(total_count / rows_per_page))
    page_numbers = []
    # The catalog commonly returns older records first. Probe the tail before
    # intermediate pages so the ten-year freshness policy can find recent books
    # even when only one additional page is allowed.
    for ratio in (0.8, 1.0, 0.6, 0.4, 0.2):
        page_no = max(2, min(last_page, math.ceil(last_page * ratio)))
        if page_no not in page_numbers:
            page_numbers.append(page_no)

    return page_numbers


def _nlk_root(payload):
    return payload.get("response", payload) if isinstance(payload, dict) else {}


def _nlk_page_info(payload):
    root = _nlk_root(payload)
    body = root.get("body", {}) if isinstance(root, dict) else {}
    try:
        total_count = max(0, int(body.get("totalCount") or 0))
    except (TypeError, ValueError):
        total_count = 0
    try:
        rows_per_page = max(1, int(body.get("numOfRows") or NLK_BOOK_PAGE_SIZE))
    except (TypeError, ValueError):
        rows_per_page = NLK_BOOK_PAGE_SIZE
    return total_count, rows_per_page


def _nlk_items(payload):
    root = _nlk_root(payload)
    header = root.get("header", {}) if isinstance(root, dict) else {}
    result_code = str(header.get("resultCode") or "").strip()
    result_message = str(header.get("resultMsg") or "").strip()
    if result_code in {"03", "3"} or result_message == "NODATA_ERROR":
        return []
    if result_code and result_code not in {"00", "0", "NORMAL_SERVICE"}:
        raise RuntimeError(result_message or f"NLK API error: {result_code}")
    body = root.get("body", {}) if isinstance(root, dict) else {}
    items = body.get("items", {}) if isinstance(body, dict) else {}
    if isinstance(items, dict):
        items = items.get("item", [])
    if isinstance(items, dict):
        return [items]
    return items if isinstance(items, list) else []


def _nlk_search_terms(keyword):
    cleaned = re.sub(r"[^0-9A-Za-z가-힣\s]", " ", str(keyword or ""))
    tokens = [token for token in cleaned.split() if len(token) >= 2]
    generic = {"추천", "도서", "책", "입문", "실용", "교양"}
    meaningful = [token for token in tokens if token not in generic]
    terms = []
    fallback_tokens = meaningful or tokens
    for term in [" ".join(tokens), *fallback_tokens]:
        term = term.strip()
        if term and term not in terms:
            terms.append(term)
    return terms[:4]


def _catalog_core_term(value):
    """Return a short noun-like anchor suitable for the NLK ``label`` lookup."""
    cleaned = re.sub(r"[^0-9A-Za-z가-힣\s]", " ", str(value or ""))
    tokens = [token for token in cleaned.split() if len(token) >= 2]
    if not tokens:
        return ""

    for token in tokens:
        for source in BASIS_TOKEN_ALIASES:
            if source == token or source in token or token in source:
                return source

    action_tokens = {
        "하기", "보기", "듣기", "읽기", "찍기", "만들기", "다니기",
        "감상", "탐방", "투어", "활동", "생활",
    }
    return next((token for token in tokens if token not in action_tokens), tokens[0])


def _book_search_terms(values, *, selected_basis="", keyword=""):
    """Validate Kakao queries while retaining the profile topic as fallback."""
    if isinstance(values, str):
        values = re.split(r"[,/|\n]", values)
    if not isinstance(values, (list, tuple)):
        values = []

    terms = []
    basis_core = _catalog_core_term(selected_basis)

    for value in values:
        cleaned = re.sub(r"[^0-9A-Za-z가-힣\s]", " ", str(value or ""))
        tokens = [token for token in cleaned.split() if len(token) >= 2][:4]
        term = " ".join(tokens).strip()
        if term and term not in terms:
            terms.append(term)
        if len(terms) >= 4:
            break

    if basis_core and basis_core not in terms:
        terms = terms[:3]
        terms.append(basis_core)

    if len(terms) < 2:
        for value in _nlk_search_terms(keyword):
            tokens = value.split()[:2]
            term = " ".join(tokens).strip()
            if term and term not in terms:
                terms.append(term)
            if len(terms) >= 2:
                break
    return terms[:4]


def _catalog_search_terms(values, *, selected_basis="", keyword=""):
    """Backward-compatible alias for stored payloads and older callers."""
    return _book_search_terms(
        values,
        selected_basis=selected_basis,
        keyword=keyword,
    )


def _semantic_search_terms(keyword, content_terms=None, basis_values=None, catalog_terms=None):
    """Prefer LLM catalog terms, then use the profile topic as a guardrail."""
    terms = []
    content_values = [value for value in content_terms or [] if str(value).strip()]
    basis_values = [value for value in basis_values or [] if str(value).strip()]
    catalog_values = [value for value in catalog_terms or [] if str(value).strip()]

    # The keyword is server-anchored to the LLM-selected profile value. Do not
    # infer the selected topic from broader content terms because words such as
    # "브랜드" could accidentally activate another saved interest.
    intent_tokens = set(_personalization_tokens(keyword, [], catalog_values[:1]))
    focused_basis_values = [
        value
        for value in basis_values
        if _expanded_basis_tokens([value]).intersection(intent_tokens)
    ]
    discovery_basis_values = (focused_basis_values or basis_values[:1])[:1]

    # The LLM has already been constrained to short, noun-like bibliography
    # terms. Search those specific terms before the broader profile label.
    for value in catalog_values:
        exact_terms = _nlk_search_terms(value)
        if exact_terms and exact_terms[0] not in terms:
            terms.append(exact_terms[0])

    for value in discovery_basis_values:
        core_term = _catalog_core_term(value)
        if core_term and core_term not in terms:
            terms.append(core_term)

    for value in discovery_basis_values:
        raw_tokens = _personalization_tokens("", [value])
        alias_added = False
        for token in raw_tokens:
            for source, aliases in BASIS_TOKEN_ALIASES.items():
                if source not in token and token not in source:
                    continue
                alias = next((item for item in aliases if item not in terms), None)
                if alias:
                    terms.append(alias)
                    alias_added = True
                    break
            if alias_added or len(terms) >= NLK_BOOK_QUERY_LIMIT:
                break

    for value in content_values:
        exact_terms = _nlk_search_terms(value)
        if exact_terms and exact_terms[0] not in terms:
            terms.append(exact_terms[0])

    for value in [keyword, *basis_values]:
        for term in _nlk_search_terms(value):
            if term not in terms:
                terms.append(term)
    return terms[:8]


def _text_values(item, *keys):
    values = []
    for key in keys:
        value = item.get(key) if isinstance(item, dict) else None
        candidates = value if isinstance(value, list) else [value]
        for candidate in candidates:
            if isinstance(candidate, dict):
                candidate = candidate.get("value") or candidate.get("label") or ""
            text = str(candidate or "").strip()
            if text and text not in values:
                values.append(text)
    return values


def _first_text(item, *keys):
    values = _text_values(item, *keys)
    return values[0] if values else ""


def _safe_http_url(value):
    text = str(value or "").strip()
    return text if text.startswith(("https://", "http://")) else ""


def _normalize_book_title(value):
    return re.sub(r"[^0-9a-z가-힣]", "", str(value or "").lower())


def _normalize_book_author(value):
    return re.sub(r"[^0-9a-z가-힣]", "", str(value or "").lower())


def _daum_book_search_url(title=""):
    query = str(title or "").strip()
    if not query:
        return "https://search.daum.net/search?w=book"
    return "https://search.daum.net/search?" + urlencode({"w": "book", "q": query})


def _without_excluded_books(books, excluded_isbns=None):
    candidates = list(books or [])
    excluded = {
        normalized
        for value in excluded_isbns or []
        if (normalized := _normalize_isbn([value]))
    }
    if not excluded:
        return candidates
    eligible = [book for book in candidates if book.get("isbn") not in excluded]
    return eligible or candidates


def _open_library_cover_url(isbn):
    return f"https://covers.openlibrary.org/b/isbn/{isbn}-L.jpg?default=false"


def _safe_external_cover_url(value):
    url = _safe_http_url(value)
    parsed = urlparse(url)
    host = (parsed.hostname or "").lower()
    allowed_hosts = {
        "covers.openlibrary.org",
    }
    allowed_suffixes = (".kakaocdn.net", ".daumcdn.net")
    if host not in allowed_hosts and not host.endswith(allowed_suffixes):
        return ""
    if url.startswith("http://"):
        return "https://" + url[len("http://"):]
    return url if url.startswith("https://") else ""


def _safe_daum_book_url(value):
    url = _safe_http_url(value)
    parsed = urlparse(url)
    host = (parsed.hostname or "").lower()
    if host != "search.daum.net":
        return ""
    if url.startswith("http://"):
        return "https://" + url[len("http://"):]
    return url if url.startswith("https://") else ""


def _normalize_isbn(values):
    candidates = []
    for value in values or []:
        for part in re.split(r"[,;/()]", str(value)):
            compact = re.sub(r"[^0-9Xx]", "", part).upper()
            if len(compact) in {10, 13} and compact not in candidates:
                candidates.append(compact)

    for length in (13, 10):
        for candidate in candidates:
            if len(candidate) == length and _valid_isbn_checksum(candidate):
                return candidate
    return ""


def _valid_isbn_checksum(isbn):
    if len(isbn) == 13 and isbn.isdigit():
        checksum = sum(
            int(digit) * (1 if index % 2 == 0 else 3)
            for index, digit in enumerate(isbn[:12])
        )
        return (10 - checksum % 10) % 10 == int(isbn[-1])
    if len(isbn) == 10 and isbn[:9].isdigit() and (isbn[-1].isdigit() or isbn[-1] == "X"):
        total = sum((10 - index) * int(digit) for index, digit in enumerate(isbn[:9]))
        total += 10 if isbn[-1] == "X" else int(isbn[-1])
        return total % 11 == 0
    return False


def _issued_year(item):
    for value in _text_values(
        item,
        "DCTERMS_issued",
        "NLON_issuedYear",
        "NLON_datePublished",
        "DCTERMS_created",
    ):
        match = re.search(r"(?:19|20)\d{2}", value)
        if match:
            return int(match.group(0))
    return None


def _is_general_book(item, book):
    if not book.get("title") or not book.get("isbn"):
        return False

    bibliographic_id = str(book.get("bibliographic_id") or "").upper()
    if bibliographic_id.startswith("KDM"):
        return False

    degree_values = _text_values(item, "BIBO_degree", "NLON_degreeYear", "NLON_department")
    if degree_values:
        return False

    type_values = [value.lower() for value in _text_values(item, "RDF_type")]
    if not any(value.rstrip("/").endswith("/book") for value in type_values):
        return False

    title = str(book.get("title") or "")
    thesis_markers = ("학위논문", "학위 청구", "석사학위", "박사학위")
    if any(marker in title for marker in thesis_markers):
        return False
    non_reading_markers = (
        "교과서", "지도서", "문제집", "수험서", "정답과 해설",
        "연구보고서", "연구 보고서", "교육과정 개발", "에 관한 연구",
    )
    if any(marker in title for marker in non_reading_markers):
        return False
    return True


def _is_recent_book(book, reference_year=None):
    issued_year = book.get("issued_year")
    if not isinstance(issued_year, int):
        return False
    current_year = reference_year or timezone.localdate().year
    return current_year - MAX_BOOK_AGE_YEARS <= issued_year <= current_year + 1


def _personalization_tokens(keyword, basis_values, content_terms=None):
    raw_values = [keyword, *(content_terms or []), *(basis_values or [])]
    stopwords = {
        "추천", "도서", "책", "입문", "실용", "교양", "오늘", "기반",
        "관련", "위한", "좋은", "읽기", "소설", "에세이",
    }
    tokens = []
    for value in raw_values:
        cleaned = re.sub(r"[^0-9A-Za-z가-힣\s]", " ", str(value or "")).lower()
        for token in cleaned.split():
            if len(token) >= 2 and token not in stopwords and token not in tokens:
                tokens.append(token)
    return tokens[:12]


def _expanded_basis_tokens(basis_values):
    tokens = _personalization_tokens("", basis_values)
    expanded = list(tokens)
    for token in tokens:
        for source, related in BASIS_TOKEN_ALIASES.items():
            if source not in token and token not in source:
                continue
            for value in related:
                if value not in expanded:
                    expanded.append(value)
    return set(expanded)


def _clean_kakao_text(value):
    text = html.unescape(str(value or ""))
    text = re.sub(r"<[^>]+>", "", text)
    return re.sub(r"\s+", " ", text).strip()


def _clean_string_list(values):
    if not isinstance(values, (list, tuple)):
        values = [values] if values else []
    cleaned = []
    for value in values:
        text = _clean_kakao_text(value)
        if text and text not in cleaned:
            cleaned.append(text)
    return cleaned


def _safe_int(value):
    try:
        return int(value)
    except (TypeError, ValueError):
        return 0


def _kakao_search_queries(keyword, *, search_terms=None, basis_values=None, content_terms=None):
    queries = []
    for value in [*(search_terms or []), keyword, *(basis_values or []), *(content_terms or [])]:
        cleaned = _clean_keyword(value)
        if cleaned and cleaned not in queries:
            queries.append(cleaned)
    return queries[:8]


def _rank_kakao_books(
    books,
    *,
    keyword,
    basis_values,
    content_terms=None,
    search_terms=None,
    theme_id="",
):
    tokens = _personalization_tokens(
        keyword,
        [*(basis_values or []), *(search_terms or [])],
        content_terms,
    )
    expanded_basis = _expanded_basis_tokens(basis_values)
    tokens = list(dict.fromkeys([*tokens, *sorted(expanded_basis)]))[:24]
    ranked = []
    current_year = timezone.localdate().year

    for book in books:
        title = str(book.get("title") or "").lower()
        description = str(book.get("description") or "").lower()
        people_and_publisher = " ".join([
            str(book.get("author") or ""),
            " ".join(book.get("translators") or []),
            str(book.get("publisher") or ""),
        ]).lower()
        score = max(0.0, 18.0 - book.get("query_index", 0) * 3.0)
        score += max(0.0, 6.0 - book.get("result_index", 0) * 0.25)
        matches = []
        for token in tokens:
            token_score = 0.0
            if token in title:
                token_score += 9.0
            if token in description:
                token_score += 5.0
            if token in people_and_publisher:
                token_score += 1.5
            if token_score:
                matches.append(token)
                score += token_score

        if book.get("description"):
            score += 3.0
        if book.get("isbn"):
            score += 2.0
        if book.get("image"):
            score += 1.0
        if str(book.get("status") or "").strip() in {"정상판매", "판매중"}:
            score += 1.0
        issued_year = book.get("issued_year")
        if isinstance(issued_year, int):
            score += max(0.0, 3.0 - max(0, current_year - issued_year) / 10)

        book["personalization_score"] = round(score, 2)
        book["match_terms"] = list(dict.fromkeys(matches))
        book["basis_match_terms"] = sorted(expanded_basis.intersection(matches))
        ranked.append(book)

    return sorted(
        ranked,
        key=lambda book: (
            -book.get("personalization_score", 0),
            book.get("query_index", 0),
            book.get("result_index", 0),
            book.get("title") or "",
        ),
    )


def _rank_personalized_books(
    books,
    *,
    keyword,
    basis_values,
    theme_id,
    content_terms=None,
):
    tokens = _personalization_tokens(keyword, basis_values, content_terms)
    basis_tokens = _expanded_basis_tokens(basis_values)
    tokens = list(dict.fromkeys([*sorted(basis_tokens), *tokens]))[:20]
    content_intent_tokens = set(_personalization_tokens("", [], content_terms))
    intent_tokens = set(_personalization_tokens(keyword, [], content_terms))
    primary_basis_values = [
        value
        for value in basis_values
        if _expanded_basis_tokens([value]).intersection(intent_tokens)
    ]
    primary_basis_tokens = set()
    for value in primary_basis_values:
        primary_basis_tokens.update(_expanded_basis_tokens([value]))
    current_year = time.localtime().tm_year
    ranked = []
    for book in books:
        title = str(book.get("title") or "").lower()
        subjects = " ".join(book.get("subjects") or []).lower()
        description = str(book.get("description") or "").lower()
        matches = []
        semantic_matches = []
        basis_metadata_matches = []
        score = 0.0
        content_match_score = 0.0
        for token in tokens:
            token_score = 0
            if token in title:
                token_score += 3
            if token in subjects:
                token_score += 12
                content_match_score += 12
                semantic_matches.append(token)
                if token in basis_tokens:
                    basis_metadata_matches.append(token)
            if token in description:
                token_score += 9
                content_match_score += 9
                if token not in semantic_matches:
                    semantic_matches.append(token)
                if token in basis_tokens and token not in basis_metadata_matches:
                    basis_metadata_matches.append(token)
            if token_score:
                matches.append(token)
                score += token_score * (2 if token in basis_tokens else 1)

        issued_year = book.get("issued_year")
        if isinstance(issued_year, int):
            age = max(0, current_year - issued_year)
            score += max(0, 8 - age / 5)
        if book.get("description"):
            score += 1
        if len(book.get("isbn") or "") == 13:
            score += 1

        if theme_id == "hobbies" and any(
            marker in f"{title} {subjects}"
            for marker in (
                "방법", "기술", "가이드", "레시피", "배우", "연습", "활용",
                "촬영", "스타일링", "사진책", "입문", "기초", "교본", "안내서", "렌즈",
            )
        ):
            score += 8
        if theme_id == "hobbies" and any(
            marker in f"{title} {subjects}"
            for marker in ("측량", "탐측", "창립", "기념", "교육과정", "교재")
        ):
            score -= 6
        if theme_id == "emotion" and any(
            marker in f"{title} {subjects}"
            for marker in ("위로", "회복", "행복", "감정", "휴식", "치유")
        ):
            score += 2

        book["personalization_score"] = round(score, 2)
        book["content_match_score"] = round(content_match_score, 2)
        book["match_terms"] = matches
        book["semantic_match_terms"] = semantic_matches
        book["basis_match_terms"] = sorted(basis_tokens.intersection(matches))
        book["basis_metadata_match_terms"] = sorted(set(basis_metadata_matches))
        book["primary_basis_match_terms"] = sorted(
            primary_basis_tokens.intersection(matches)
        )
        book["primary_basis_metadata_match_terms"] = sorted(
            primary_basis_tokens.intersection(basis_metadata_matches)
        )
        book["content_intent_match_terms"] = sorted(
            content_intent_tokens.intersection(semantic_matches)
        )
        ranked.append(book)

    if tokens:
        if theme_id in {"interests", "hobbies"} and basis_tokens:
            required_match_field = (
                "primary_basis_match_terms"
                if primary_basis_tokens
                else "basis_match_terms"
            )
            metadata_match_field = (
                "primary_basis_metadata_match_terms"
                if primary_basis_tokens
                else "basis_metadata_match_terms"
            )
            # Prefer candidates whose standardized subject/abstract metadata
            # confirms the topic. Fall back to a title match only when the API
            # returned no metadata-confirmed candidate at all.
            if any(book.get(metadata_match_field) for book in ranked):
                ranked = [book for book in ranked if book.get(metadata_match_field)]
            else:
                ranked = [book for book in ranked if book.get(required_match_field)]
        else:
            ranked = [
                book
                for book in ranked
                if book.get("basis_match_terms")
                or book.get("content_intent_match_terms")
            ]

    return sorted(
        ranked,
        key=lambda book: (
            -book.get("personalization_score", 0),
            -(book.get("issued_year") or 0),
            book.get("title") or "",
        ),
    )


def _join_values(values):
    if not values:
        return ""
    if isinstance(values, str):
        return values
    return ", ".join(str(value) for value in values if value)


def _clean_keyword(value):
    keyword = re.sub(r"\s+", " ", str(value or "")).strip()
    keyword = keyword.strip("\"'`.,")
    if not keyword:
        return ""
    return " ".join(keyword.split()[:5])


def _clean_content_terms(values, fallback_keyword=""):
    if isinstance(values, str):
        values = re.split(r"[,/|\n]", values)
    if not isinstance(values, (list, tuple)):
        values = []

    terms = []
    for value in values:
        cleaned = _clean_keyword(value)
        cleaned = " ".join(cleaned.split()[:3])
        if cleaned and cleaned not in terms:
            terms.append(cleaned)

    if len(terms) < 2:
        for term in _nlk_search_terms(fallback_keyword):
            if term not in terms:
                terms.append(term)
            if len(terms) >= 2:
                break
    return terms[:4]


def _find_candidate(candidates, candidate_id):
    if not candidate_id:
        return None
    return next(
        (book for book in candidates if book.get("candidate_id") == candidate_id),
        None,
    )


def _parse_review_result(raw_result):
    text = str(raw_result or "").strip()
    candidate_match = re.search(r"candidate_id\s*:\s*([A-Za-z0-9_-]+)", text)
    genre_match = re.search(r"genre\s*:\s*(.+?)(?:\nreview\s*:|$)", text, re.DOTALL)
    review_match = re.search(r"review\s*:\s*(.+)", text, re.DOTALL)

    candidate_id = candidate_match.group(1).strip() if candidate_match else ""
    genre = _clean_genre(genre_match.group(1)) if genre_match else ""
    review = review_match.group(1).strip() if review_match else text
    review = re.sub(r"^```(?:text)?\s*|\s*```$", "", review).strip()
    return candidate_id, genre, review


def _clean_genre(value):
    genre = re.sub(r"\s+", " ", str(value or "")).strip()
    genre = genre.strip("\"'`.,:-")
    return " ".join(genre.split()[:2])[:12]


def _infer_genre(book, theme):
    text = " ".join([
        str(theme.get("keyword") or ""),
        str(book.get("title") or ""),
        str(book.get("description") or ""),
    ])
    genre_rules = [
        ("만화", ("만화", "그래픽노블", "웹툰")),
        ("소설", ("소설", "장편", "단편", "문학")),
        ("시", ("시집", "시 ")),
        ("심리", ("심리", "마음", "감정")),
        ("인문", ("인문", "철학", "역사", "사회")),
        ("실용서", ("실용", "레시피", "요리", "가이드", "매뉴얼", "입문")),
        ("예술서", ("예술", "사진", "미술", "영화", "음악")),
        ("자기계발", ("자기계발", "커리어", "습관", "성장")),
        ("에세이", ("에세이", "산문")),
    ]
    for genre, keywords in genre_rules:
        if any(keyword in text for keyword in keywords):
            return genre
    return "도서"


def _compose_fallback_review(theme, book):
    title = book.get("title") or "이 책"
    description = book.get("description") or ""
    description_sentence = (
        f"책 소개에서 전해지는 '{description[:80]}'의 결은 읽기 전부터 차분한 기대를 남깁니다. "
        if description
        else ""
    )
    return (
        f"{title}은 지금 펼쳐 들었을 때 부담 없이 호흡을 맞추기 좋은 책입니다. "
        f"{description_sentence}"
        "선명한 메시지를 앞세우기보다 읽는 사람이 자기 속도대로 문장을 따라가게 하는 점이 매력입니다. "
        "읽고 난 뒤에는 마음에 남은 장면이나 문장을 오래 곱씹게 만드는 추천입니다."
    )

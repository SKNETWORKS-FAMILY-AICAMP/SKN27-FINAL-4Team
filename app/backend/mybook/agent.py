import json
import os
import re
from concurrent.futures import ThreadPoolExecutor, as_completed
from functools import lru_cache

from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate

from .constants import (
    EMOTION_SEARCH_MARKERS,
    FALLBACK_KEYWORDS,
    FALLBACK_CONTENT_TERMS,
    GENRE_RULES,
    KAKAO_API_KEY_ENV_VARS,
    KAKAO_BOOK_PAGE_SIZE,
    KAKAO_BOOK_PROVIDER_INFO,
    KAKAO_BOOK_QUERY_LIMIT,
    POSITIVE_EMOTION_LABELS,
    PROFILE_TOPIC_THEME_IDS,
    REJECTED_KAKAO_TITLE_MARKERS,
    RECOMMENDATION_ENGINE_VERSION,
    RECOMMENDATION_HISTORY_LIMIT,
    THEME_DEFINITIONS,
    THEME_SEARCH_GUIDES,
    VISIBLE_DATA_BLOCKED_PATTERNS,
)
from .exceptions import BookRecommendationUnavailable
from .services.catalog_service import (
    request_kakao_book_search as _request_kakao_book_search,
)
from .services.ranking_service import (
    rank_kakao_books as _rank_kakao_books_service,
)
from .utils import (
    _book_search_terms,
    _clean_content_terms,
    _clean_kakao_text,
    _clean_keyword,
    _clean_string_list,
    _daum_book_search_url,
    _expanded_basis_tokens,
    _is_safe_book_candidate,
    _kakao_search_queries,
    _normalize_book_author,
    _normalize_book_title,
    _normalize_isbn,
    _personalization_tokens,
    _safe_daum_book_url,
    _safe_external_cover_url,
    _safe_int,
    _without_excluded_books,
)


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

        history = BookRecommendationAgent._rotation_history(cached_data)
        previous_basis = {
            theme_id: values[-1]
            for theme_id, values in history["selected_basis"].items()
            if values
        }
        themes = BookRecommendationAgent._build_themes(user_profile, previous_basis)
        supplied_exclusions = excluded_isbns if isinstance(excluded_isbns, dict) else {}
        excluded_by_theme = {}
        for theme_id in (definition["id"] for definition in THEME_DEFINITIONS):
            excluded_by_theme[theme_id] = list(dict.fromkeys([
                *(history["isbns"].get(theme_id) or []),
                *(supplied_exclusions.get(theme_id) or []),
            ]))[-RECOMMENDATION_HISTORY_LIMIT:]
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
                theme["search_terms"] = cached_theme_info.get("search_terms", theme.get("search_terms", []))
                theme["content_terms"] = cached_theme_info.get("content_terms", theme.get("content_terms", []))
                theme["selected_basis"] = cached_theme_info.get("selected_basis", theme.get("selected_basis", ""))
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
                errors = []
                for future in as_completed(future_to_theme):
                    t = future_to_theme[future]
                    try:
                        future.result()
                    except Exception as exc:
                        print(f"[BookAgent] Theme {t['id']} candidate search failed: {exc}")
                        t["candidates"] = []
                        t["error"] = str(exc)
                        errors.append(exc)

                missing_themes = [
                    theme for theme in themes_to_process if not theme.get("candidates")
                ]
                if missing_themes:
                    missing_ids = ", ".join(theme["id"] for theme in missing_themes)
                    if errors:
                        raise BookRecommendationUnavailable(
                            f"책 후보 검색에 실패했습니다: {missing_ids}",
                            code="BOOK_CANDIDATE_SEARCH_FAILED",
                        ) from errors[0]
                    raise BookRecommendationUnavailable(
                        f"일반 단행본 후보를 찾지 못했습니다: {missing_ids}",
                        code="GENERAL_BOOK_CANDIDATES_NOT_FOUND",
                    )

        books = BookRecommendationAgent._generate_reviews(user_profile, themes, cached_books=cached_books)
        history = BookRecommendationAgent._updated_rotation_history(history, themes, books)

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
                "adult_content_filter": "제목·책 소개의 성인 등급 및 유해 의심 신호를 후보·캐시·최종 선택 단계에서 차단",
                "profile_topic_relevance": "선택된 관심사·취미가 제목 또는 책 소개에서 직접 확인되는 후보만 허용",
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
            "recommendation_history": history,
            "source_disclosure": {
                "book_metadata": "Kakao Daum 책 검색",
                "cover_metadata": "Kakao Daum 책 검색 표지",
                "curation": "OpenAI를 이용해 생성한 맞춤 추천 AI 추천사",
                "display_policy": "도서 검색 결과와 AI 생성 추천을 구분해 표시합니다.",
                "providers": [KAKAO_BOOK_PROVIDER_INFO],
            },
        }

    @staticmethod
    def _rotation_history(cached_data):
        history = {
            "selected_basis": {theme_id: [] for theme_id in ("interests", "hobbies")},
            "isbns": {definition["id"]: [] for definition in THEME_DEFINITIONS},
        }
        if not isinstance(cached_data, dict):
            return history

        raw_history = cached_data.get("recommendation_history") or {}
        for theme_id in history["selected_basis"]:
            values = (raw_history.get("selected_basis") or {}).get(theme_id) or []
            history["selected_basis"][theme_id] = [
                str(value).strip() for value in values if str(value).strip()
            ][-RECOMMENDATION_HISTORY_LIMIT:]
        for theme_id in history["isbns"]:
            values = (raw_history.get("isbns") or {}).get(theme_id) or []
            history["isbns"][theme_id] = list(dict.fromkeys(
                _normalize_isbn([value]) for value in values if _normalize_isbn([value])
            ))[-RECOMMENDATION_HISTORY_LIMIT:]

        for theme in cached_data.get("themes") or []:
            theme_id = str(theme.get("id") or "") if isinstance(theme, dict) else ""
            selected = str(theme.get("selected_basis") or "").strip() if isinstance(theme, dict) else ""
            if theme_id in history["selected_basis"] and selected:
                values = history["selected_basis"][theme_id]
                if not values or values[-1] != selected:
                    values.append(selected)
                    del values[:-RECOMMENDATION_HISTORY_LIMIT]
        for book in cached_data.get("books") or []:
            if not isinstance(book, dict):
                continue
            theme_id = str(book.get("theme_id") or "")
            isbn = _normalize_isbn([book.get("isbn")])
            if theme_id in history["isbns"] and isbn and isbn not in history["isbns"][theme_id]:
                history["isbns"][theme_id].append(isbn)
                del history["isbns"][theme_id][:-RECOMMENDATION_HISTORY_LIMIT]
        return history

    @staticmethod
    def _updated_rotation_history(history, themes, books):
        for theme in themes:
            theme_id = theme.get("id")
            selected = str(theme.get("selected_basis") or "").strip()
            if theme_id in history["selected_basis"] and selected:
                values = history["selected_basis"][theme_id]
                if not values or values[-1] != selected:
                    values.append(selected)
                    del values[:-RECOMMENDATION_HISTORY_LIMIT]
        for book in books:
            theme_id = book.get("theme_id")
            isbn = _normalize_isbn([book.get("isbn")])
            if theme_id in history["isbns"] and isbn and isbn not in history["isbns"][theme_id]:
                history["isbns"][theme_id].append(isbn)
                del history["isbns"][theme_id][:-RECOMMENDATION_HISTORY_LIMIT]
        return history

    @staticmethod
    def _search_theme_candidates(theme):
        ranking_basis_values = theme["basis_values"]
        if theme["id"] in PROFILE_TOPIC_THEME_IDS and theme.get("selected_basis"):
            ranking_basis_values = [theme["selected_basis"]]
        search_options = {
            "display": 8,
            "basis_values": ranking_basis_values,
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
                basis_values=ranking_basis_values,
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
    def _build_themes(user_profile, previous_basis=None):
        previous_basis = previous_basis if isinstance(previous_basis, dict) else {}
        try:
            shared_llm = _get_llm(temperature=0.25, max_tokens=220)
        except Exception:
            # 기존 테마별 폴백 경로가 인증 설정 오류도 처리하도록 유지한다.
            shared_llm = None

        def build_theme(definition):
            theme_id = definition["id"]
            fallback_keyword, fallback_reason = FALLBACK_KEYWORDS[theme_id]
            basis_values = BookRecommendationAgent._basis_values(
                user_profile,
                definition["basis_key"],
            )
            required_basis = BookRecommendationAgent._next_profile_basis(
                theme_id,
                basis_values,
                previous_basis.get(theme_id),
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
                    llm=shared_llm,
                    required_basis=required_basis,
                ),
            }

        with ThreadPoolExecutor(max_workers=len(THEME_DEFINITIONS)) as executor:
            return list(executor.map(build_theme, THEME_DEFINITIONS))

    @staticmethod
    def _build_search_intent(
        user_profile,
        definition,
        basis_values,
        fallback_keyword,
        fallback_reason,
        llm=None,
        required_basis="",
    ):
        try:
            response = (llm or _get_llm(temperature=0.25, max_tokens=220)).invoke([
                (
                    "system",
                    "당신은 책 제목의 문구가 아니라 책이 실제로 다루는 내용을 기준으로 "
                    "개인 맞춤 Kakao Daum 도서 검색어를 설계하는 큐레이터입니다. "
                    "온라인 서점 검색에서 실제 책 후보가 충분히 나오는 한국어 검색어와 추천 의도를 JSON으로만 작성하세요.",
                ),
                (
                    "user",
                    BookRecommendationAgent._keyword_prompt(
                        user_profile,
                        definition,
                        basis_values,
                        required_basis=required_basis,
                    ),
                ),
            ])
            data = BookRecommendationAgent._parse_json(response.content)
            keyword = _clean_keyword(data.get("keyword"))
            selected_basis = required_basis or BookRecommendationAgent._selected_basis_value(
                data.get("selected_basis"), basis_values,
            )
            content_terms = _clean_content_terms(data.get("content_terms"), keyword)
            keyword, content_terms = BookRecommendationAgent._anchor_profile_topic(
                definition["id"],
                keyword,
                content_terms,
                selected_basis,
            )
            if definition["id"] == "emotion":
                keyword, content_terms, raw_search_terms = (
                    BookRecommendationAgent._sanitize_emotion_search_intent(
                        keyword,
                        content_terms,
                        data.get("search_terms"),
                        basis_values,
                    )
                )
                search_terms = _book_search_terms(
                    raw_search_terms,
                    selected_basis="",
                    keyword=keyword,
                )
            else:
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
        selected_basis = required_basis or (
            str(basis_values[0]).strip() if basis_values else ""
        )
        fallback_content_terms = BookRecommendationAgent._fallback_content_terms(
            definition["id"],
            basis_values,
            fallback_keyword,
        )
        search_term_basis = selected_basis
        if definition["id"] == "emotion":
            keyword, fallback_content_terms, fallback_search_terms = (
                BookRecommendationAgent._sanitize_emotion_search_intent(
                    keyword,
                    fallback_content_terms,
                    [],
                    basis_values,
                )
            )
            search_term_basis = ""
        else:
            fallback_search_terms = []
        return {
            "keyword": keyword,
            "content_terms": fallback_content_terms,
            "search_terms": _book_search_terms(
                fallback_search_terms,
                selected_basis=search_term_basis,
                keyword=keyword,
            ),
            "selected_basis": selected_basis,
            "reason": fallback_reason,
            "keyword_basis": definition["basis_label"],
        }

    @staticmethod
    def _selected_basis_value(value, basis_values):
        available = [str(item).strip() for item in basis_values if str(item).strip()]
        requested = str(value or "").strip()
        return next((item for item in available if item == requested), available[0] if available else "")

    @staticmethod
    def _next_profile_basis(theme_id, basis_values, previous_basis):
        available = [str(item).strip() for item in basis_values if str(item).strip()]
        if theme_id not in PROFILE_TOPIC_THEME_IDS or not available:
            return ""
        previous = str(previous_basis or "").strip()
        if previous not in available:
            return available[0]
        return available[(available.index(previous) + 1) % len(available)]

    @staticmethod
    def _emotion_is_positive(basis_values):
        values = {str(value).strip().lower() for value in basis_values if str(value).strip()}
        return bool(values & {label.lower() for label in POSITIVE_EMOTION_LABELS})

    @staticmethod
    def _emotion_reading_goal(basis_values):
        if BookRecommendationAgent._emotion_is_positive(basis_values):
            return "긍정적인 상태를 자연스럽게 유지·확장하는 몰입, 유머, 성취, 발견의 독서 경험"
        return "무거운 상태를 직접 분석하지 않고 긴장을 덜어 환기·회복을 돕는 독서 경험"

    @staticmethod
    def _sanitize_emotion_search_intent(keyword, content_terms, search_terms, basis_values):
        emotion_labels = list(dict.fromkeys([
            *(str(value).strip() for value in basis_values if str(value).strip()),
            *EMOTION_SEARCH_MARKERS,
        ]))

        def without_labels(value):
            cleaned = str(value or "")
            for label in emotion_labels:
                cleaned = re.sub(
                    rf"{re.escape(label)}(?:으로|에서|에게|처럼|보다|까지|부터|을|를|이|가|은|는|의|과|와|로)?",
                    " ",
                    cleaned,
                    flags=re.IGNORECASE,
                )
            cleaned = re.sub(r"\s+", " ", cleaned).strip(" ,-/")
            return re.sub(
                r"^(?:(?:(?:더|더욱)\s*)?깊게\s+만드는|더하는|유지하는|이어가는|해소하는|달래는|회복하는)\s+",
                "",
                cleaned,
            ).strip()

        positive = BookRecommendationAgent._emotion_is_positive(basis_values)
        fallback_keyword = "몰입 성장 소설" if positive else "마음 환기 소설"
        cleaned_keyword = _clean_keyword(without_labels(keyword)) or fallback_keyword
        cleaned_content = [without_labels(value) for value in content_terms or []]
        cleaned_search = [without_labels(value) for value in search_terms or []]
        goal_terms = (
            ["몰입", "일상 활력", "유머", "성취"]
            if positive
            else ["마음 환기", "긴장 완화", "회복", "휴식"]
        )
        cleaned_content = _clean_content_terms(
            [*cleaned_content, *goal_terms],
            cleaned_keyword,
        )
        cleaned_search = [value for value in cleaned_search if value]
        if not cleaned_search:
            cleaned_search = goal_terms[:3]
        return cleaned_keyword, cleaned_content, cleaned_search

    @staticmethod
    def _anchor_profile_topic(theme_id, keyword, content_terms, selected_basis):
        """Keep an interest/hobby label visible in the actual catalog queries."""
        if theme_id not in PROFILE_TOPIC_THEME_IDS or not selected_basis:
            return keyword, content_terms

        anchored_keyword = keyword
        if selected_basis not in keyword:
            anchored_keyword = _clean_keyword(f"{selected_basis} {keyword}")

        anchored_terms = list(content_terms or [])
        if not any(selected_basis in term for term in anchored_terms):
            anchored_terms.insert(0, selected_basis)
        return anchored_keyword, _clean_content_terms(anchored_terms, anchored_keyword)

    @staticmethod
    def _keyword_prompt(user_profile, definition, basis_values, required_basis=""):
        basis_text = ", ".join(str(value) for value in basis_values if str(value).strip()) or "미상"
        rotation_rule = (
            f"- 이번 회차 고정 주제: {required_basis}\n"
            f"- selected_basis는 반드시 '{required_basis}'로 출력하고 다른 프로필 주제를 섞지 마세요.\n"
            if required_basis else ""
        )
        emotion_goal = (
            f"- 감정 독서 목표: {BookRecommendationAgent._emotion_reading_goal(basis_values)}\n"
            "- 핵심 값의 감정 단어를 keyword·search_terms·content_terms에 그대로 쓰지 마세요. 감정과 같은 제목을 찾는 것이 아닙니다.\n"
            if definition["id"] == "emotion" else ""
        )
        return f"""
[추천 유형]
- id: {definition['id']}
- 이름: {definition['name']}
- 핵심 기준: {definition['basis_label']}
- 핵심 값: {basis_text}
{rotation_rule}{emotion_goal}

[해야 할 일]
{THEME_SEARCH_GUIDES.get(definition['id'], '핵심 기준을 읽고 책 검색어를 만드세요.')}

[검색 키워드 작성 규칙]
- search_terms는 Kakao Daum 책 검색 API에 각각 독립적으로 넣을 탐색어입니다. 문장이나 가상의 책 제목이 아니라 실제 온라인 서점에서 관련 책을 찾기 좋은 1~4어절의 한국어 검색어로 작성하세요.
- 관심사·취미 유형에서는 지정된 이번 회차 고정 주제 하나만 selected_basis로 사용하세요. selected_basis는 반드시 입력된 핵심 값의 원문과 완전히 같아야 합니다.
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
            return (
                "몰입 성장 소설"
                if BookRecommendationAgent._emotion_is_positive(values)
                else "마음 환기 소설"
            )
        if theme_id == "interests":
            return " ".join(values[:2])
        if theme_id == "hobbies":
            return f"{' '.join(values[:2])} 실용"
        return " ".join(values[:2]) or fallback_keyword

    @staticmethod
    def _fallback_content_terms(theme_id, basis_values, fallback_keyword):
        values = [str(value).strip() for value in basis_values if str(value).strip()]
        return _clean_content_terms(
            [*values[:2], *FALLBACK_CONTENT_TERMS.get(theme_id, ()), fallback_keyword],
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
                    or any(marker in book["title"] for marker in REJECTED_KAKAO_TITLE_MARKERS)
                    or not _is_safe_book_candidate(book)
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
    def _generate_reviews(user_profile, themes, cached_books=None):
        if cached_books is None:
            cached_books = {}

        results = [None] * len(themes)
        try:
            shared_llm = _get_llm(temperature=0.45, max_tokens=360)
        except Exception:
            # 각 테마 처리에서 기존 오류 코드로 변환되도록 한다.
            shared_llm = None

        def process_theme(index, theme):
            theme_id = theme["id"]
            if theme.get("skip_process") and theme_id in cached_books:
                return index, cached_books[theme_id]

            if not theme.get("candidates"):
                raise BookRecommendationUnavailable(
                    f"{theme_id} 추천에 사용할 실제 책 후보가 없습니다.",
                    code="GENERAL_BOOK_CANDIDATES_NOT_FOUND",
                )

            try:
                return index, BookRecommendationAgent._generate_single_review(
                    user_profile,
                    theme,
                    llm=shared_llm,
                )
            except Exception as exc:
                print(f"[BookAgent] Review generation failed for {theme['id']}: {exc}")
                if isinstance(exc, BookRecommendationUnavailable):
                    raise
                raise BookRecommendationUnavailable(
                    f"{theme_id} 추천 서평을 생성하지 못했습니다.",
                    code="BOOK_REVIEW_GENERATION_FAILED",
                ) from exc

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
    def _generate_single_review(user_profile, theme, llm=None):
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
            | (llm or _get_llm(temperature=0.45, max_tokens=360))
            | StrOutputParser()
        )
        raw_result = chain.invoke({})
        selected_id, genre, review = _parse_review_result(raw_result)
        selected_book = _find_candidate(theme["candidates"], selected_id)
        if selected_book is None:
            raise BookRecommendationUnavailable(
                "AI가 실제 후보 목록에 없는 책을 선택했습니다.",
                code="BOOK_REVIEW_INVALID_SELECTION",
            )
        if not _is_safe_book_candidate(selected_book):
            raise BookRecommendationUnavailable(
                "성인·유해 콘텐츠 가능성이 있는 도서는 추천할 수 없습니다.",
                code="BOOK_UNSAFE_SELECTION",
            )
        if not review:
            raise BookRecommendationUnavailable(
                "AI 추천 서평이 비어 있습니다.",
                code="BOOK_REVIEW_EMPTY",
            )

        return BookRecommendationAgent._book_payload(
            theme,
            selected_book,
            review,
            genre=genre,
        )

    @staticmethod
    def _single_review_prompt(user_profile, theme):
        basis_text = ", ".join(theme["basis_values"]) or "미상"
        emotion_selection_rule = ""
        if theme.get("id") == "emotion":
            emotion_selection_rule = (
                "\n- 감정 독서 목표: "
                f"{BookRecommendationAgent._emotion_reading_goal(theme.get('basis_values') or [])}\n"
                "- 제목에 감정 단어가 포함된 후보도 제외하지 마세요.\n"
                "- 단, 제목 일치만으로 고르지 말고 책 소개, 저자, 출판사, 주제와 서지정보를 비교해 위 목표에 가장 잘 맞는 책을 고르세요.\n"
                "- 성인 전용, 19금, 고수위, 성애·에로틱 콘텐츠가 조금이라도 의심되는 후보는 절대 고르지 마세요.\n"
            )
        topic_selection_rule = ""
        if theme.get("id") in PROFILE_TOPIC_THEME_IDS:
            selected_basis = str(theme.get("selected_basis") or basis_text).strip()
            topic_selection_rule = (
                f"\n- 이번 추천의 단일 고정 주제는 '{selected_basis}'입니다.\n"
                "- 책 소개에서 이 주제·직접 동의어 또는 이 주제에만 속하는 구체적 하위 개념이 핵심 내용으로 확인되는 후보만 고르세요. "
                "검색 결과에 함께 나왔다는 이유나 분위기·라이프스타일 같은 간접 연결만으로 고르면 안 됩니다.\n"
            )
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
{emotion_selection_rule}{topic_selection_rule}

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
모든 유형에서 성인 전용, 19금, 청소년 유해, 고수위, 성애·에로틱 콘텐츠가 명시되거나 의심되는 책은 선택하지 마세요.
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
            "recommendation_basis": _visible_recommendation_basis(theme),
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


@lru_cache(maxsize=8)
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

    return [
        value
        for value in values
        if not any(pattern in value for pattern in VISIBLE_DATA_BLOCKED_PATTERNS)
        and not re.search(r"\d+\s*세", value)
    ][:4]


def _visible_recommendation_basis(theme):
    label = str(
        theme.get("keyword_basis")
        or theme.get("basis_label")
        or "추천 기준"
    ).strip()
    basis_values = [
        str(value).strip()
        for value in theme.get("basis_values") or []
        if str(value).strip()
    ]
    if theme.get("id") == "emotion":
        value = basis_values[0] if basis_values else ""
    else:
        value = str(theme.get("selected_basis") or "").strip()
    return f"{label} · {value}" if value else label


def _kakao_rest_api_key():
    return next(
        (
            os.environ.get(name, "").strip()
            for name in KAKAO_API_KEY_ENV_VARS
            if os.environ.get(name, "").strip()
        ),
        "",
    )






















































def _rank_kakao_books(
    books,
    *,
    keyword,
    basis_values,
    content_terms=None,
    search_terms=None,
    theme_id="",
):
    return _rank_kakao_books_service(
        books,
        keyword=keyword,
        basis_values=basis_values,
        content_terms=content_terms,
        search_terms=search_terms,
        theme_id=theme_id,
        personalization_tokens=_personalization_tokens,
        expanded_basis_tokens=_expanded_basis_tokens,
    )


def _join_values(values):
    if not values:
        return ""
    if isinstance(values, str):
        return values
    return ", ".join(str(value) for value in values if value)


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
    review = review_match.group(1).strip() if review_match else ""
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
    for genre, keywords in GENRE_RULES:
        if any(keyword in text for keyword in keywords):
            return genre
    return "도서"


__all__ = (
    "BookRecommendationAgent",
    "BookRecommendationUnavailable",
    "RECOMMENDATION_ENGINE_VERSION",
)

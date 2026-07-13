import json
import os
import re

import requests
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate


FALLBACK_KEYWORDS = {
    "emotion": ("마음 회복 에세이", "오늘의 정서 흐름을 반영한 추천입니다."),
    "interests": ("교양 입문서", "프로필 관심사를 반영한 추천입니다."),
    "hobbies": ("취미 에세이", "프로필 취미를 반영한 추천입니다."),
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


class BookRecommendationAgent:
    @staticmethod
    def recommend(user_profile):
        themes = BookRecommendationAgent._build_themes(user_profile)

        for theme in themes:
            theme["candidates"] = BookRecommendationAgent._search_naver_books(
                theme["keyword"],
                display=4,
            )
            if not theme["candidates"]:
                fallback_keyword = FALLBACK_KEYWORDS[theme["id"]][0]
                theme["keyword"] = fallback_keyword
                theme["candidates"] = BookRecommendationAgent._search_naver_books(
                    fallback_keyword,
                    display=4,
                )

        books = BookRecommendationAgent._generate_reviews(user_profile, themes)

        return {
            "is_fallback": not bool(books),
            "themes": [
                {
                    "id": theme["id"],
                    "name": theme["name"],
                    "keyword": theme["keyword"],
                    "reason": theme["reason"],
                    "basis_label": theme["basis_label"],
                    "basis_values": theme["basis_values"],
                    "candidate_count": len(theme.get("candidates", [])),
                }
                for theme in themes
            ],
            "books": books,
        }

    @staticmethod
    def _build_themes(user_profile):
        themes = []

        for definition in THEME_DEFINITIONS:
            theme_id = definition["id"]
            fallback_keyword, fallback_reason = FALLBACK_KEYWORDS[theme_id]
            basis_values = BookRecommendationAgent._basis_values(
                user_profile,
                definition["basis_key"],
            )

            themes.append(
                {
                    **definition,
                    "basis_values": basis_values,
                    "keyword": BookRecommendationAgent._search_keyword(
                        theme_id,
                        basis_values,
                        fallback_keyword,
                    ),
                    "reason": fallback_reason,
                }
            )

        return themes

    @staticmethod
    def _search_keyword(theme_id, basis_values, fallback_keyword):
        values = [str(value).strip() for value in basis_values if str(value).strip()]
        if not values:
            return fallback_keyword
        if theme_id == "emotion":
            return f"{values[0]} 마음 에세이"
        if theme_id == "interests":
            return " ".join(values[:2])
        if theme_id == "hobbies":
            return " ".join(values[:2])
        return " ".join(values[:2]) or fallback_keyword

    @staticmethod
    def _search_naver_books(keyword, display=4):
        client_id = (
            os.environ.get("NAVER_BOOK_CLIENT_ID")
            or os.environ.get("NAVER_SEARCH_CLIENT_ID")
            or ""
        ).strip()
        client_secret = (
            os.environ.get("NAVER_BOOK_CLIENT_SECRET")
            or os.environ.get("NAVER_SEARCH_CLIENT_SECRET")
            or ""
        ).strip()
        if not client_id or not client_secret:
            print("[BookAgent] Naver book search API keys are missing.")
            return []

        try:
            response = requests.get(
                "https://openapi.naver.com/v1/search/book.json",
                headers={
                    "X-Naver-Client-Id": client_id,
                    "X-Naver-Client-Secret": client_secret,
                },
                params={"query": keyword, "display": display, "sort": "sim"},
                timeout=5,
            )
            response.raise_for_status()
            return [
                BookRecommendationAgent._normalize_book_item(index, item)
                for index, item in enumerate(response.json().get("items", []), start=1)
            ]
        except Exception as exc:
            print(f"[BookAgent] Naver API search failed for '{keyword}': {exc}")
            return []

    @staticmethod
    def _normalize_book_item(index, item):
        return {
            "candidate_id": f"book_{index}",
            "title": _strip_html(item.get("title", "")),
            "author": _strip_html(item.get("author", "")),
            "publisher": _strip_html(item.get("publisher", "")),
            "description": _strip_html(item.get("description", "")),
            "image": item.get("image", ""),
            "link": item.get("link", ""),
            "isbn": item.get("isbn", ""),
        }

    @staticmethod
    def _generate_reviews(user_profile, themes):
        themes_with_candidates = [theme for theme in themes if theme.get("candidates")]
        if not themes_with_candidates:
            return []

        results = []
        for theme in themes_with_candidates:
            try:
                results.append(BookRecommendationAgent._generate_single_review(user_profile, theme))
            except Exception as exc:
                print(f"[BookAgent] Review generation failed for {theme['id']}: {exc}")
                results.append(BookRecommendationAgent._fallback_review(theme))
        return results

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
        selected_id, review = _parse_review_result(raw_result)
        selected_book = _find_candidate(theme.get("candidates", []), selected_id)
        if selected_book is None:
            selected_book = theme["candidates"][0]

        return BookRecommendationAgent._book_payload(
            theme,
            selected_book,
            review or _compose_fallback_review(theme, selected_book),
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
                f"  출판사: {book['publisher']}\n"
                f"  요약: {book['description'][:120]}"
            )

        return f"""
[사용자 정보]
- 나이: {user_profile.get("age") or "미상"}
- 성별: {user_profile.get("gender") or "미상"}
- 오늘의 주된 감정: {user_profile.get("today_emotion") or "평온"}
- 프로필 관심사: {_join_values(user_profile.get("interests")) or "미상"}
- 프로필 취미: {_join_values(user_profile.get("hobbies")) or "미상"}

[추천 조합]
- 실제 고려 조합: 나이, 성별, {theme['basis_label']}
- 참고 맥락: {theme['basis_label']} {basis_text}

[후보 도서]
{chr(10).join(candidate_lines)}

후보 도서 중 1권을 고르고, 2~3문장의 추천 서평을 작성하세요.
서평은 책 자체의 분위기, 주제, 읽고 난 뒤 남을 감각을 중심으로 자연스럽게 작성하세요.
참고 맥락은 책을 고르고 문장의 톤을 잡는 데만 사용하세요.
서평 본문에 "관심사가 있어서", "검색어", "키워드", "근거", "데이터"처럼 추천 로직이 직접 드러나는 표현을 쓰지 마세요.
후보에 없는 책을 새로 만들면 안 됩니다.

아래 형식만 지키세요.
candidate_id: book_1
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
        )

    @staticmethod
    def _book_payload(theme, book, review):
        return {
            "theme": theme["name"],
            "theme_id": theme["id"],
            "theme_reason": theme.get("reason", ""),
            "keyword": theme.get("keyword", ""),
            "title": book.get("title", ""),
            "author": book.get("author", ""),
            "publisher": book.get("publisher", ""),
            "image": book.get("image", ""),
            "link": book.get("link", ""),
            "isbn": book.get("isbn", ""),
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
    provider = os.environ.get("MYBOOK_LLM_PROVIDER") or os.environ.get("LLM_PROVIDER") or "groq"
    provider = provider.lower().strip()

    if provider == "groq":
        from langchain_groq import ChatGroq

        base_url = (
            os.environ.get("MYBOOK_GROQ_BASE_URL")
            or os.environ.get("GROQ_BASE_URL")
            or ""
        ).strip()
        if base_url:
            base_url = re.sub(r"/openai/v1/?$", "", base_url.rstrip("/"))

        return ChatGroq(
            model=os.environ.get("GROQ_MODEL", "llama-3.1-70b-versatile"),
            temperature=temperature,
            max_tokens=max_tokens,
            api_key=os.environ.get("GROQ_API_KEY"),
            base_url=base_url or None,
        )

    from langchain_openai import ChatOpenAI

    return ChatOpenAI(
        model=os.environ.get("OPENAI_MODEL", "gpt-4o-mini"),
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


def _strip_html(value):
    return re.sub(r"<[^>]+>", "", str(value or "")).strip()


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
    review_match = re.search(r"review\s*:\s*(.+)", text, re.DOTALL)

    candidate_id = candidate_match.group(1).strip() if candidate_match else ""
    review = review_match.group(1).strip() if review_match else text
    review = re.sub(r"^```(?:text)?\s*|\s*```$", "", review).strip()
    return candidate_id, review


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

import json
import os
import re

import requests
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate


FALLBACK_KEYWORDS = {
    "emotion": ("감정 독서 도서", "오늘 감정이 좋다면 유지하고, 무겁다면 덜어내는 독서 방향입니다."),
    "interests": ("관심사 입문 도서", "프로필 관심사 자체를 더 깊이 읽을 수 있는 방향입니다."),
    "hobbies": ("취미 실용 도서", "프로필 취미를 실제로 즐기고 넓히는 방향입니다."),
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
                    "keyword_basis": theme.get("keyword_basis", ""),
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
                    **BookRecommendationAgent._build_search_intent(
                        user_profile,
                        definition,
                        basis_values,
                        fallback_keyword,
                        fallback_reason,
                    ),
                }
            )

        return themes

    @staticmethod
    def _build_search_intent(user_profile, definition, basis_values, fallback_keyword, fallback_reason):
        try:
            response = _get_llm(temperature=0.25, max_tokens=220).invoke([
                (
                    "system",
                    "당신은 개인 맞춤 도서 검색 키워드를 설계하는 큐레이터입니다. "
                    "검색 가능한 한국어 키워드와 추천 의도를 JSON으로만 작성하세요.",
                ),
                ("user", BookRecommendationAgent._keyword_prompt(user_profile, definition, basis_values)),
            ])
            data = BookRecommendationAgent._parse_json(response.content)
            keyword = _clean_keyword(data.get("keyword"))
            reason = str(data.get("reason") or "").strip()
            if keyword:
                return {
                    "keyword": keyword,
                    "reason": reason or fallback_reason,
                    "keyword_basis": f"{definition['basis_label']} + 나이 + 성별",
                }
        except Exception as exc:
            print(f"[BookAgent] Keyword generation failed for {definition['id']}: {exc}")

        return {
            "keyword": BookRecommendationAgent._fallback_search_keyword(
                definition["id"],
                basis_values,
                fallback_keyword,
            ),
            "reason": fallback_reason,
            "keyword_basis": definition["basis_label"],
        }

    @staticmethod
    def _keyword_prompt(user_profile, definition, basis_values):
        basis_text = ", ".join(str(value) for value in basis_values if str(value).strip()) or "미상"
        guide_by_theme = {
            "emotion": (
                "오늘의 주된 감정이 긍정적이면 그 감정을 오래 유지하고 음미할 책, "
                "부정적이면 감정을 안전하게 해소하고 가라앉힐 때 읽을 책 검색어를 만드세요. "
                "마음리포트처럼 원인 분석, 감정 진단, 하루 요약을 하는 방향과 겹치면 안 됩니다."
            ),
            "interests": (
                "프로필 관심사 자체를 실제로 다루는 책 검색어를 만드세요. "
                "관심사를 핑계로 한 힐링/자기계발서가 아니라, 그 분야의 입문서, 교양서, 해설서, 비평서처럼 "
                "관심 대상에 대해 읽을 만한 책을 찾는 방향이어야 합니다."
            ),
            "hobbies": (
                "프로필 취미를 실제 취미 관점에서 다루는 책 검색어를 만드세요. "
                "취미를 소재로 한 감성 에세이에 치우치지 말고, 방법, 기술, 작품 감상, 역사, 도구, 루틴처럼 "
                "그 취미를 더 잘 즐기거나 넓힐 수 있는 책을 찾는 방향이어야 합니다."
            ),
        }
        return f"""
[추천 유형]
- id: {definition['id']}
- 이름: {definition['name']}
- 핵심 기준: {definition['basis_label']}
- 핵심 값: {basis_text}

[사용자 맥락]
- 나이: {user_profile.get("age") or "미상"}
- 성별: {user_profile.get("gender") or "미상"}

[해야 할 일]
{guide_by_theme.get(definition['id'], '핵심 기준, 나이, 성별을 함께 읽고 책 검색어를 만드세요.')}

[검색 키워드 작성 규칙]
- 네이버 도서 검색에 바로 넣을 수 있는 한국어 검색어 1개만 만드세요.
- 검색어는 2~5개 단어로 짧게 작성하세요.
- 책 장르나 독서 목적이 드러나게 만드세요. 단, 에세이로 고정하지 마세요.
- 후보 장르는 소설, 인문, 심리, 교양, 실용서, 예술서, 만화, 자기계발, 에세이 중 맥락에 맞게 고르세요.
- 예: 마음 회복 소설, 커리어 인문학, 사진 실용서, 영화 심리 교양, 요리 레시피북.
- 감정 추천 검색어는 감정 유지/해소를 위한 독서 경험에 집중하고, 마음리포트·감정분석·자가진단처럼 보이는 단어는 피하세요.
- 관심사 추천 검색어는 관심사 명칭이 핵심 주제로 드러나야 하며, 막연한 위로/힐링 도서로 바꾸지 마세요.
- 취미 추천 검색어는 취미 활동을 직접 다루는 실용/입문/감상/역사/기술 맥락을 우선하세요.
- 나이와 성별은 검색 방향을 미세 조정하는 데만 사용하고, 성별 고정관념으로 장르를 단정하지 마세요.
- 사용자의 나이/성별을 이유 문장에 직접 노출하지 마세요.

아래 JSON만 출력하세요.
{{
  "keyword": "도서 검색 키워드",
  "reason": "이 기준으로 검색어를 만든 이유를 45자 안팎으로 설명",
  "keyword_basis": "{definition['basis_label']} + 나이 + 성별"
}}
""".strip()

    @staticmethod
    def _fallback_search_keyword(theme_id, basis_values, fallback_keyword):
        values = [str(value).strip() for value in basis_values if str(value).strip()]
        if not values:
            return fallback_keyword
        if theme_id == "emotion":
            return f"{values[0]} 마음 도서"
        if theme_id == "interests":
            return f"{' '.join(values[:2])} 추천 도서"
        if theme_id == "hobbies":
            return f"{' '.join(values[:2])} 실용 도서"
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
        selected_id, genre, review = _parse_review_result(raw_result)
        selected_book = _find_candidate(theme.get("candidates", []), selected_id)
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
- 검색 키워드: {theme.get('keyword') or '미상'}
- 검색 키워드 생성 의도: {theme.get('reason') or '사용자 맥락에 맞는 책 후보를 찾기 위한 검색어입니다.'}

[후보 도서]
{chr(10).join(candidate_lines)}

후보 도서 중 1권을 고르고, 2~3문장의 추천 서평을 작성하세요.
서평은 이 책을 고른 이유가 분명히 느껴지도록, 책의 주제/분위기/현재 맥락과 맞는 지점을 자연스럽게 포함하세요.
참고 맥락은 책을 고르고 문장의 톤을 잡는 데 사용하세요.
유형별 기준을 반드시 지키세요.
- 감정 추천: 오늘의 감정이 기쁨, 평온, 만족, 설렘처럼 긍정적이면 그 감정을 유지하거나 더 선명하게 느끼게 하는 책을 고르세요. 슬픔, 불안, 분노, 외로움, 지침, 스트레스처럼 무거운 감정이면 감정을 해소하거나 숨을 고르게 하는 책을 고르세요. 마음리포트처럼 감정의 원인, 패턴, 진단, 하루 분석을 설명하지 말고 독서 경험만 말하세요.
- 관심사 추천: 관심사 자체를 실제 주제로 다루는 책을 고르세요. 예를 들어 음악이면 음악 감상, 음악사, 뮤지션, 악기, 장르 해설처럼 그 관심사에 대해 읽을 내용이 있어야 합니다. 관심사를 막연한 위로 문장으로 바꾸지 마세요.
- 취미 추천: 취미를 실제로 즐기는 사람에게 도움이 되는 책을 고르세요. 방법, 기술, 도구, 작품 감상, 문화, 역사, 루틴처럼 취미 관점이 드러나야 하며, 취미를 소재로 한 일반 감성 에세이에 치우치지 마세요.
도서 장르는 후보 도서의 실제 성격을 따르세요. 에세이, 소설, 인문서, 실용서, 예술서, 만화 등 특정 장르를 사전에 우대하지 마세요.
서평 본문에 "관심사가 있어서", "취미가 있어서", "검색어", "키워드", "근거", "데이터", "마음리포트", "분석 결과"처럼 추천 로직이나 리포트 맥락이 직접 드러나는 표현을 쓰지 마세요.
나이와 성별은 책 선택의 배경으로만 반영하고, 문장에 직접 노출하거나 성별 고정관념으로 설명하지 마세요.
후보에 없는 책을 새로 만들면 안 됩니다.
genre는 선택한 책의 장르를 2~8자 정도로 짧게 쓰세요. 예: 소설, 심리, 인문, 실용서, 예술서, 만화, 자기계발, 에세이.

아래 형식만 지키세요.
candidate_id: book_1
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
        return {
            "theme": theme["name"],
            "theme_id": theme["id"],
            "theme_reason": theme.get("reason", ""),
            "keyword": theme.get("keyword", ""),
            "keyword_basis": theme.get("keyword_basis", ""),
            "genre": genre or _infer_genre(book, theme),
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


def _strip_html(value):
    return re.sub(r"<[^>]+>", "", str(value or "")).strip()


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

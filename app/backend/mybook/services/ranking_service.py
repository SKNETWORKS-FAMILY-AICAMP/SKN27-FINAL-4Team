"""Deterministic ranking policy for Kakao book candidates."""

from django.utils import timezone

from ..constants import (
    PROFILE_TOPIC_THEME_IDS,
)


def rank_kakao_books(
    books,
    *,
    keyword,
    basis_values,
    personalization_tokens,
    expanded_basis_tokens,
    content_terms=None,
    search_terms=None,
    theme_id="",
):
    tokens = personalization_tokens(
        keyword,
        [*(basis_values or []), *(search_terms or [])],
        content_terms,
    )
    expanded_basis = expanded_basis_tokens(basis_values)
    tokens = list(dict.fromkeys([*tokens, *sorted(expanded_basis)]))[:24]
    intent_evidence_tokens = set(
        personalization_tokens(keyword, [], [*(content_terms or []), *(search_terms or [])])
    ).difference(expanded_basis)
    ranked = []
    current_year = timezone.localdate().year

    for book in books:
        title = str(book.get("title") or "").lower()
        description = str(book.get("description") or "").lower()
        people_and_publisher = " ".join(
            [
                str(book.get("author") or ""),
                " ".join(book.get("translators") or []),
                str(book.get("publisher") or ""),
            ]
        ).lower()
        score = max(0.0, 18.0 - book.get("query_index", 0) * 3.0)
        score += max(0.0, 6.0 - book.get("result_index", 0) * 0.25)
        matches = []
        basis_title_matches = []
        basis_description_matches = []
        intent_metadata_matches = []
        for token in tokens:
            token_score = 0.0
            if token in title:
                token_score += 9.0
                if token in expanded_basis:
                    basis_title_matches.append(token)
                if token in intent_evidence_tokens:
                    intent_metadata_matches.append(token)
            if token in description:
                token_score += 5.0
                if token in expanded_basis:
                    basis_description_matches.append(token)
                if token in intent_evidence_tokens:
                    intent_metadata_matches.append(token)
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
        book["basis_title_match_terms"] = sorted(set(basis_title_matches))
        book["basis_description_match_terms"] = sorted(set(basis_description_matches))
        book["direct_basis_match_terms"] = sorted(
            set(basis_title_matches).union(basis_description_matches)
        )
        book["intent_metadata_match_terms"] = sorted(set(intent_metadata_matches))
        book["direct_topic_match_terms"] = sorted(
            set(book["direct_basis_match_terms"]).union(
                book["intent_metadata_match_terms"]
                if len(book["intent_metadata_match_terms"]) >= 2
                else []
            )
        )
        ranked.append(book)

    # 검색 API의 검색어 일치는 내용 관련성을 보장하지 않는다. 관심사·취미는
    # 선택 주제(및 서버가 관리하는 직접 동의어)가 제목이나 책 소개에서 실제로
    # 확인된 후보만 최종 AI 선택 단계로 넘긴다.
    if theme_id in PROFILE_TOPIC_THEME_IDS and expanded_basis:
        ranked = [book for book in ranked if book.get("direct_topic_match_terms")]

    return sorted(
        ranked,
        key=lambda book: (
            -book.get("personalization_score", 0),
            book.get("query_index", 0),
            book.get("result_index", 0),
            book.get("title") or "",
        ),
    )

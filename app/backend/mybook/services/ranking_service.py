"""Deterministic ranking policies for Kakao and NLK book candidates."""

import time

from django.utils import timezone

from ..constants import (
    EMOTION_POSITIVE_MARKERS,
    HOBBY_NEGATIVE_MARKERS,
    HOBBY_POSITIVE_MARKERS,
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


def rank_personalized_books(
    books,
    *,
    keyword,
    basis_values,
    theme_id,
    personalization_tokens,
    expanded_basis_tokens,
    content_terms=None,
):
    tokens = personalization_tokens(keyword, basis_values, content_terms)
    basis_tokens = expanded_basis_tokens(basis_values)
    tokens = list(dict.fromkeys([*sorted(basis_tokens), *tokens]))[:20]
    content_intent_tokens = set(personalization_tokens("", [], content_terms))
    intent_tokens = set(personalization_tokens(keyword, [], content_terms))
    primary_basis_values = [
        value
        for value in basis_values
        if expanded_basis_tokens([value]).intersection(intent_tokens)
    ]
    primary_basis_tokens = set()
    for value in primary_basis_values:
        primary_basis_tokens.update(expanded_basis_tokens([value]))

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

        metadata_text = f"{title} {subjects}"
        if theme_id == "hobbies" and any(
            marker in metadata_text for marker in HOBBY_POSITIVE_MARKERS
        ):
            score += 8
        if theme_id == "hobbies" and any(
            marker in metadata_text for marker in HOBBY_NEGATIVE_MARKERS
        ):
            score -= 6
        if theme_id == "emotion" and any(
            marker in metadata_text for marker in EMOTION_POSITIVE_MARKERS
        ):
            score += 2

        book["personalization_score"] = round(score, 2)
        book["content_match_score"] = round(content_match_score, 2)
        book["match_terms"] = matches
        book["semantic_match_terms"] = semantic_matches
        book["basis_match_terms"] = sorted(basis_tokens.intersection(matches))
        book["basis_metadata_match_terms"] = sorted(set(basis_metadata_matches))
        book["primary_basis_match_terms"] = sorted(primary_basis_tokens.intersection(matches))
        book["primary_basis_metadata_match_terms"] = sorted(
            primary_basis_tokens.intersection(basis_metadata_matches)
        )
        book["content_intent_match_terms"] = sorted(
            content_intent_tokens.intersection(semantic_matches)
        )
        ranked.append(book)

    if tokens:
        if theme_id in PROFILE_TOPIC_THEME_IDS and basis_tokens:
            required_match_field = (
                "primary_basis_match_terms" if primary_basis_tokens else "basis_match_terms"
            )
            metadata_match_field = (
                "primary_basis_metadata_match_terms"
                if primary_basis_tokens
                else "basis_metadata_match_terms"
            )
            if any(book.get(metadata_match_field) for book in ranked):
                ranked = [book for book in ranked if book.get(metadata_match_field)]
            else:
                ranked = [book for book in ranked if book.get(required_match_field)]
        else:
            ranked = [
                book
                for book in ranked
                if book.get("basis_match_terms") or book.get("content_intent_match_terms")
            ]

    return sorted(
        ranked,
        key=lambda book: (
            -book.get("personalization_score", 0),
            -(book.get("issued_year") or 0),
            book.get("title") or "",
        ),
    )

"""Pure normalization, validation, and search-term utilities."""

import html
import re
from urllib.parse import urlencode, urlparse

from .constants import (
    ADULT_CONTENT_PATTERNS,
    ALLOWED_COVER_HOST_SUFFIXES,
    BASIS_TOKEN_ALIASES,
    CATALOG_ACTION_TOKENS,
    GENERIC_SEARCH_TERMS,
    PERSONALIZATION_STOPWORDS,
)


_ADULT_CONTENT_REGEXES = tuple(
    re.compile(pattern, re.IGNORECASE) for pattern in ADULT_CONTENT_PATTERNS
)


def _fallback_search_terms(keyword):
    cleaned = re.sub(r"[^0-9A-Za-z가-힣\s]", " ", str(keyword or ""))
    tokens = [token for token in cleaned.split() if len(token) >= 2]
    meaningful = [token for token in tokens if token not in GENERIC_SEARCH_TERMS]
    terms = []
    fallback_tokens = meaningful or tokens
    for term in [" ".join(tokens), *fallback_tokens]:
        term = term.strip()
        if term and term not in terms:
            terms.append(term)
    return terms[:4]


def _catalog_core_term(value):
    """Return a short noun-like anchor suitable for a Kakao book query."""
    cleaned = re.sub(r"[^0-9A-Za-z가-힣\s]", " ", str(value or ""))
    tokens = [token for token in cleaned.split() if len(token) >= 2]
    if not tokens:
        return ""

    for token in tokens:
        for source in BASIS_TOKEN_ALIASES:
            if source == token or source in token or token in source:
                return source

    return next((token for token in tokens if token not in CATALOG_ACTION_TOKENS), tokens[0])


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
        for value in _fallback_search_terms(keyword):
            tokens = value.split()[:2]
            term = " ".join(tokens).strip()
            if term and term not in terms:
                terms.append(term)
            if len(terms) >= 2:
                break
    return terms[:4]
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
    return [book for book in candidates if book.get("isbn") not in excluded]


def _is_safe_book_candidate(book):
    """Return False when public catalog metadata signals adult-only content."""
    if not isinstance(book, dict):
        return False
    source_result = book.get("source_result")
    source_result = source_result if isinstance(source_result, dict) else {}
    metadata = " ".join(
        [
            *(str(book.get(field) or "") for field in ("title", "description")),
            *(str(source_result.get(field) or "") for field in ("title", "description")),
        ]
    )
    normalized = re.sub(r"[\[\]{}()<>_/·:：-]+", " ", metadata)
    normalized = re.sub(r"\s+", " ", normalized).strip()
    return not any(pattern.search(normalized) for pattern in _ADULT_CONTENT_REGEXES)


def _safe_external_cover_url(value):
    url = _safe_http_url(value)
    parsed = urlparse(url)
    host = (parsed.hostname or "").lower()
    if not host.endswith(ALLOWED_COVER_HOST_SUFFIXES):
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


def _personalization_tokens(keyword, basis_values, content_terms=None):
    raw_values = [keyword, *(content_terms or []), *(basis_values or [])]
    tokens = []
    for value in raw_values:
        cleaned = re.sub(r"[^0-9A-Za-z가-힣\s]", " ", str(value or "")).lower()
        for token in cleaned.split():
            if len(token) >= 2 and token not in PERSONALIZATION_STOPWORDS and token not in tokens:
                tokens.append(token)
    return tokens[:12]


def _expanded_basis_tokens(basis_values):
    tokens = [
        token
        for token in _personalization_tokens("", basis_values)
        if token not in CATALOG_ACTION_TOKENS
    ]
    expanded = list(tokens)
    compact_basis_values = [
        re.sub(r"[^0-9A-Za-z가-힣]", "", str(value or "")).lower()
        for value in basis_values or []
    ]
    for token in [*tokens, *compact_basis_values]:
        for source, related in BASIS_TOKEN_ALIASES.items():
            compact_source = re.sub(r"[^0-9A-Za-z가-힣]", "", source).lower()
            if compact_source not in token and token not in compact_source:
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
        for term in _fallback_search_terms(fallback_keyword):
            if term not in terms:
                terms.append(term)
            if len(terms) >= 2:
                break
    return terms[:4]

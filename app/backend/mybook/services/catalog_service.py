"""HTTP transport and response validation for external book catalogs."""

import math
import time

import requests

from ..constants import (
    KAKAO_BOOK_API_URL,
    KAKAO_BOOK_RETRY_COUNT,
    KAKAO_BOOK_TIMEOUT_SECONDS,
    NLK_BOOK_API_URL,
    NLK_BOOK_PAGE_SIZE,
    NLK_BOOK_RETRY_COUNT,
    NLK_BOOK_TIMEOUT_SECONDS,
    NLK_NO_DATA_CODES,
    NLK_PROBE_PAGE_RATIOS,
    NLK_SUCCESS_CODES,
    RETRYABLE_HTTP_STATUSES,
)


def request_kakao_book_search(service_key, query, *, size=20, page=1, sort="accuracy"):
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
                time.sleep(0.25 * (2**attempt))
                continue
            raise
        if response.status_code not in RETRYABLE_HTTP_STATUSES:
            response.raise_for_status()
            try:
                payload = response.json()
            except ValueError as exc:
                raise RuntimeError("Kakao book API returned a non-JSON response") from exc
            if not isinstance(payload, dict) or not isinstance(payload.get("documents", []), list):
                raise RuntimeError("Kakao book API returned an invalid response")
            return payload
        if attempt < KAKAO_BOOK_RETRY_COUNT:
            time.sleep(0.25 * (2**attempt))

    response.raise_for_status()
    return response.json()


def request_nlk_books(service_key, keyword, display, page_no=1):
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
                time.sleep(0.25 * (2**attempt))
                continue
            raise
        if response.status_code not in RETRYABLE_HTTP_STATUSES:
            response.raise_for_status()
            try:
                return response.json()
            except ValueError as exc:
                raise RuntimeError("NLK API returned a non-JSON response") from exc
        if attempt < NLK_BOOK_RETRY_COUNT:
            time.sleep(0.25 * (2**attempt))

    response.raise_for_status()
    return response.json()


def nlk_probe_page_numbers(first_payload):
    total_count, rows_per_page = nlk_page_info(first_payload)
    if total_count <= rows_per_page:
        return []

    last_page = max(1, math.ceil(total_count / rows_per_page))
    page_numbers = []
    # The catalog commonly returns older records first. Probe the tail first so
    # the freshness policy can find recent books within a small request budget.
    for ratio in NLK_PROBE_PAGE_RATIOS:
        page_no = max(2, min(last_page, math.ceil(last_page * ratio)))
        if page_no not in page_numbers:
            page_numbers.append(page_no)
    return page_numbers


def nlk_root(payload):
    return payload.get("response", payload) if isinstance(payload, dict) else {}


def nlk_page_info(payload):
    root = nlk_root(payload)
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


def nlk_items(payload):
    root = nlk_root(payload)
    header = root.get("header", {}) if isinstance(root, dict) else {}
    result_code = str(header.get("resultCode") or "").strip()
    result_message = str(header.get("resultMsg") or "").strip()
    if result_code in NLK_NO_DATA_CODES or result_message == "NODATA_ERROR":
        return []
    if result_code and result_code not in NLK_SUCCESS_CODES:
        raise RuntimeError(result_message or f"NLK API error: {result_code}")

    body = root.get("body", {}) if isinstance(root, dict) else {}
    items = body.get("items", {}) if isinstance(body, dict) else {}
    if isinstance(items, dict):
        items = items.get("item", [])
    if isinstance(items, dict):
        return [items]
    return items if isinstance(items, list) else []

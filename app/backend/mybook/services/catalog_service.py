"""HTTP transport and response validation for Kakao book search."""

import time

import requests

from ..constants import (
    KAKAO_BOOK_API_URL,
    KAKAO_BOOK_RETRY_COUNT,
    KAKAO_BOOK_TIMEOUT_SECONDS,
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

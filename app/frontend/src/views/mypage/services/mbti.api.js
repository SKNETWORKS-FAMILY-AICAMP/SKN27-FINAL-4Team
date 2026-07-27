// 2026-07-23: PUT/POST/DELETE는 CSRF 토큰 필수 — 생짜 fetch라 axios 인터셉터를
// 못 타서 운영(세션 인증)에서 전부 403이었다. 공용 토큰 저장소에서 첨부한다.
import { getCsrfToken } from '../../../api/client.js'
export async function fetchMbtiDemoPayload(periodKey = "") {
  const queryParams = new URLSearchParams();
  if (periodKey) queryParams.set("period_key", periodKey);
  const queryString = queryParams.toString();
  const response = await fetch(`/api/mbti/monthly-demo/${queryString ? `?${queryString}` : ""}`, {
    cache: "no-store",
    credentials: "include"
  });
  if (!response.ok) {
    throw new Error(`MBTI demo API failed: ${response.status}`);
  }
  return response.json();
}

export async function requestMbtiMonthlyAnalysis(periodKey = "") {
  const response = await fetch("/api/mbti/monthly-analysis/", {
    method: "POST",
    headers: { "Content-Type": "application/json", "X-CSRFToken": getCsrfToken() },
    credentials: "include",
    body: JSON.stringify(periodKey ? { period_key: periodKey } : {})
  });
  if (!response.ok) {
    throw new Error(`MBTI analysis request failed: ${response.status}`);
  }
  return response.json();
}

export async function saveOnboardingMbti(mbtiType) {
  const response = await fetch("/api/mbti/onboarding/", {
    method: "POST",
    headers: { "Content-Type": "application/json", "X-CSRFToken": getCsrfToken() },
    credentials: "include",
    body: JSON.stringify({ mbti_type: mbtiType })
  });
  if (!response.ok) {
    throw new Error(`Failed to save MBTI: ${response.status}`);
  }
  return response.json();
}

export async function fetchMockQuestion(axis = "") {
  const url = axis
    ? `/api/mbti/mock-qna/question/?axis=${encodeURIComponent(axis)}`
    : "/api/mbti/mock-qna/question/";
  const response = await fetch(url, { credentials: "include" });
  if (!response.ok) {
    throw new Error(`Failed to fetch mock question: ${response.status}`);
  }
  return response.json();
}

export async function saveMockAnswer(payload) {
  const response = await fetch("/api/mbti/mock-qna/answer/", {
    method: "POST",
    headers: { "Content-Type": "application/json", "X-CSRFToken": getCsrfToken() },
    credentials: "include",
    body: JSON.stringify(payload)
  });
  if (!response.ok) {
    throw new Error(`Failed to save mock answer: ${response.status}`);
  }
  return response.json();
}

export async function resetMockQna() {
  const response = await fetch("/api/mbti/mock-qna/reset/", {
    method: "DELETE",
    headers: { "Content-Type": "application/json", "X-CSRFToken": getCsrfToken() },
    credentials: "include"
  });
  if (!response.ok) {
    throw new Error(`Failed to reset mock qna: ${response.status}`);
  }
  return response.json();
}

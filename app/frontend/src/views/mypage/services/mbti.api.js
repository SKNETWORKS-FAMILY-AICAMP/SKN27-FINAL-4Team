export async function fetchMbtiDemoPayload(force = false) {
  const queryParams = force ? "?force=true" : "";
  const response = await fetch(`/api/mbti/monthly-demo/${queryParams}`, {
    cache: "no-store",
    credentials: "include"
  });
  if (!response.ok) {
    throw new Error(`MBTI demo API failed: ${response.status}`);
  }
  return response.json();
}

export async function saveOnboardingMbti(mbtiType) {
  const response = await fetch("/api/mbti/onboarding/", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
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
    headers: { "Content-Type": "application/json" },
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
    headers: { "Content-Type": "application/json" },
    credentials: "include"
  });
  if (!response.ok) {
    throw new Error(`Failed to reset mock qna: ${response.status}`);
  }
  return response.json();
}

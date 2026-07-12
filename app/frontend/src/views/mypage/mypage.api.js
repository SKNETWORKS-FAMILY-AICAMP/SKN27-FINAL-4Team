export async function fetchMbtiDemoPayload(force = false) {
  const queryParams = force ? "?force=true" : "";
  const endpoints = [
    `/api/mbti/monthly-demo/${queryParams}`,
    `http://localhost:8000/api/mbti/monthly-demo/${queryParams}`
  ];

  let lastError = null;
  for (const endpoint of endpoints) {
    try {
      const response = await fetch(endpoint, { cache: "no-store", credentials: "include" });
      if (!response.ok) {
        lastError = new Error(`MBTI demo API failed: ${response.status}`);
        continue;
      }
      return response.json();
    } catch (error) {
      lastError = error;
    }
  }

  throw lastError || new Error("MBTI demo API is not reachable");
}

export async function fetchMyProfile() {
  const response = await fetch("/api/myprofile/profile/", { credentials: "include" });
  if (!response.ok) {
    throw new Error(`Failed to fetch profile: ${response.status}`);
  }
  return response.json();
}

export async function updateMyProfile(profileData) {
  const response = await fetch("/api/myprofile/profile/", {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    credentials: "include",
    body: JSON.stringify({ profile: profileData })
  });
  if (!response.ok) {
    throw new Error(`Failed to update profile: ${response.status}`);
  }
  return response.json();
}

export async function fetchCurrentWeather(location = {}) {
  const params = new URLSearchParams();
  if (location.lat != null && location.lon != null) {
    params.set("lat", location.lat);
    params.set("lon", location.lon);
  }
  if (location.region) {
    params.set("region", location.region);
  }

  const query = params.toString();
  const response = await fetch(`/api/myweather/current/${query ? `?${query}` : ""}`, {
    cache: "no-store",
    credentials: "include"
  });
  if (!response.ok) {
    let detail = `Failed to fetch weather: ${response.status}`;
    try {
      const data = await response.json();
      detail = data.detail || detail;
    } catch (error) {}
    throw new Error(detail);
  }
  return response.json();
}

export async function fetchWardrobeRecommendation() {
  const response = await fetch("/api/mywardrobe/recommendation/", {
    cache: "no-store",
    credentials: "include"
  });
  if (!response.ok) {
    let detail = `Failed to fetch wardrobe recommendation: ${response.status}`;
    try {
      const data = await response.json();
      detail = data.detail || detail;
    } catch (error) {}
    throw new Error(detail);
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
  const url = axis ? `/api/mbti/mock-qna/question/?axis=${axis}` : `/api/mbti/mock-qna/question/`;
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

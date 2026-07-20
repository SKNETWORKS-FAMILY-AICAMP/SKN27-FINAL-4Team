export { fetchBookRecommendation } from "./services/book.api";
export {
  fetchMbtiDemoPayload,
  fetchMockQuestion,
  resetMockQna,
  saveMockAnswer,
  saveOnboardingMbti,
} from "./services/mbti.api";
export { fetchMyProfile, updateMyProfile } from "./services/profile.api";
export { fetchCurrentWeather, fetchWeatherRegions } from "./services/weather.api";

export const MEMORY_API_ENABLED = true;

export async function fetchMemoryVault(force = false) {
  const queryParams = force ? "?force=true" : "";
  const endpoints = [
    `/api/mymemory/memories/${queryParams}`,
    `/api/mypage/memory/${queryParams}`
  ];

  let lastError = null;
  for (const endpoint of endpoints) {
    try {
      const response = await fetch(endpoint, {
        cache: "no-store",
        credentials: "include"
      });
      if (!response.ok) {
        lastError = new Error(`Failed to fetch memories: ${response.status}`);
        continue;
      }
      return response.json();
    } catch (error) {
      lastError = error;
    }
  }

  throw lastError || new Error("Memory API is not reachable");
}

export async function deleteMemoryVaultItem(memoryId) {
  const encodedId = encodeURIComponent(memoryId);
  const endpoints = [
    `/api/mymemory/memories/${encodedId}/`,
    `/api/mypage/memory/${encodedId}/`
  ];

  let lastError = null;
  for (const endpoint of endpoints) {
    try {
      const response = await fetch(endpoint, {
        method: "DELETE",
        credentials: "include"
      });
      if (!response.ok) {
        lastError = new Error(`Failed to delete memory: ${response.status}`);
        continue;
      }
      if (response.status === 204) return {};
      return response.json().catch(() => ({}));
    } catch (error) {
      lastError = error;
    }
  }

  throw lastError || new Error("Memory delete API is not reachable");
}

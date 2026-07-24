// 2026-07-23: PUT/POST/DELETE는 CSRF 토큰 필수 — 생짜 fetch라 axios 인터셉터를
// 못 타서 운영(세션 인증)에서 전부 403이었다. 공용 토큰 저장소에서 첨부한다.
import { getCsrfToken } from '../../../api/client.js'
export async function fetchMyProfile() {
  const response = await fetch("/api/myprofile/profile/", { credentials: "include" });
  if (!response.ok) {
    throw new Error(`Failed to fetch profile: ${response.status}`);
  }
  return response.json();
}

export async function fetchTodayEmotion() {
  const response = await fetch('/api/myprofile/today-emotion/', {
    cache: 'no-store',
    credentials: 'include',
  });
  if (!response.ok) {
    throw new Error(`Failed to fetch today's emotion: ${response.status}`);
  }
  return response.json();
}

export async function updateMyProfile(profileData) {
  const response = await fetch("/api/myprofile/profile/", {
    method: "PUT",
    headers: { "Content-Type": "application/json", "X-CSRFToken": getCsrfToken() },
    credentials: "include",
    body: JSON.stringify({ profile: profileData })
  });
  if (!response.ok) {
    throw new Error(`Failed to update profile: ${response.status}`);
  }
  return response.json();
}

export async function fetchMyProfile() {
  const response = await fetch("/api/myprofile/profile/", {
    cache: "no-store",
    credentials: "include",
  });
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
    headers: { "Content-Type": "application/json" },
    credentials: "include",
    body: JSON.stringify({ profile: profileData })
  });
  if (!response.ok) {
    throw new Error(`Failed to update profile: ${response.status}`);
  }
  return response.json();
}

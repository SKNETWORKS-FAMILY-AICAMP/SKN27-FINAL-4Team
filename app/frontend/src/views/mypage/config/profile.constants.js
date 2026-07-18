export const MIN_PROFILE_PREFERENCE_COUNT = 3;

export const PROFILE_GENDER_OPTIONS = Object.freeze([
  "남",
  "여",
  "선택 안 함",
]);

export function countProfilePreferences(profile) {
  const interests = Array.isArray(profile?.interests) ? profile.interests : [];
  const hobbies = Array.isArray(profile?.hobbies) ? profile.hobbies : [];
  return new Set([...interests, ...hobbies].filter(Boolean)).size;
}

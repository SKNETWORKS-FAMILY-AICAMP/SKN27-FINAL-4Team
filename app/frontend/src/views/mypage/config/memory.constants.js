export const MEMORY_API_ROUTES = Object.freeze([
  "/api/mymemory/memories/",
  "/api/mypage/memory/",
]);

export const MEMORY_NEGATIVE_POLARITIES = Object.freeze([
  "불호",
  "싫음",
  "오",
  "negative",
  "dislike",
  "-1",
]);

export const MEMORY_NEUTRAL_POLARITIES = Object.freeze([
  "중립",
  "neutral",
  "0",
]);

export const MEMORY_DATE_TIME_FORMAT = Object.freeze({
  year: "numeric",
  month: "2-digit",
  day: "2-digit",
  hour: "2-digit",
  minute: "2-digit",
});

export const MEMORY_DATE_FORMAT = Object.freeze({
  year: "numeric",
  month: "long",
  day: "numeric",
});

export const DEFAULT_MEMORY_POLARITY = "호";

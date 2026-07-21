export const WEATHER_SECTIONS = Object.freeze([
  { key: "summary", label: "오늘" },
  { key: "rhythm", label: "예보" },
  { key: "choices", label: "추천" },
]);

export const DEFAULT_KMA_ATTRIBUTION = Object.freeze({
  label: "기상청 API허브",
  url: "https://apihub.kma.go.kr/apiInfo.do",
});

export const WEATHER_DAY_START_HOUR = 6;
export const WEATHER_DAY_END_HOUR = 18;
export const WEATHER_EMOJI_NIGHT_START_HOUR = 19;

export const WEATHER_INDEX_COLORS = Object.freeze({
  danger: "#ef4444",
  warning: "#f97316",
  caution: "#facc15",
  interest: "#3b82f6",
  safe: "#22c55e",
  unknown: "#8ea7ff",
});

export const WEATHER_SCORE_THRESHOLDS = Object.freeze({
  high: 66,
  medium: 38,
});

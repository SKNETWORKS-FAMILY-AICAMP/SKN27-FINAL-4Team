export const DEFAULT_WEATHER_REGION = "서울";

export const MYPAGE_STORAGE_KEYS = Object.freeze({
  settings: "mindroom-settings",
  character: "binteumsaiCharacter",
  weatherLocation: "mindroom-weather-location",
  weatherAutoLocation: "mindroom-weather-auto-location",
});

export const MYPAGE_TIMING = Object.freeze({
  weatherRefreshIntervalMs: 60 * 1000,
  weatherFreshnessMs: 30 * 60 * 1000,
  geolocationTimeoutMs: 5000,
  geolocationMaximumAgeMs: 10 * 60 * 1000,
  toastDurationMs: 2400,
});

export const DEFAULT_MYPAGE_SETTINGS = Object.freeze({
  language: "ko",
  fontScale: 1,
  highContrast: false,
});

export const MYPAGE_CHARACTERS = Object.freeze([
  {
    id: "otter",
    name: "토토",
    role: "다정한 위로형",
    tone: "부드럽고 따뜻한 말투",
    line: "오늘 마음은 제가 옆에서 같이 정리해볼게요.",
    tags: ["다정함", "포근함"],
    stats: { empathy: 88, calm: 72, support: 86, careful: 82 },
  },
  {
    id: "cat",
    name: "까미",
    role: "시크한 직면형",
    tone: "무심하지만 핵심을 짚는 말투",
    line: "피하고 싶은 마음까지 천천히 살펴볼까요?",
    tags: ["솔직함", "냉철함"],
    stats: { empathy: 70, calm: 92, support: 76, careful: 84 },
  },
  {
    id: "redpanda",
    name: "포리",
    role: "활발한 응원형",
    tone: "밝고 힘 있게 응원하는 말투",
    line: "작은 행동 하나만 골라서 같이 시작해봐요.",
    tags: ["에너지", "긍정적"],
    stats: { empathy: 82, calm: 68, support: 94, careful: 78 },
  },
  {
    id: "bird",
    name: "여울",
    role: "소심한 공감형",
    tone: "조심스럽고 섬세한 말투",
    line: "괜찮아요. 천천히 말해도 제가 듣고 있을게요.",
    tags: ["조심스러움", "섬세함"],
    stats: { empathy: 92, calm: 85, support: 78, careful: 90 },
  },
]);

export const MBTI_VIEWS = Object.freeze([
  { key: "onboardingType", title: "온보딩 MBTI 설명", shortLabel: "온보딩 MBTI", buttonLabel: "온보딩 MBTI 설명" },
  { key: "onboardingNext", title: "월간 MBTI 분석", shortLabel: "월간 분석", buttonLabel: "월간 MBTI 분석" },
]);

export const MOVABLE_PANEL_IDS = Object.freeze([
  "profile",
  "mbti",
  "weather",
  "book",
  "memory",
  "character",
]);

export const PANEL_DESCRIPTIONS = Object.freeze({
  book: "관심사와 취미, 오늘의 감정을 바탕으로 지금 읽어볼 만한 책을 추천해요.",
  profile: "내 기본 정보와 관심사·취미를 확인하고 수정할 수 있어요.",
  character: "방 안의 동행 캐릭터를 고르고, 적용 전에 말투와 성향 정보를 확인할 수 있어요.",
  weather: "현재 날씨와 오늘의 활동 제안을 확인할 수 있어요.",
  mbti: "대화 중 자연스럽게 나눈 성향 답변을 바탕으로, 내가 요즘 어떤 방식으로 생각하고 소통하는지 MBTI 유형으로 돌아봐요.",
});

export const NAVIGATION_CONFIRM_OPTIONS = Object.freeze({
  chat: {
    title: "대화하러 갈까요?",
    message: "현재 마이룸을 벗어나 대화 페이지로 이동합니다.",
    path: "/chat",
  },
  report: {
    title: "마음리포트를 볼까요?",
    message: "현재 마이룸을 벗어나 마음리포트 페이지로 이동합니다.",
    path: "/report",
  },
});

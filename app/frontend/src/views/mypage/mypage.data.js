export const i18n = {
  ko: {
    subtitle: "대화와 분석 결과를 조용히 정리하는 개인 공간",
    roomTitle: "마이페이지 메인",
    hint: "방 안의 오브젝트에 커서를 올리거나 클릭해 기능을 열어보세요.",
    profile: "프로필 관리",
    character: "캐릭터 정보",
    weather: "날씨 정보",
    book: "오늘의 책 추천",
    memory: "기억 보관함",
    mbti: "MBTI 분석",
    taste: "취향 분석",
    settings: "설정"
  },
  en: {
    subtitle: "A personal room for conversations and self-insight",
    roomTitle: "My Page",
    hint: "Hover or click room objects to open each feature.",
    profile: "Profile",
    character: "Character Info",
    weather: "Weather",
    book: "Today's Book",
    memory: "Memory Vault",
    mbti: "MBTI Analysis",
    taste: "Taste Analysis",
    settings: "Settings"
  }
};

export function createMypageState() {
  return {
    activePanel: null,
    pendingPanel: null,
    pendingChatNavigation: false,
    pendingReportNavigation: false,
    navigationConfirm: null,
    roomFocusTarget: "character",
    roomMoveKey: 0,
    toast: "",
    weatherPayload: null,
    weatherLoading: false,
    weatherError: "",
    weatherLocation: null,
    weatherLastFetchedAt: 0,
    weatherRequestId: 0,
    weatherRefreshTimer: null,
    bookPayload: null,
    bookLoading: false,
    bookError: "",
    memoryPayload: null,
    memoryLoading: false,
    memoryError: "",
    memoryNotice: "",
    todayEmotionSummary: null,
    todayEmotionRefreshTimer: null,
    weatherRegions: [],
    profileSavedAt: "",
    profileEdit: false,
    profileSnapshot: null,
    selectedCharacter: "otter",
    characters: [
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
      }
    ],
    profile: {
      name: "",
      mbti: "",
      gender: "",
      birthDate: "",
      job: "",
      status: "",
      keywords: "",
      interests: [],
      hobbies: []
    },
    profileOptions: {
      interests: ["산책", "음악", "요리", "관계", "일", "수면", "운동", "공부", "가족", "혼자 있는 시간"],
      hobbies: ["플레이리스트 만들기", "짧은 에세이 읽기", "방 정리", "필사", "가벼운 요가", "사진 찍기", "드라마 보기"]
    },
    mbtiViewMode: "onboardingType",
    mbtiViews: [
      { key: "onboardingType", title: "온보딩 MBTI 설명", shortLabel: "온보딩 MBTI", buttonLabel: "온보딩 MBTI 설명" },
      { key: "onboardingNext", title: "월간 MBTI 분석", shortLabel: "월간 분석", buttonLabel: "월간 MBTI 분석" }
    ],
    mbtiApiStatus: "demo-fallback",
    mbtiData: null,
    taste: null,
    account: null,
    settings: {
      language: "ko",
      fontScale: 1,
      highContrast: false
    }
  };
}

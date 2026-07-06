export const i18n = {
  ko: {
    subtitle: "대화와 분석 결과를 조용히 정리하는 개인 공간",
    roomTitle: "마이페이지 메인",
    hint: "방 안의 오브젝트에 커서를 올리거나 클릭해 기능을 열어보세요.",
    user: "서마음",
    profile: "프로필 조회",
    mbti: "MBTI 분석",
    taste: "취향 분석",
    settings: "설정"
  },
  en: {
    subtitle: "A personal room for conversations and self-insight",
    roomTitle: "My Page",
    hint: "Hover or click room objects to open each feature.",
    user: "Maeum Seo",
    profile: "Profile",
    mbti: "MBTI Analysis",
    taste: "Taste Analysis",
    settings: "Settings"
  }
};

export function createMypageState() {
  return {
    activePanel: null,
    toast: "",
    showCharacterPicker: false,
    profileSavedAt: "",
    profileEdit: false,
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
      name: "서마음",
      mbti: "INFP",
      gender: "여",
      birthDate: "1997.06.23",
      job: "프로젝트를 준비 중인 사람",
      status: "교류하고 싶음",
      keywords: "공감형, 느린 집중, 감성 기록, 안정 선호",
      interests: ["산책", "음악", "관계"],
      hobbies: ["플레이리스트 만들기"]
    },
    profileOptions: {
      interests: ["산책", "음악", "요리", "관계", "일", "수면", "운동", "공부", "가족", "혼자 있는 시간"],
      hobbies: ["플레이리스트 만들기", "짧은 에세이 읽기", "방 정리", "필사", "가벼운 요가", "사진 찍기", "드라마 보기"]
    },
    mbtiViewMode: "onboardingType",
    mbtiViews: [
      { key: "onboardingType", title: "온보딩 MBTI 설명", shortLabel: "온보딩 MBTI", buttonLabel: "온보딩 MBTI 설명" },
      { key: "onboardingNext", title: "월간 MBTI 분석", shortLabel: "월간 분석", buttonLabel: "월간 MBTI 분석" },
      // { key: "mockQna", title: "임시 Q&A 입력", shortLabel: "임시 입력", buttonLabel: "임시 Q&A 입력" }
    ],
    mbtiApiStatus: "demo-fallback",
    mbtiData: {
      onboarding: {
        type: "ENFP",
        period: "온보딩 시점 기준 (가입 직후 사용자 입력)",
        description: "ENFP는 일반적으로 새로운 가능성을 빠르게 떠올리고, 사람·관계·아이디어를 연결하며, 정해진 절차보다 유연한 탐색을 선호하는 경향으로 설명됩니다.",
        report: [
          "초기 자기보고 MBTI이므로 설문 점수나 대화 기반 추정 근거를 붙이지 않습니다.",
          "가입 직후 사용자가 직접 입력한 유형을 기준으로, 이후 월간 분석 결과와 비교할 시작점 역할만 합니다.",
          "근거 리포트 영역에는 유형 설명과 표시 기준 안내만 제공합니다."
        ]
      },
      previous: {
        type: "ENFP",
        monthLabel: "전전달(4월) 기준"
      },
      current: {
        type: "INFP",
        monthLabel: "전달(5월) 기준",
        axes: [
          { label: "I", pair: "I / E", score: 68 },
          { label: "N", pair: "N / S", score: 61 },
          { label: "F", pair: "F / T", score: 57 },
          { label: "P", pair: "P / J", score: 64 }
        ]
      },
      report: [
        "[MBTI 변화 경향 현황] 전전달(4월) 추정 MBTI인 ENFP와 비교해, 전달(5월)에는 I 선호 지표가 새로 우세해져 INFP로 변화 경향이 나타났다.",
        "[MBTI 추정 및 경향분석 근거] 전달(5월) 추정에 영향을 준 실제 답변과 근거 문장을 바탕으로, 어떤 표현이 어느 선호 지표·방향을 뒷받침했는지 설명한다.",
        "[현재 MBTI에 대한 간단한 설명] 전달(5월) 기준 추정된 INFP 유형이 일반적으로 어떤 경향으로 설명되는지 간단히 안내하며, 성격을 확정하는 것이 아니라 그 달 관찰된 경향으로 해석함을 안내한다."
      ]
    },
    taste: {
      updated: "오늘 14:20",
      period: "최근 30일",
      messageCount: 128,
      conversationCount: 18,
      threshold: "최근 30일 기준 5회 이상",
      keywords: [
        { text: "로파이 음악", kind: "최근 관심사", count: 14, source: "휴식, 집중 관련 대화", lastSeen: "06.22" },
        { text: "감정 기록", kind: "간접 취향 신호", count: 11, source: "하루 정리, 메모 관련 대화", lastSeen: "06.21" },
        { text: "실내 식물", kind: "최근 관심사", count: 8, source: "공간 안정감, 책상 꾸미기 대화", lastSeen: "06.19" },
        { text: "짧은 산책", kind: "간접 취향 신호", count: 7, source: "회복 루틴 제안 대화", lastSeen: "06.18" },
        { text: "밤 루틴", kind: "간접 취향 신호", count: 6, source: "취침 전 정리 대화", lastSeen: "06.17" },
        { text: "선택지 줄이기", kind: "대화 선호", count: 5, source: "추천 방식 관련 대화", lastSeen: "06.16" }
      ],
      notices: [
        "최근 30일 대화 로그에서 같은 맥락이 일정 기준 이상 반복된 키워드만 표시합니다.",
        "직접 취향이라고 말하지 않았더라도 반복 맥락이 충분하면 간접 취향 신호로 분류합니다.",
        "성격을 판단하는 분석이 아니라, 최근 대화에서 자주 나타난 관심사 현황을 보여주는 집계입니다."
      ]
    },
    account: {
      email: "maeum@example.com",
      provider: "Kakao",
      joinedAt: "2026.05.12",
      lastLogin: "2026.06.22 14:05",
      session: "Chrome Windows 현재 세션",
      plan: "Free"
    },
    settings: {
      language: "ko",
      fontScale: 1,
      highContrast: false
    }
  };
}

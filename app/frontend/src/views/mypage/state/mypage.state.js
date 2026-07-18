import {
  DEFAULT_MYPAGE_SETTINGS,
  MBTI_VIEWS,
  MYPAGE_CHARACTERS,
} from "../config/mypage.constants";

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
    mbti: "MBTI 분석"
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
    mbti: "MBTI Analysis"
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
    toastTimer: null,
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
    weatherRegions: [],
    profileSavedAt: "",
    profileEdit: false,
    profileSnapshot: null,
    selectedCharacter: "otter",
    characters: MYPAGE_CHARACTERS,
    profile: {
      name: "",
      mbti: "",
      gender: "",
      birthDate: "",
      job: "",
      interests: [],
      hobbies: []
    },
    mbtiViewMode: "onboardingType",
    mbtiViews: MBTI_VIEWS,
    mbtiApiStatus: "idle",
    mbtiData: null,
    settings: { ...DEFAULT_MYPAGE_SETTINGS }
  };
}

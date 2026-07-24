export const BOOK_THEME_ORDER = Object.freeze(["emotion", "interests", "hobbies"]);

export const BOOK_THEME_LABELS = Object.freeze({
  emotion: "감정 추천",
  interests: "관심사 추천",
  hobbies: "취미 추천",
});

export const BOOK_THEME_CAPTIONS = Object.freeze({
  emotion: "오늘의 마음",
  interests: "프로필 관심사",
  hobbies: "프로필 취미",
});

export const BOOK_THEME_NAMES = Object.freeze({
  emotion: "오늘의 감정 추천",
  interests: "관심사 기반 추천",
  hobbies: "취미 기반 추천",
});

export const BOOK_THEME_GUIDES = Object.freeze({
  emotion: "오늘 기록된 감정과 책의 분위기·주제를 비교해 추천해요.",
  interests: "프로필에 저장된 관심사와 책의 주제·분야를 비교해 추천해요.",
  hobbies: "프로필에 저장된 취미와 책의 내용·활용성을 비교해 추천해요.",
});

export const DEFAULT_BOOK_SOURCE_PROVIDER = Object.freeze({
  label: "Kakao Daum 책 검색",
  short_label: "Kakao 도서정보",
  detail_url: "https://developers.kakao.com/docs/latest/ko/daum-search/dev-guide#search-book",
  attribution: "책 정보·표지: Kakao Daum 책 검색",
});

<script setup>
import { computed, ref, watch } from "vue";
import { userApi } from "../../api/user.js";
import hobbyCsv from "../../assets/data/preference_hobbies.csv?raw";
import interestCsv from "../../assets/data/preference_interests.csv?raw";
import {
  AGREEMENT_VERSION,
  privacyCollectionContent,
  termsContent,
} from "../../constants/onboardingAgreements.js";

const emit = defineEmits(["navigate"]);

const MIN_PREFERENCE_COUNT = 3;
const PREFERENCE_GRID_SLOT_COUNT = 16;

const hobbyItems = parseKeywordCsv(hobbyCsv, "hobby");
const interestItems = parseKeywordCsv(interestCsv, "interest");
const storedProfile = getStoredProfile();
const defaultHobbies = ["볼링", "해외여행", "카페 투어"];
const defaultInterests = [];
const initialHobbies = normalizeInitialPreferenceLabels(
  storedProfile.hobbies?.length ? storedProfile.hobbies : defaultHobbies,
  "hobby",
  Infinity,
);
const initialInterests = normalizeInitialPreferenceLabels(
  storedProfile.interests?.length ? storedProfile.interests : defaultInterests,
  "interest",
  Infinity,
);

const profileForm = ref({
  nickname: storedProfile.nickname || "레이설",
  birthDate: formatBirthDateForDisplay(storedProfile.birth_date) || storedProfile.birthDate || storedProfile.birthday || "1998.12.23",
  gender: storedProfile.gender || "남",
  job: storedProfile.job || "UI/UX 디자이너",
});

const genderOptions = ["남", "여", "선택 안 함"];
const selectedHobbies = ref(initialHobbies);
const selectedInterests = ref(initialInterests);
const isSaving = ref(false);
const saveError = ref("");
const activePreferenceType = ref("hobby");
const termsOfServiceAgreed = ref(false);
const privacyCollectionAgreed = ref(false);
const activeAgreementModal = ref(null);

const selectedPreferenceLabels = computed(() => [...selectedHobbies.value, ...selectedInterests.value]);
const selectedPreferenceItems = computed(() => [
  ...selectedHobbies.value.map((label) => ({ ...getKeywordItem(label, "hobby"), type: "hobby" })),
  ...selectedInterests.value.map((label) => ({ ...getKeywordItem(label, "interest"), type: "interest" })),
]);
const activePreferenceItems = computed(() => activePreferenceType.value === "hobby" ? hobbyItems : interestItems);
const activePreferenceTitle = computed(() => activePreferenceType.value === "hobby" ? "취미/활동" : "관심 주제");
const activeCategory = ref("전체");
const categoryOptions = computed(() => {
  const seen = [];
  activePreferenceItems.value.forEach((item) => {
    const category = item.onboardingCategory || "기타";
    if (!seen.includes(category)) seen.push(category);
  });
  return ["전체", ...seen];
});
watch(activePreferenceType, () => {
  activeCategory.value = "전체";
});
const visiblePreferenceItems = computed(() =>
  activeCategory.value === "전체"
    ? activePreferenceItems.value
    : activePreferenceItems.value.filter((item) => (item.onboardingCategory || "기타") === activeCategory.value),
);
const preferenceGridItems = computed(() => {
  const slots = visiblePreferenceItems.value.map((item) => ({ ...item, placeholder: false }));

  while (slots.length < PREFERENCE_GRID_SLOT_COUNT) {
    slots.push({
      id: `preference-placeholder-${activePreferenceType.value}-${slots.length}`,
      placeholder: true,
    });
  }

  return slots;
});
const agreementsSatisfied = computed(() => termsOfServiceAgreed.value && privacyCollectionAgreed.value);
const activeAgreementTitle = computed(() => activeAgreementModal.value === "privacy" ? "개인정보 수집 및 이용 안내" : "이용약관");
const activeAgreementContent = computed(() => activeAgreementModal.value === "privacy" ? privacyCollectionContent : termsContent);

function getStoredProfile() {
  try {
    return JSON.parse(localStorage.getItem("binteumsaiUserProfile") || "{}");
  } catch {
    return {};
  }
}

function parseKeywordCsv(csvText, type) {
  const lines = csvText.replace(/^\uFEFF/, "").split(/\r?\n/).filter(Boolean);
  const headers = parseCsvLine(lines.shift() || "");

  return lines
    .map((line) => {
      const values = parseCsvLine(line);
      const raw = Object.fromEntries(headers.map((header, index) => [header, values[index] || ""]));
      return normalizeKeywordItem(raw, type);
    })
    .filter((item) => item.label)
    .sort((a, b) => a.sortOrder - b.sortOrder || b.popularityScore - a.popularityScore || a.label.localeCompare(b.label, "ko"));
}

function parseCsvLine(line) {
  const result = [];
  let current = "";
  let inQuotes = false;

  for (let index = 0; index < line.length; index += 1) {
    const char = line[index];
    const next = line[index + 1];

    if (char === '"' && next === '"') {
      current += '"';
      index += 1;
      continue;
    }

    if (char === '"') {
      inQuotes = !inQuotes;
      continue;
    }

    if (char === "," && !inQuotes) {
      result.push(current);
      current = "";
      continue;
    }

    current += char;
  }

  result.push(current);
  return result.map((value) => value.trim());
}

function normalizeKeywordItem(raw, type) {
  const label = type === "hobby"
    ? raw.display_label || raw.label || raw.keyword
    : raw.label || raw.displayLabel || raw.displayText || raw.keyword;
  const relatedKeywords = splitRelatedKeywords(raw.relatedKeywords);
  const searchText = [
    label,
    raw.display_label,
    raw.displayText,
    raw.keyword,
    raw.category,
    raw.subcategory,
    raw.subCategory,
    ...relatedKeywords,
  ].filter(Boolean).join(" ").toLowerCase();

  return {
    id: raw.hobby_id || raw.interestId || `${type}-${label}`,
    type,
    label,
    category: raw.category || "기타",
    subCategory: raw.subcategory || raw.subCategory || "",
    onboardingCategory: getOnboardingCategory(raw, type),
    icon: getKeywordIcon(label, type),
    relatedKeywords,
    sortOrder: Number(raw.sort_order || raw.sortOrder || 999),
    popularityScore: Number(raw.popularity_score || raw.popularityScore || 0),
    searchText,
  };
}

function getOnboardingCategory(raw, type) {
  const source = [raw.category, raw.subcategory, raw.subCategory, raw.label, raw.display_label, raw.keyword].filter(Boolean).join(" ");

  if (type === "hobby") {
    if (/운동|스포츠|산책|러닝|등산|요가|헬스/.test(source)) return "스포츠";
    if (/여행|외출|카페|맛집|공간|전시|공연|문화|사진/.test(source)) return "외출·공간";
    if (/영상|콘텐츠|영화|드라마|웹툰|게임|디지털|독서/.test(source)) return "콘텐츠·몰입";
    if (/음악|연주|노래|창작|표현|드로잉|글쓰기/.test(source)) return "음악·표현";
    if (/요리|미식|반려|자연|가드닝|라이프|홈/.test(source)) return "라이프스타일";
    if (/소셜|모임|체험|방문|페스티벌/.test(source)) return "소셜·체험";
    if (/학습|성장|자기|외국어|프로그래밍|디자인|마케팅|자격/.test(source)) return "성장";
    return "라이프스타일";
  }

  if (/콘텐츠|미디어|영상|영화|드라마|웹툰|예능|애니/.test(source)) return "콘텐츠";
  if (/음악|문화|K-POP|공연|뮤지컬|댄스|퍼포먼스/.test(source)) return "음악·문화";
  if (/여행|장소|공간|맛집|카페|팝업|사진/.test(source)) return "공간·취향";
  if (/라이프|패션|뷰티|반려|식물|홈|루틴|자기관리|쇼핑|음식|커피|차/.test(source)) return "라이프스타일";
  if (/관계|소통|연애|성장|자기이해|자기계발|심리/.test(source)) return "관계·성장";
  if (/감성|무드|창작|표현/.test(source)) return "감성·표현";
  if (/트렌드|레트로|뉴트로|호러|오컬트|로맨스|판타지|디지털/.test(source)) return "트렌드";
  return "라이프스타일";
}

function getKeywordIcon(label, type) {
  const text = String(label || "");
  if (/드라마/.test(text)) return "📺";
  if (/홈트레이닝/.test(text)) return "🏠";
  if (/국내여행|해외여행|캠핑/.test(text)) return "🚅";
  if (/웹툰 보기|웹툰/.test(text)) return "📖";
  if (/유튜브 시청|OTT 시청|OTT시청/.test(text)) return "📺";
  if (/꽃꽂이|꽃꽃이/.test(text)) return "🌸";
  if (/외국어|자격증/.test(text)) return "📚";
  if (/독서/.test(text)) return "📕";
  if (/낚시/.test(text)) return "🎣";
  if (/동호회|봉사 활동|봉사활동/.test(text)) return "👨‍👩‍👧‍👦";
  if (/원데이 클래스|원데이클래스|공방체험|공방 체험/.test(text)) return "🎨";
  if (/수집/.test(text)) return "📁";
  if (/패션 코디/.test(text)) return "🥼";
  if (/인테리어 꾸미기/.test(text)) return "🪄";
  if (/쇼핑/.test(text)) return "🛍️";
  if (/SNS/.test(text)) return "📱";

  if (/판타지/.test(text)) return "🧚";
  if (/호러|오컬트/.test(text)) return "👻";
  if (/홈라이프|홈 라이프/.test(text)) return "🏠";
  if (/K[- ]?POP/i.test(text)) return "🎤";
  if (/힙합|R&B/i.test(text)) return "🎵";
  if (/콘서트|페스티벌/.test(text)) return "🎪";
  if (/클래식|재즈/.test(text)) return "🎷";
  if (/다큐멘터리/.test(text)) return "🎞️";
  if (/레트로|뉴트로/.test(text)) return "📻";
  if (/로맨스/.test(text)) return "💕";
  if (/루틴|습관/.test(text)) return "🔁";
  if (/모임|소셜/.test(text)) return "🫂";
  if (/뮤지컬/.test(text)) return "🎭";
  if (/반려동물/.test(text)) return "🐾";
  if (/뷰티/.test(text)) return "💄";
  if (/여행/.test(text)) return "✈️";
  if (/연애/.test(text)) return "💘";
  if (/유튜브|유트브/.test(text)) return "💻";
  if (/팝업스토어|팝업 스토어/.test(text)) return "🎪";
  if (/인테리어/.test(text)) return "🛋️";
  if (/자기관리/.test(text)) return "💪";

  if (/자전거|사이클|라이딩/.test(text)) return "🚲";
  if (/골프/.test(text)) return "🏌️";
  if (/배드민턴/.test(text)) return "🏸";
  if (/테니스/.test(text)) return "🎾";
  if (/볼링/.test(text)) return "🎳";
  if (/축구|풋살/.test(text)) return "⚽";
  if (/농구/.test(text)) return "🏀";
  if (/수영/.test(text)) return "🏊";
  if (/클라이밍/.test(text)) return "🧗";
  if (/헬스|근력|웨이트/.test(text)) return "🏋️";
  if (/필라테스|요가/.test(text)) return "🧘";
  if (/러닝|달리기/.test(text)) return "🏃";
  if (/리본|댄스/.test(text)) return "💃";
  if (/노래 부르기/.test(text)) return "🎤";
  if (/음악|K-POP|발라드|재즈|콘서트/.test(text)) return "🎧";
  if (/악기|연주/.test(text)) return "🎸";
  if (/산책|러닝|운동|요가|등산|스포츠/.test(text)) return "🚶";
  if (/카페|커피|차|맛집|요리|베이킹/.test(text)) return "☕";
  if (/영화|드라마|웹툰|예능|애니|콘텐츠|유튜브|OTT시청/.test(text)) return "🎬";
  if (/게임|디지털|트렌드|방탈출/.test(text)) return "🎮";
  if (/독서|글쓰기|자기계발|학습/.test(text)) return "📚";
  if (/심리/.test(text)) return "💞 ";
  if (/전시|문화|공연/.test(text)) return "🎟️";
  if (/창작|드로잉|표현/.test(text)) return "🖋️";
  if (/사진/.test(text)) return "📷";
  if (/영상촬영/.test(text)) return "📽️";
  if (/반려|동물/.test(text)) return "🐾";
  if (/식물|가드닝|자연/.test(text)) return "🌱";
  if (/국내여행|외출|공간|팝업스토어 방문|캠핑|해외여행/.test(text)) return "🚅";
  if (/패션|뷰티|인테리어|쇼핑/.test(text)) return "🛍️";
  if (/낚시/.test(text)) return "🎣";
}

function splitRelatedKeywords(value) {
  return String(value || "")
    .split(/[|,]/)
    .map((keyword) => keyword.trim())
    .filter(Boolean);
}

function getItems(type) {
  return type === "hobby" ? hobbyItems : interestItems;
}

function getSelectedRef(type) {
  return type === "hobby" ? selectedHobbies : selectedInterests;
}

function getKeywordItem(label, type) {
  return getItems(type).find((item) => item.label === label) || {
    id: `${type}-${label}`,
    type,
    label,
    category: "기타",
    onboardingCategory: type === "hobby" ? "라이프스타일" : "라이프스타일",
    icon: getKeywordIcon(label, type),
    searchText: label.toLowerCase(),
    sortOrder: 999,
    popularityScore: 0,
  };
}

function normalizeInitialPreferenceLabels(labels, type, limit) {
  if (limit <= 0) return [];

  const seen = new Set();
  const normalized = [];

  for (const label of labels || []) {
    const normalizedLabel = getKeywordItem(label, type).label?.trim();
    if (!normalizedLabel || seen.has(normalizedLabel)) continue;

    seen.add(normalizedLabel);
    normalized.push(normalizedLabel);
    if (normalized.length >= limit) break;
  }

  return normalized;
}

function uniqueItems(items) {
  const seen = new Set();
  return items.filter((item) => {
    if (!item || seen.has(`${item.type}-${item.label}`)) return false;
    seen.add(`${item.type}-${item.label}`);
    return true;
  });
}

function getKeywordType(item) {
  return item?.type === "interest" ? "interest" : item?.type === "hobby" ? "hobby" : activePreferenceType.value;
}

function isKeywordSelected(item) {
  return getSelectedRef(getKeywordType(item)).value.includes(item.label);
}

function toggleKeywordItem(item) {
  const type = getKeywordType(item);
  const selected = getSelectedRef(type);

  if (selected.value.includes(item.label)) {
    selected.value = selected.value.filter((label) => label !== item.label);
    saveError.value = "";
    return;
  }

  saveError.value = "";
  selected.value = [...selected.value, item.label];
}

function resetPreferences() {
  selectedHobbies.value = [];
  selectedInterests.value = [];
  saveError.value = "";
}

function removeSelectedKeyword(label, type) {
  const selected = getSelectedRef(type);
  selected.value = selected.value.filter((item) => item !== label);
}

function openAgreementModal(type) {
  activeAgreementModal.value = type;
}

function closeAgreementModal() {
  activeAgreementModal.value = null;
}

function showValidationMessage(message) {
  saveError.value = message;
  alert(message);
}

async function saveUserInfo() {
  if (isSaving.value) return;

  isSaving.value = true;
  saveError.value = "";

  const nickname = profileForm.value.nickname.trim();
  const birthDateText = profileForm.value.birthDate.trim();
  const gender = profileForm.value.gender.trim();
  const normalizedBirthDate = normalizeBirthDate(profileForm.value.birthDate);
  const age = calculateAge(normalizedBirthDate);

  if (!nickname || !birthDateText || !gender) {
    showValidationMessage("이름 또는 닉네임, 생년월일, 성별을 꼭 입력해 주세요.");
    isSaving.value = false;
    return;
  }

  if (!normalizedBirthDate) {
    showValidationMessage("생년월일은 YYYY.MM.DD 형식으로 입력해 주세요.");
    isSaving.value = false;
    return;
  }

  if (!agreementsSatisfied.value) {
    showValidationMessage("필수 약관을 확인하고 동의해 주세요.");
    isSaving.value = false;
    return;
  }

  if (selectedPreferenceLabels.value.length < MIN_PREFERENCE_COUNT) {
    showValidationMessage(`취향 조각을 ${MIN_PREFERENCE_COUNT}개 이상 선택해 주세요.`);
    isSaving.value = false;
    return;
  }

  const profilePayload = {
    nickname,
    birth_date: normalizedBirthDate,
    gender,
    age,
    job: profileForm.value.job.trim(),
    hobbies: selectedHobbies.value,
    interests: selectedInterests.value,
    agreements: {
      termsOfService: termsOfServiceAgreed.value,
      privacyCollection: privacyCollectionAgreed.value,
      termsVersion: AGREEMENT_VERSION,
      privacyVersion: AGREEMENT_VERSION,
      agreedAt: new Date().toISOString(),
    },
  };

  try {
    const savedProfile = await userApi.saveProfile(profilePayload);
    const localProfile = {
      ...profileForm.value,
      nickname: savedProfile?.nickname || nickname,
      age: savedProfile?.age || age,
      gender: savedProfile?.gender || gender,
      birthDate: formatBirthDateForDisplay(savedProfile?.birth_date) || profileForm.value.birthDate,
      birth_date: savedProfile?.birth_date || normalizedBirthDate,
      birthday: formatBirthDateForDisplay(savedProfile?.birth_date) || profileForm.value.birthDate,
      hobbies: savedProfile?.hobbies || selectedHobbies.value,
      interests: savedProfile?.interests || selectedInterests.value,
    };

    localStorage.setItem("binteumsaiUserProfile", JSON.stringify(localProfile));
    localStorage.setItem("binteumsaiOnboardingJustCompleted", "true");

    try {
      const updatedUser = await userApi.getCurrentUser();
      window.dispatchEvent(new CustomEvent("binteumsai-auth-changed", { detail: { user: updatedUser } }));
    } catch {
      // 헤더 즉시 갱신에 실패해도 다음 페이지 이동/새로고침 시 정상적으로 반영된다.
    }

    emit("navigate", "onboardingComplete");
  } catch (error) {
    saveError.value = error.response?.data?.error || "사용자 정보를 저장하지 못했어요. 잠시 후 다시 시도해 주세요.";
  } finally {
    isSaving.value = false;
  }
}

function selectGender(gender) {
  profileForm.value.gender = gender;
}

function normalizeNicknameInput() {
  profileForm.value.nickname = String(profileForm.value.nickname || "").replace(/[^A-Za-z가-힣]/g, "");
}

function normalizeBirthDateInput() {
  const digits = String(profileForm.value.birthDate || "").replace(/\D/g, "").slice(0, 8);
  const parts = [];

  if (digits.length > 0) parts.push(digits.slice(0, 4));
  if (digits.length > 4) parts.push(digits.slice(4, 6));
  if (digits.length > 6) parts.push(digits.slice(6, 8));

  profileForm.value.birthDate = parts.join(".");
}

function normalizeBirthDate(value) {
  const text = String(value || "").trim();
  if (!text) return null;

  const match = text.match(/^(\d{4})\.(\d{2})\.(\d{2})$/);
  if (!match) return "";

  const [, year, month, day] = match;
  const date = new Date(`${year}-${month}-${day}T00:00:00`);
  if (
    Number.isNaN(date.getTime()) ||
    date.getFullYear() !== Number(year) ||
    date.getMonth() + 1 !== Number(month) ||
    date.getDate() !== Number(day)
  ) {
    return "";
  }

  return `${year}-${month}-${day}`;
}

function calculateAge(dateText) {
  if (!dateText) return Number(storedProfile.age || 1);
  const birth = new Date(`${dateText}T00:00:00`);
  const today = new Date();
  let age = today.getFullYear() - birth.getFullYear();
  const monthDiff = today.getMonth() - birth.getMonth();

  if (monthDiff < 0 || (monthDiff === 0 && today.getDate() < birth.getDate())) {
    age -= 1;
  }

  return Math.max(age, 1);
}

function formatBirthDateForDisplay(value) {
  if (!value) return "";
  const match = String(value).match(/^(\d{4})-(\d{2})-(\d{2})$/);
  if (!match) return "";
  return `${match[1]}.${match[2]}.${match[3]}`;
}
</script>

<template>
  <section class="view-card userinfo-setup-view">
    <article class="glass-panel userinfo-panel">
      <div class="setup-stepper" aria-label="첫 로그인 설정 단계">
        <span class="done"><b>1</b>로그인</span>
        <span class="done"><b>2</b>캐릭터</span>
        <span class="active"><b>3</b>정보와 취향</span>
        <span><b>4</b>완료</span>
      </div>

      <header class="userinfo-heading">
        <div class="text-area">
          <div class="heading-title"><h2>기본 정보와 취향 조각 수집하기</h2><span class="sparkle-mark" aria-hidden="true">✨</span></div>
          <p>당신에게 맞는 대화를 위해 필요한 정보만 가볍게 입력해 주세요.</p>
        </div>

        <div class="mascot-card image-area" aria-hidden="true">
          <img src="/characters/redpanda/default.png" alt="">
          <span>조금만 알려주면 더 잘 도와줄게요!</span>
        </div>
      </header>

      <form class="setup-form" novalidate @submit.prevent="saveUserInfo">
        <div class="form-grid">
          <section class="basic-info-card" aria-label="기본 정보 입력">
            <header class="section-heading">
              <div>
                <h3>기본 정보 입력</h3>
                <p>프로필 생성을 위한 기본 정보를 입력해 주세요.</p>
              </div>
            </header>

            <label class="field">
              <span>이름 또는 닉네임</span>
              <input
                v-model="profileForm.nickname"
                type="text"
                placeholder="이름 또는 닉네임"
                @input="normalizeNicknameInput"
              >
            </label>

            <label class="field">
              <span>생년월일</span>
              <span class="input-with-icon">
                <input
                  v-model="profileForm.birthDate"
                  class="ltr-input"
                  type="text"
                  dir="ltr"
                  inputmode="numeric"
                  maxlength="10"
                  placeholder="생년월일 8자리"
                  @input="normalizeBirthDateInput"
                >
                
              </span>
            </label>

            <label class="field">
              <span>직업</span>
              <input v-model="profileForm.job" type="text" placeholder="직업을 입력해 주세요">
            </label>

            <div class="field">
              <span>성별</span>
              <div class="gender-toggle" role="group" aria-label="성별 선택">
                <button
                  v-for="gender in genderOptions"
                  :key="gender"
                  type="button"
                  :class="{ active: profileForm.gender === gender }"
                  @click="selectGender(gender)"
                >
                  {{ gender }}
                  <i v-if="profileForm.gender === gender">✓</i>
                </button>
              </div>
            </div>

            <p class="lock-note">🔒 입력한 정보는 안전하게 보호되며, 서비스 제공 목적으로만 사용됩니다.</p>
          </section>

          <section class="preference-card" aria-label="취미와 관심분야 키워드 설정">
            <header class="preference-heading">
              <div>
                <h3>취미와 관심 분야</h3>
                <p>좋아하거나 관심 있는 활동을 자유롭게 골라주세요.</p>
              </div>
              <div class="preference-heading-actions">
                <span>선택한 태그 {{ selectedPreferenceLabels.length }}개</span>
                <button class="preference-reset-button" type="button" @click="resetPreferences">초기화</button>
              </div>
            </header>

            <div class="preference-tabs" role="tablist" aria-label="취향 종류">
              <button
                type="button"
                :class="{ active: activePreferenceType === 'hobby' }"
                @click="activePreferenceType = 'hobby'"
              >
                취미/활동
              </button>
              <button
                type="button"
                :class="{ active: activePreferenceType === 'interest' }"
                @click="activePreferenceType = 'interest'"
              >
                관심 주제
              </button>
            </div>

            <div class="preference-category-row" role="group" aria-label="카테고리 필터">
              <button
                v-for="category in categoryOptions"
                :key="category"
                type="button"
                :class="{ active: activeCategory === category }"
                @click="activeCategory = category"
              >
                {{ category }}
              </button>
            </div>

            <div class="preference-choice-box">
              <div class="preference-chip-grid" :aria-label="`${activePreferenceTitle} 선택 목록`">
                <template v-for="item in preferenceGridItems" :key="item.id">
                  <span
                    v-if="item.placeholder"
                    class="preference-choice-placeholder"
                    aria-hidden="true"
                  />
                  <button
                    v-else
                    type="button"
                    class="keyword-chip preference-choice-chip"
                    :class="{ selected: isKeywordSelected(item) }"
                    :aria-pressed="isKeywordSelected(item)"
                    @click="toggleKeywordItem(item)"
                  >
                    <span class="chip-icon" aria-hidden="true">{{ item.icon }}</span>
                    <strong>{{ item.label }}</strong>
                    <i v-if="isKeywordSelected(item)">✓</i>
                  </button>
                </template>
              </div>
            </div>

            <section class="selected-fragments" aria-label="선택한 취향 조각">
              <header>
                <div>
                  <h4>선택한 취향 조각</h4>
                  <p>{{ selectedPreferenceItems.length }}개 선택 완료!</p>
                </div>
              </header>
              <div v-if="selectedPreferenceItems.length" class="selected-keyword-row">
                <button
                  v-for="item in selectedPreferenceItems"
                  :key="`${item.type}-${item.label}`"
                  type="button"
                  class="selected-keyword-pill"
                  @click="removeSelectedKeyword(item.label, item.type)"
                >
                  <span aria-hidden="true">{{ item.icon }}</span>
                  {{ item.label }}
                  <i aria-hidden="true">×</i>
                </button>
              </div>
              <p v-else class="empty-selected-message">아직 선택한 조각이 없어요. 위 항목에서 취향을 골라주세요.</p>
            </section>

          </section>
        </div>

        <section class="agreement-card" aria-labelledby="agreement-title">
          <header>
            <div>
              <p>Required agreement</p>
              <h3 id="agreement-title">서비스 이용을 위한 확인</h3>
            </div>
            <span>필수 2개</span>
          </header>
          <p class="agreement-desc">빈틈사이를 시작하기 전에 필요한 약관을 확인해 주세요.</p>

          <div class="agreement-list">
            <div class="agreement-row">
              <label for="terms-of-service-agreement">
                <input
                  id="terms-of-service-agreement"
                  v-model="termsOfServiceAgreed"
                  type="checkbox"
                >
                <span class="required-badge">필수</span>
                <strong>이용약관에 동의합니다</strong>
              </label>
              <button type="button" @click="openAgreementModal('terms')">약관 보기</button>
            </div>

            <div class="agreement-row">
              <label for="privacy-collection-agreement">
                <input
                  id="privacy-collection-agreement"
                  v-model="privacyCollectionAgreed"
                  type="checkbox"
                >
                <span class="required-badge">필수</span>
                <strong>개인정보 수집 및 이용에 동의합니다</strong>
              </label>
              <button type="button" @click="openAgreementModal('privacy')">내용 보기</button>
            </div>
          </div>

          <p v-if="!agreementsSatisfied" class="agreement-help">필수 약관을 확인하고 동의해 주세요.</p>
        </section>

        <footer class="setup-submit-row">
          <p v-if="saveError" class="save-error">{{ saveError }}</p>
          <button class="btn primary large" type="submit" :disabled="isSaving || !agreementsSatisfied">
            {{ isSaving ? "저장 중..." : "동의하고 시작하기 ✨" }}
          </button>
        </footer>
      </form>
    </article>

    <div v-if="activeAgreementModal" class="agreement-modal-backdrop" @click.self="closeAgreementModal">
      <section class="agreement-modal" role="dialog" aria-modal="true" :aria-labelledby="`${activeAgreementModal}-agreement-title`">
        <header class="agreement-modal-header">
          <h3 :id="`${activeAgreementModal}-agreement-title`">{{ activeAgreementTitle }}</h3>
          <button type="button" aria-label="닫기" @click="closeAgreementModal">×</button>
        </header>

        <div class="agreement-modal-content">
          <p v-for="line in activeAgreementContent" :key="line">{{ line }}</p>
        </div>

        <button class="modal-complete-button" type="button" @click="closeAgreementModal">확인</button>
      </section>
    </div>
  </section>
</template>

<style scoped>
.userinfo-setup-view {
  width: min(1280px, calc(100% - 56px));
  min-height: calc(100dvh - var(--bt-header-h) - 46px);
  margin: 24px auto 34px;
  word-break: keep-all;
  overflow-wrap: break-word;
}

.userinfo-panel {
  padding: clamp(28px, 3vw, 44px);
  border-radius: 32px;
  background:
    linear-gradient(145deg, rgba(45, 13, 63, 0.82), rgba(22, 8, 41, 0.88)),
    rgba(45, 13, 63, 0.74);
}

.setup-stepper {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 16px;
  max-width: 760px;
  margin: 0 auto 30px;
}

.setup-stepper span {
  position: relative;
  display: grid;
  justify-items: center;
  gap: 9px;
  color: rgba(255, 245, 230, 0.62);
  font-size: 15px;
  font-weight: 900;
}

.setup-stepper span:not(:last-child)::after {
  content: "";
  position: absolute;
  top: 21px;
  left: calc(50% + 34px);
  width: calc(100% - 44px);
  border-top: 1px dashed rgba(255, 219, 228, 0.3);
}

.setup-stepper b {
  width: 46px;
  height: 46px;
  display: grid;
  place-items: center;
  border-radius: 50%;
  border: 1px solid rgba(255, 255, 255, 0.14);
  background: rgba(255, 255, 255, 0.08);
  color: rgba(255, 245, 230, 0.76);
  font-size: 18px;
}

.setup-stepper .done b {
  color: #ffd37a;
}

.setup-stepper .active {
  color: #fff7df;
}

.setup-stepper .active b {
  border: 0;
  color: #fff;
  background: linear-gradient(90deg, #f84f9b 0%, #ff8a57 100%);
  box-shadow: 0 0 0 6px rgba(248, 79, 155, 0.14), 0 0 24px rgba(248, 79, 155, 0.42);
}

.userinfo-heading {
  display: grid;
  grid-template-columns: minmax(0, 1fr) minmax(180px, 260px);
  gap: 26px;
  align-items: center;
  margin-bottom: 24px;
}

.userinfo-heading h2 {
  margin: 0;
  color: #fff7df;
  font-size: clamp(32px, 3vw, 50px);
  line-height: 1.18;
  letter-spacing: -0.02em;
}

.userinfo-heading p {
  max-width: 720px;
  margin: 12px 0 0;
  color: rgba(255, 245, 230, 0.72);
  font-size: clamp(14px, 0.9vw, 18px);
  line-height: 1.55;
}

.mascot-card {
  min-height: 176px;
  display: grid;
  justify-items: center;
  align-content: center;
  gap: 8px;
  padding: 14px;
  border: 0;
  border-radius: 24px;
  background: transparent;
}

.mascot-card img {
  width: 168px;
  height: 128px;
  object-fit: contain;
  filter: drop-shadow(0 18px 22px rgba(5, 2, 18, 0.38));
}

.mascot-card span {
  color: rgba(255, 245, 230, 0.78);
  font-size: 13px;
  font-weight: 850;
  text-align: center;
}

.setup-form {
  display: grid;
  gap: 20px;
}

.basic-info-card {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 18px 28px;
  padding: 18px;
  border: 1px solid rgba(255, 116, 180, 0.22);
  border-radius: 22px;
  background: rgba(73, 27, 88, 0.3);
}

.profile-column {
  min-width: 0;
  display: grid;
  gap: 16px;
}

.field {
  min-width: 0;
  display: grid;
  gap: 9px;
}

.field > span {
  color: #fff7df;
  font-size: 15px;
  font-weight: 900;
}

.field input {
  width: 100%;
  min-height: 54px;
  padding: 0 18px;
  border: 1px solid rgba(255, 116, 180, 0.34);
  border-radius: 14px;
  background: rgba(255, 255, 255, 0.06);
  color: #fffaf0;
  outline: 0;
}

.field input:focus {
  border-color: rgba(255, 129, 150, 0.72);
  box-shadow: 0 0 0 4px rgba(248, 79, 155, 0.14);
}

.gender-toggle {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 10px;
}

.gender-toggle button {
  position: relative;
  min-width: 0;
  min-height: 54px;
  border: 1px solid rgba(255, 116, 180, 0.26);
  border-radius: 14px;
  background: rgba(255, 255, 255, 0.055);
  color: rgba(255, 245, 230, 0.78);
  font-size: 15px;
  font-weight: 950;
  white-space: nowrap;
  cursor: pointer;
}

.gender-toggle button.active {
  color: #fff;
  border-color: rgba(255, 129, 150, 0.72);
  background: linear-gradient(90deg, rgba(248, 79, 155, 0.7), rgba(255, 138, 87, 0.48));
}

.gender-toggle i {
  position: absolute;
  right: 10px;
  top: 50%;
  transform: translateY(-50%);
  color: #ffd37a;
  font-style: normal;
}

.preference-card {
  display: grid;
  gap: 18px;
  padding: 18px;
  border: 1px solid rgba(255, 116, 180, 0.24);
  border-radius: 22px;
  background: rgba(71, 25, 86, 0.48);
}

.agreement-card {
  display: grid;
  gap: 14px;
  padding: 18px;
  border: 1px solid rgba(255, 116, 180, 0.24);
  border-radius: 22px;
  background: rgba(73, 27, 88, 0.42);
}

.agreement-card header {
  display: flex;
  align-items: end;
  justify-content: space-between;
  gap: 14px;
}

.agreement-card header p {
  margin: 0 0 6px;
  color: #f84f9b;
  font-size: 13px;
  font-weight: 950;
}

.agreement-card h3 {
  margin: 0;
  color: #fff7df;
  font-size: clamp(22px, 1.6vw, 28px);
}

.agreement-card header > span {
  color: #ffd37a;
  font-size: 14px;
  font-weight: 950;
  white-space: nowrap;
}

.agreement-desc,
.agreement-help {
  margin: 0;
  color: rgba(255, 245, 230, 0.68);
  line-height: 1.5;
}

.agreement-help {
  color: #ffb09a;
  font-size: 13px;
  font-weight: 850;
}

.agreement-list {
  display: grid;
  gap: 10px;
}

.agreement-row {
  min-width: 0;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  padding: 12px 14px;
  border: 1px solid rgba(255, 116, 180, 0.18);
  border-radius: 16px;
  background: rgba(255, 255, 255, 0.045);
}

.agreement-row label {
  min-width: 0;
  display: flex;
  align-items: center;
  gap: 10px;
  color: #fff7df;
  cursor: pointer;
}

.agreement-row input {
  width: 20px;
  height: 20px;
  flex: 0 0 auto;
  accent-color: #f84f9b;
}

.agreement-row strong {
  min-width: 0;
  line-height: 1.4;
}

.required-badge {
  flex: 0 0 auto;
  padding: 4px 8px;
  border-radius: 999px;
  background: rgba(248, 79, 155, 0.18);
  color: #ffd37a;
  font-size: 12px;
  font-weight: 950;
}

.agreement-row button {
  flex: 0 0 auto;
  min-height: 34px;
  padding: 0 12px;
  border: 1px solid rgba(255, 116, 180, 0.24);
  border-radius: 999px;
  background: rgba(255, 255, 255, 0.055);
  color: #fff7df;
  font-size: 13px;
  font-weight: 900;
  cursor: pointer;
}

.preference-heading,
.keyword-vault header {
  display: flex;
  align-items: end;
  justify-content: space-between;
  gap: 16px;
}

.preference-heading p {
  margin: 0 0 6px;
  color: #f84f9b;
  font-size: 13px;
  font-weight: 950;
}

.preference-heading h3,
.keyword-vault h3 {
  margin: 0;
  color: #fff7df;
  font-size: clamp(22px, 1.8vw, 30px);
  line-height: 1.25;
}

.preference-heading > span {
  color: #ffd37a;
  font-size: 14px;
  font-weight: 950;
  white-space: nowrap;
}

.preference-heading-actions {
  display: inline-flex;
  align-items: center;
  justify-content: flex-end;
  gap: 10px;
}

.preference-reset-button {
  min-height: 32px;
  padding: 0 12px;
  border: 1px solid rgba(255, 211, 122, 0.38);
  border-radius: 999px;
  background: rgba(255, 255, 255, 0.06);
  color: #ffe0a4;
  font-size: 12px;
  font-weight: 900;
  cursor: pointer;
}

.preference-reset-button:hover {
  border-color: rgba(255, 211, 122, 0.74);
  background: rgba(255, 211, 122, 0.14);
}

.preference-tabs {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 12px;
  padding: 6px;
  border-radius: 16px;
  background: rgba(255, 255, 255, 0.045);
}

.preference-tabs button {
  min-height: 54px;
  border: 0;
  border-radius: 13px;
  background: transparent;
  color: rgba(255, 245, 230, 0.74);
  font-size: 15px;
  font-weight: 950;
  cursor: pointer;
}

.preference-tabs button.active {
  color: #fff;
  background: linear-gradient(90deg, #f84f9b 0%, #ff8a57 100%);
  box-shadow: 0 12px 28px rgba(248, 79, 155, 0.24);
}

.preference-category-row {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.preference-category-row button {
  min-height: 36px;
  padding: 0 15px;
  border: 1px solid rgba(255, 116, 180, 0.22);
  border-radius: 999px;
  background: rgba(255, 255, 255, 0.045);
  color: rgba(255, 245, 230, 0.8);
  font-size: 13px;
  font-weight: 900;
  white-space: nowrap;
  cursor: pointer;
}

.preference-category-row button.active {
  color: #fff;
  border-color: transparent;
  background: linear-gradient(90deg, #f84f9b 0%, #ff8a57 100%);
}

.preference-chip-grid {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 12px;
}

.preference-choice-chip {
  position: relative;
  min-height: 58px;
  justify-content: flex-start;
  gap: 10px;
  padding: 0 44px 0 16px;
  border-radius: 14px;
}

.preference-choice-chip .chip-icon {
  font-size: 18px;
}

.preference-choice-chip strong {
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
}

.preference-choice-chip i {
  position: absolute;
  right: 12px;
  top: 50%;
  width: 22px;
  height: 22px;
  display: grid;
  place-items: center;
  transform: translateY(-50%);
  border-radius: 50%;
  background: rgba(255, 255, 255, 0.22);
  color: #fff;
  font-size: 13px;
  font-style: normal;
  font-weight: 950;
}

.selected-fragments {
  display: grid;
  gap: 10px;
  padding-top: 14px;
  border-top: 1px solid rgba(255, 116, 180, 0.16);
}

.selected-fragments header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}

.selected-fragments h4 {
  margin: 0;
  color: #fff7df;
  font-size: 16px;
}

.selected-fragments p {
  margin: 0;
  color: rgba(255, 245, 230, 0.66);
  font-size: 13px;
  line-height: 1.45;
}

.featured-preference-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 18px;
}

.featured-preference-grid h4 {
  margin: 0 0 12px;
  color: rgba(255, 245, 230, 0.86);
  font-size: 17px;
}

.featured-card-row {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 10px;
}

.featured-keyword-card {
  position: relative;
  min-height: 94px;
  display: grid;
  place-items: center;
  gap: 6px;
  padding: 14px 10px;
  border: 1px solid rgba(255, 116, 180, 0.24);
  border-radius: 16px;
  background: rgba(255, 255, 255, 0.055);
  color: #fffaf0;
  cursor: pointer;
}

.featured-keyword-card.selected {
  border-color: rgba(255, 129, 150, 0.72);
  background:
    linear-gradient(145deg, rgba(248, 79, 155, 0.38), rgba(255, 138, 87, 0.22)),
    rgba(255, 255, 255, 0.06);
  box-shadow: 0 0 22px rgba(248, 79, 155, 0.24);
}

.featured-keyword-card > span {
  font-size: 28px;
}

.featured-keyword-card strong {
  min-width: 0;
  font-size: 14px;
  line-height: 1.25;
  text-align: center;
}

.featured-keyword-card i {
  position: absolute;
  right: 8px;
  top: 8px;
  width: 24px;
  height: 24px;
  display: grid;
  place-items: center;
  border-radius: 50%;
  background: linear-gradient(90deg, #f84f9b 0%, #ff8a57 100%);
  color: #fff;
  font-style: normal;
  font-weight: 950;
}

.keyword-vault {
  display: grid;
  gap: 10px;
}

.keyword-vault p {
  margin: 6px 0 0;
  color: rgba(255, 245, 230, 0.62);
  font-size: 13px;
}

.vault-actions {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  justify-content: flex-end;
}

.vault-actions button {
  min-height: 38px;
  padding: 0 14px;
  border: 1px solid rgba(255, 116, 180, 0.28);
  border-radius: 999px;
  background: rgba(255, 255, 255, 0.055);
  color: #fff7df;
  font-size: 13px;
  font-weight: 900;
  white-space: nowrap;
  cursor: pointer;
}

.keyword-group-card {
  display: grid;
  grid-template-columns: 150px minmax(0, 1fr);
  gap: 14px;
  align-items: center;
  padding: 12px 14px;
  border: 1px solid rgba(255, 116, 180, 0.16);
  border-radius: 16px;
  background: rgba(255, 255, 255, 0.04);
}

.keyword-group-card > strong {
  color: #ffd37a;
  font-size: 16px;
  line-height: 1.3;
}

.keyword-group-card > strong span {
  margin-right: 8px;
}

.keyword-group-card > div,
.selected-chip-row,
.selected-keyword-row {
  min-width: 0;
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.keyword-chip,
.selected-chip-row button,
.selected-keyword-pill {
  min-width: 0;
  min-height: 34px;
  padding: 0 13px;
  border: 1px solid rgba(255, 116, 180, 0.22);
  border-radius: 999px;
  background: rgba(255, 255, 255, 0.055);
  color: rgba(255, 245, 230, 0.84);
  font-size: 13px;
  font-weight: 850;
  white-space: nowrap;
  cursor: pointer;
}

.keyword-chip.selected {
  border-color: transparent;
  color: #fff;
  background: linear-gradient(90deg, #f84f9b 0%, #ff8a57 100%);
}

.selected-summary-card {
  display: grid;
  grid-template-columns: 220px minmax(0, 1fr) minmax(260px, 300px);
  gap: 16px;
  align-items: center;
  padding: 18px;
  border: 1px solid rgba(255, 116, 180, 0.24);
  border-radius: 24px;
  background: rgba(73, 27, 88, 0.42);
}

.summary-title {
  display: flex;
  align-items: center;
  gap: 12px;
}

.summary-icon {
  width: 58px;
  height: 58px;
  display: grid;
  place-items: center;
  border-radius: 18px;
  background: rgba(255, 255, 255, 0.08);
  font-size: 30px;
}

.summary-title strong {
  color: #fff7df;
  font-size: 16px;
}

.summary-title p {
  margin: 4px 0 0;
  color: #ffd37a;
  font-size: 13px;
  font-weight: 900;
}

.summary-action {
  display: grid;
  gap: 8px;
}

.summary-action .btn {
  min-width: 260px;
  min-height: 60px;
  font-size: 16px;
}

.save-error {
  margin: 0;
  color: #ffb09a;
  font-size: 13px;
  font-weight: 850;
}

.keyword-modal-backdrop {
  position: fixed;
  inset: 0;
  z-index: 300;
  display: grid;
  place-items: center;
  padding: 24px;
  background: rgba(8, 3, 22, 0.62);
  backdrop-filter: blur(12px);
}

.agreement-modal-backdrop {
  position: fixed;
  inset: 0;
  z-index: 320;
  display: grid;
  place-items: center;
  padding: 24px;
  background: rgba(8, 3, 22, 0.62);
  backdrop-filter: blur(12px);
}

.agreement-modal {
  width: min(620px, 100%);
  display: grid;
  gap: 16px;
  padding: 24px;
  border: 1px solid rgba(255, 116, 180, 0.32);
  border-radius: 26px;
  background: rgba(38, 14, 60, 0.96);
  box-shadow: 0 30px 90px rgba(0, 0, 0, 0.42);
}

.agreement-modal-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
}

.agreement-modal-header h3 {
  margin: 0;
  color: #fff7df;
  font-size: 24px;
}

.agreement-modal-header button {
  width: 42px;
  height: 42px;
  border: 0;
  border-radius: 50%;
  background: rgba(255, 255, 255, 0.08);
  color: #fff;
  font-size: 24px;
  cursor: pointer;
}

.agreement-modal-content {
  display: grid;
  gap: 10px;
  max-height: min(52vh, 360px);
  overflow: auto;
  padding: 16px;
  border: 1px solid rgba(255, 116, 180, 0.18);
  border-radius: 18px;
  background: rgba(255, 255, 255, 0.045);
}

.agreement-modal-content p {
  margin: 0;
  color: rgba(255, 245, 230, 0.78);
  line-height: 1.65;
}

.keyword-modal {
  width: min(920px, 100%);
  max-height: min(760px, calc(100dvh - 48px));
  display: grid;
  grid-template-rows: auto auto minmax(0, 1fr) auto;
  gap: 16px;
  padding: 24px;
  border: 1px solid rgba(255, 116, 180, 0.32);
  border-radius: 26px;
  background: rgba(38, 14, 60, 0.96);
  box-shadow: 0 30px 90px rgba(0, 0, 0, 0.42);
}

.keyword-modal-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
}

.keyword-modal-header h3 {
  margin: 0;
  color: #fff7df;
  font-size: 24px;
}

.keyword-modal-header button {
  width: 42px;
  height: 42px;
  border: 0;
  border-radius: 50%;
  background: rgba(255, 255, 255, 0.08);
  color: #fff;
  font-size: 24px;
  cursor: pointer;
}

.keyword-search {
  position: relative;
}

.keyword-search input {
  width: 100%;
  min-height: 52px;
  padding: 0 48px 0 16px;
  border: 1px solid rgba(255, 116, 180, 0.28);
  border-radius: 16px;
  background: rgba(255, 255, 255, 0.06);
  color: #fff;
  outline: 0;
}

.keyword-search span {
  position: absolute;
  right: 18px;
  top: 50%;
  transform: translateY(-50%);
  color: rgba(255, 245, 230, 0.62);
}

.modal-keyword-list {
  min-height: 0;
  display: flex;
  flex-wrap: wrap;
  align-content: flex-start;
  gap: 10px;
  overflow: auto;
  padding-right: 6px;
}

.keyword-modal-footer {
  display: grid;
  gap: 12px;
  padding-top: 14px;
  border-top: 1px solid rgba(255, 255, 255, 0.1);
}

.keyword-modal-footer strong {
  color: #fff;
}

.modal-complete-button {
  min-height: 54px;
  border: 0;
  border-radius: 999px;
  background: linear-gradient(90deg, #f84f9b 0%, #ff8a57 100%);
  color: #fff;
  font-size: 16px;
  font-weight: 950;
  cursor: pointer;
}

.empty-keyword-message {
  color: rgba(255, 245, 230, 0.66);
}

@media (max-width: 1180px) {
  .userinfo-setup-view {
    width: min(100% - 28px, 860px);
  }

  .userinfo-heading,
  .basic-info-card,
  .preference-chip-grid,
  .featured-preference-grid,
  .selected-summary-card {
    grid-template-columns: 1fr;
  }

  .mascot-card {
    justify-self: start;
    width: min(260px, 100%);
  }

  .summary-action .btn {
    width: min(360px, 100%);
  }
}

@media (max-width: 760px) {
  .userinfo-panel {
    padding: 22px;
  }

  .setup-stepper {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }

  .setup-stepper span::after {
    display: none;
  }

  .gender-toggle,
  .preference-tabs,
  .featured-card-row,
  .keyword-group-card {
    grid-template-columns: 1fr;
  }

  .preference-heading,
  .keyword-vault header,
  .agreement-card header,
  .agreement-row {
    display: grid;
  }
}

:global(#app .userinfo-setup-view) {
  width: 100% !important;
  max-width: none !important;
  padding: clamp(26px, 4vh, 54px) clamp(18px, 4vw, 52px) 72px !important;
}

:global(#app .userinfo-setup-view .userinfo-panel) {
  width: min(100%, 1120px) !important;
  margin: 0 auto !important;
}

.userinfo-panel {
  padding: clamp(38px, 4.2vw, 62px);
  border: 1px solid rgba(255, 151, 197, 0.24);
  border-radius: 28px;
  background:
    radial-gradient(circle at 18% 0%, rgba(255, 87, 166, 0.12), transparent 32%),
    radial-gradient(circle at 86% 20%, rgba(255, 145, 92, 0.12), transparent 28%),
    linear-gradient(145deg, rgba(31, 14, 59, 0.9), rgba(38, 13, 57, 0.88) 48%, rgba(23, 10, 44, 0.92));
  box-shadow:
    0 30px 90px rgba(7, 2, 26, 0.34),
    inset 0 1px 0 rgba(255, 245, 238, 0.12);
  backdrop-filter: blur(20px) saturate(132%);
}

.setup-stepper {
  max-width: 720px;
  margin-bottom: clamp(42px, 5vw, 72px);
}

.setup-stepper span {
  gap: 10px;
  font-size: 14px;
}

.setup-stepper b {
  width: 44px;
  height: 44px;
}

.setup-stepper span:not(:last-child)::after {
  top: 21px;
  left: calc(50% + 32px);
  width: calc(100% - 52px);
}

.userinfo-heading {
  grid-template-columns: minmax(0, 1fr) 220px;
  gap: 24px;
  align-items: start;
  margin-bottom: 34px;
}

.userinfo-heading h2 {
  max-width: 690px;
  font-size: clamp(38px, 4.3vw, 56px);
  letter-spacing: 0;
}

.heading-title {
  white-space: nowrap;
}

.heading-title h2 {
  display: inline;
  max-width: none;
}

.sparkle-mark {
  display: inline-block;
  margin-left: 8px;
  color: #ffcf72;
  font-size: clamp(36px, 4vw, 52px);
  line-height: 1;
  filter: drop-shadow(0 0 18px rgba(255, 142, 87, 0.38));
}

.userinfo-heading .text-area :is(h2, p, .sparkle-mark) {
  cursor: default;
  user-select: none;
}

.mascot-card {
  min-height: 170px;
  padding-top: 0;
}

.mascot-card img {
  width: 150px;
  height: 122px;
}

.setup-form {
  gap: 18px;
}

.form-grid {
  display: grid;
  grid-template-columns: minmax(0, 0.92fr) minmax(0, 1.18fr);
  gap: 16px;
  align-items: stretch;
}

.basic-info-card,
.preference-card,
.agreement-card {
  border-color: rgba(255, 116, 180, 0.22);
  background:
    linear-gradient(145deg, rgba(255, 255, 255, 0.055), rgba(255, 255, 255, 0.018)),
    rgba(64, 25, 83, 0.36);
  box-shadow: inset 0 1px 0 rgba(255, 245, 238, 0.07);
}

.basic-info-card {
  grid-template-columns: 1fr;
  gap: 18px;
  align-content: start;
  padding: 22px;
  border-radius: 20px;
}

.preference-card {
  gap: 14px;
  padding: 22px;
  border-radius: 20px;
}

.section-heading h3,
.preference-heading h3 {
  margin: 0;
  color: #fff7df;
  font-size: clamp(22px, 2vw, 28px);
  line-height: 1.25;
  letter-spacing: 0;
}

.section-heading p,
.preference-heading p {
  margin: 8px 0 0;
  color: rgba(255, 245, 230, 0.66);
  font-size: 14px;
  line-height: 1.45;
}

.field {
  gap: 10px;
}

.field > span {
  font-size: 14px;
}

.field input {
  min-height: 54px;
  border-color: rgba(255, 122, 181, 0.24);
  background: rgba(255, 255, 255, 0.045);
  box-shadow: inset 0 1px 0 rgba(255, 245, 238, 0.05);
}

.input-with-icon {
  position: relative;
  display: block;
}

.input-with-icon input {
  padding-right: 48px;
}

.input-with-icon > span {
  position: absolute;
  right: 16px;
  top: 50%;
  transform: translateY(-50%);
  color: rgba(255, 245, 230, 0.66);
  font-size: 14px;
  pointer-events: none;
}

.gender-toggle {
  gap: 10px;
}

.gender-toggle button {
  min-height: 52px;
  border-radius: 13px;
}

.lock-note,
.preference-limit {
  margin: auto 0 0;
  color: rgba(255, 245, 230, 0.58);
  font-size: 13px;
  line-height: 1.45;
}

.preference-heading {
  align-items: start;
}

.preference-heading > span {
  padding-top: 6px;
  font-size: 14px;
}

.preference-tabs {
  gap: 0;
  padding: 0;
  border-radius: 14px;
  overflow: hidden;
  background: rgba(255, 255, 255, 0.04);
}

.preference-tabs button {
  min-height: 48px;
  border-radius: 12px;
  font-size: 14px;
}

.preference-category-row {
  gap: 7px;
}

.preference-category-row button {
  min-height: 32px;
  padding: 0 12px;
  font-size: 13px;
}

.preference-chip-grid {
  grid-template-columns: repeat(2, minmax(0, 1fr));
  grid-auto-rows: minmax(44px, auto);
  gap: 9px;
  align-content: start;
  min-height: 330px;
  max-height: 330px;
  overflow-x: hidden;
  overflow-y: auto;
  padding-top: 2px;
  padding-right: 4px;
  scrollbar-width: thin;
  scrollbar-color: rgba(255, 129, 150, 0.58) rgba(255, 255, 255, 0.06);
}

:global(#app .userinfo-setup-view .preference-chip-grid) {
  max-height: 330px !important;
  overflow-x: hidden !important;
  overflow-y: auto !important;
}

.preference-chip-grid::-webkit-scrollbar {
  width: 6px;
}

.preference-chip-grid::-webkit-scrollbar-track {
  border-radius: 999px;
  background: rgba(255, 255, 255, 0.06);
}

.preference-chip-grid::-webkit-scrollbar-thumb {
  border-radius: 999px;
  background: linear-gradient(180deg, rgba(248, 79, 155, 0.72), rgba(255, 138, 87, 0.72));
}

.preference-choice-chip {
  width: 100%;
  height: auto;
  min-height: 44px;
  display: grid;
  grid-template-columns: 18px minmax(0, 1fr) 18px;
  align-items: center;
  padding: 0 10px 0 13px;
  border-radius: 999px;
  background: rgba(255, 255, 255, 0.045);
  font-size: 13px;
}

.preference-choice-placeholder {
  display: block;
  width: 100%;
  min-height: 44px;
  visibility: hidden;
  pointer-events: none;
}

.preference-choice-chip .chip-icon {
  font-size: 14px;
}

.preference-choice-chip strong {
  font-size: 13px;
  font-weight: 850;
  overflow: visible;
  text-overflow: clip;
  white-space: normal;
  word-break: keep-all;
  line-height: 1.32;
}

.preference-choice-chip i {
  position: static;
  right: auto;
  justify-self: end;
  width: 18px;
  height: 18px;
  font-size: 12px;
  transform: none;
}

.preference-choice-box {
  display: grid;
  gap: 12px;
  padding: 14px;
  border: 1px solid rgba(255, 116, 180, 0.24);
  border-radius: 18px;
  background:
    linear-gradient(145deg, rgba(255, 255, 255, 0.058), rgba(255, 255, 255, 0.018)),
    rgba(37, 10, 58, 0.38);
  box-shadow:
    inset 0 1px 0 rgba(255, 245, 238, 0.07),
    0 14px 30px rgba(18, 4, 35, 0.16);
}

.preference-choice-box-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  padding-bottom: 2px;
}

.preference-choice-box-header strong {
  color: #fff7df;
  font-size: 15px;
  font-weight: 950;
}

.preference-choice-box-header em {
  min-height: 28px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  padding: 0 11px;
  border: 1px solid rgba(255, 211, 122, 0.22);
  border-radius: 999px;
  background: rgba(255, 211, 122, 0.09);
  color: #ffd37a;
  font-size: 13px;
  font-style: normal;
  font-weight: 950;
  white-space: nowrap;
}

.selected-fragments {
  display: grid;
  gap: 11px;
  margin-top: 2px;
  padding: 14px;
  border: 1px solid rgba(255, 116, 180, 0.22);
  border-radius: 18px;
  background:
    linear-gradient(145deg, rgba(248, 79, 155, 0.09), rgba(255, 138, 87, 0.045)),
    rgba(255, 255, 255, 0.035);
  box-shadow: inset 0 1px 0 rgba(255, 245, 238, 0.06);
}

.selected-fragments header {
  display: flex;
  align-items: start;
  justify-content: space-between;
  gap: 12px;
}

.selected-fragments h4 {
  margin: 0;
  color: #fff7df;
  font-size: 15px;
  font-weight: 950;
}

.selected-fragments p {
  margin: 4px 0 0;
  color: rgba(255, 245, 230, 0.62);
  font-size: 13px;
  line-height: 1.45;
}

.selected-fragments header > span {
  color: #ffd37a;
  font-size: 13px;
  font-weight: 900;
  line-height: 1.45;
  text-align: right;
}

.selected-fragments .selected-keyword-row {
  gap: 7px;
}

.selected-fragments .selected-keyword-pill {
  min-height: 30px;
  padding: 0 10px;
  border-color: rgba(255, 211, 122, 0.22);
  background: rgba(255, 255, 255, 0.065);
  color: rgba(255, 245, 230, 0.88);
  font-size: 13px;
}

.selected-fragments .selected-keyword-pill span {
  margin-right: 4px;
}

.selected-fragments .selected-keyword-pill i {
  margin-left: 5px;
  color: #ffd37a;
  font-style: normal;
  font-weight: 950;
}

.empty-selected-message {
  padding: 10px 12px;
  border: 1px dashed rgba(255, 116, 180, 0.2);
  border-radius: 14px;
  background: rgba(255, 255, 255, 0.028);
}

.agreement-card {
  gap: 12px;
  padding: 22px;
  border-radius: 20px;
}

.agreement-card header p {
  margin-bottom: 5px;
  font-size: 12px;
}

.agreement-card h3 {
  font-size: clamp(24px, 2.2vw, 31px);
  letter-spacing: 0;
}

.agreement-row {
  min-height: 56px;
  padding: 10px 14px;
}

.setup-submit-row {
  display: grid;
  justify-items: end;
  gap: 10px;
  padding-top: 4px;
}

.setup-submit-row .btn {
  width: min(360px, 100%);
  min-height: 64px;
  border: 0;
  border-radius: 16px;
  background: linear-gradient(90deg, #f84f9b 0%, #ff6f7a 54%, #ff8a57 100%);
  color: #fff;
  font-size: 17px;
  font-weight: 950;
  box-shadow: 0 18px 44px rgba(248, 79, 155, 0.26);
}

.setup-submit-row .btn:disabled {
  cursor: not-allowed;
  opacity: 0.58;
  filter: saturate(0.75);
}

@media (max-width: 1120px) {
  .form-grid,
  .userinfo-heading {
    grid-template-columns: 1fr;
  }

  .mascot-card {
    justify-self: start;
  }
}

@media (max-width: 760px) {
  :global(#app .userinfo-setup-view) {
    padding-inline: 12px !important;
  }

  .userinfo-panel {
    padding: 22px 16px;
    border-radius: 24px;
  }

  .userinfo-heading h2 {
    font-size: 34px;
  }

  .preference-chip-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
    min-height: calc((38px * 8) + (9px * 7));
    max-height: calc((38px * 8) + (9px * 7));
  }

  :global(#app .userinfo-setup-view .preference-chip-grid) {
    max-height: calc((38px * 8) + (9px * 7)) !important;
  }

  .selected-fragments header {
    display: grid;
  }

  .selected-fragments header > span {
    text-align: left;
  }

  .agreement-row {
    display: grid;
    justify-items: start;
  }

  .setup-submit-row {
    justify-items: stretch;
  }

  .setup-submit-row .btn {
    width: 100%;
  }
}
</style>

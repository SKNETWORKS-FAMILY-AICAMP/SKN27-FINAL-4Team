<script setup>
import { computed, ref } from "vue";
import { userApi } from "../../api/user.js";
import hobbyCsv from "../../assets/data/onboarding/preference_hobbies.csv?raw";
import interestCsv from "../../assets/data/onboarding/preference_interests.csv?raw";

const emit = defineEmits(["navigate"]);

const FEATURE_HOBBY_LABELS = ["음악 감상", "카페 투어", "산책", "요리"];
const FEATURE_INTEREST_LABELS = ["심리", "반려동물", "드라마", "디지털 트렌드"];
const VAULT_GROUP_CONFIG = [
  { title: "취미", icon: "🎵", type: "hobby", labels: ["독서", "영화 감상", "운동", "사진 찍기", "요리", "드로잉", "게임", "악기 연주"] },
  { title: "관심 분야", icon: "⭐", type: "interest", labels: ["심리", "반려동물", "K-POP", "자기계발", "다큐멘터리", "댄스/퍼포먼스", "드라마", "디지털 트렌드"] },
  { title: "라이프스타일", icon: "🌿", type: "interest", labels: ["여행/외출", "감성/무드", "건강/운동", "패션/뷰티", "인테리어", "맛집/카페", "환경/지속가능", "문화/예술"] },
  { title: "학습/성장", icon: "🎓", type: "hobby", labels: ["외국어 학습", "글쓰기", "프로그래밍", "디자인", "마케팅", "창업", "자격증", "독서 모임"] },
];

const hobbyItems = parseKeywordCsv(hobbyCsv, "hobby");
const interestItems = parseKeywordCsv(interestCsv, "interest");
const storedProfile = getStoredProfile();

const profileForm = ref({
  nickname: storedProfile.nickname || "별빛소년",
  birthDate: formatBirthDateForDisplay(storedProfile.birth_date) || storedProfile.birthDate || storedProfile.birthday || "1997.05.21",
  gender: storedProfile.gender || "남",
  job: storedProfile.job || "UI/UX 디자이너",
});

const genderOptions = ["남", "여", "선택 안 함"];
const selectedHobbies = ref(storedProfile.hobbies?.length ? storedProfile.hobbies : ["음악 감상", "카페 투어", "산책"]);
const selectedInterests = ref(storedProfile.interests?.length ? storedProfile.interests : ["심리", "반려동물", "드라마", "디지털 트렌드"]);
const isSaving = ref(false);
const saveError = ref("");
const activeKeywordModal = ref(null);
const keywordSearchQuery = ref("");

const selectedPreferenceLabels = computed(() => [...selectedHobbies.value, ...selectedInterests.value]);
const featureHobbyItems = computed(() => FEATURE_HOBBY_LABELS.map((label) => getKeywordItem(label, "hobby")));
const featureInterestItems = computed(() => FEATURE_INTEREST_LABELS.map((label) => getKeywordItem(label, "interest")));
const vaultGroups = computed(() => VAULT_GROUP_CONFIG.map((group) => ({
  ...group,
  items: group.labels.map((label) => getKeywordItem(label, group.type)),
})));
const activeModalItems = computed(() => activeKeywordModal.value === "hobby" ? hobbyItems : interestItems);
const activeModalSelected = computed(() => activeKeywordModal.value === "hobby" ? selectedHobbies.value : selectedInterests.value);
const activeModalTitle = computed(() => activeKeywordModal.value === "hobby" ? "취미 전체 선택" : "관심분야 전체 선택");
const activeModalCountLabel = computed(() => activeKeywordModal.value === "hobby" ? "선택한 취미" : "선택한 관심분야");
const activeModalPlaceholder = computed(() => activeKeywordModal.value === "hobby" ? "취미 키워드를 검색해보세요" : "관심분야를 검색해보세요");
const filteredModalItems = computed(() => {
  const query = keywordSearchQuery.value.trim().toLowerCase();
  const items = activeModalItems.value;

  if (query) {
    return items.filter((item) => item.searchText.includes(query));
  }

  return uniqueItems([
    ...items.slice(0, 32),
    ...featureHobbyItems.value,
    ...featureInterestItems.value,
  ]).filter((item) => item.type === activeKeywordModal.value);
});

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
    relatedKeywords,
    sortOrder: Number(raw.sort_order || raw.sortOrder || 999),
    popularityScore: Number(raw.popularity_score || raw.popularityScore || 0),
    searchText,
  };
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
    searchText: label.toLowerCase(),
    sortOrder: 999,
    popularityScore: 0,
  };
}

function uniqueItems(items) {
  const seen = new Set();
  return items.filter((item) => {
    if (!item || seen.has(`${item.type}-${item.label}`)) return false;
    seen.add(`${item.type}-${item.label}`);
    return true;
  });
}

function isKeywordSelected(item) {
  return getSelectedRef(item.type).value.includes(item.label);
}

function toggleKeywordItem(item) {
  const selected = getSelectedRef(item.type);

  if (selected.value.includes(item.label)) {
    selected.value = selected.value.filter((label) => label !== item.label);
    return;
  }

  selected.value.push(item.label);
}

function removeSelectedKeyword(label, type) {
  const selected = getSelectedRef(type);
  selected.value = selected.value.filter((item) => item !== label);
}

function openKeywordModal(type) {
  activeKeywordModal.value = type;
  keywordSearchQuery.value = "";
}

function closeKeywordModal() {
  activeKeywordModal.value = null;
  keywordSearchQuery.value = "";
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

  const profilePayload = {
    nickname,
    birth_date: normalizedBirthDate,
    gender,
    age,
    job: profileForm.value.job.trim(),
    hobbies: selectedHobbies.value,
    interests: selectedInterests.value,
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
    emit("navigate", "home");
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
        <span class="done"><b>✓</b>로그인</span>
        <span class="done"><b>2</b>캐릭터</span>
        <span class="active"><b>3</b>정보와 취향</span>
        <span><b>4</b>완료</span>
      </div>

      <header class="userinfo-heading">
        <div class="text-area">
          <h2>기본 정보와 취향 조각 수집하기 ✨</h2>
          <p>당신에게 맞는 대화를 위해 필요한 정보만 가볍게 입력해 주세요.</p>
        </div>

        <div class="mascot-card image-area" aria-hidden="true">
          <img src="/characters/redpanda/default.png" alt="">
          <span>조금만 알려주면 더 잘 도와줄게요!</span>
        </div>
      </header>

      <form class="setup-form" novalidate @submit.prevent="saveUserInfo">
        <section class="basic-info-card" aria-label="기본 정보 입력">
          <div class="profile-column">
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
              <span>직업</span>
              <input v-model="profileForm.job" type="text" placeholder="직업을 입력해 주세요">
            </label>
          </div>

          <div class="profile-column">
            <label class="field">
              <span>생년월일</span>
              <input
                v-model="profileForm.birthDate"
                class="ltr-input"
                type="text"
                dir="ltr"
                inputmode="numeric"
                maxlength="10"
                placeholder="YYYY.MM.DD"
                @input="normalizeBirthDateInput"
              >
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
          </div>
        </section>

        <section class="preference-card" aria-label="취미와 관심분야 키워드 설정">
          <header class="preference-heading">
            <div>
              <p>Preference fragments</p>
              <h3> 취미와 관심 분야</h3>
            </div>
            <span>선택한 조각 {{ selectedPreferenceLabels.length }}개</span>
          </header>

          <div class="featured-preference-grid">
            <section>
              <h4> 취미</h4>
              <div class="featured-card-row">
                <button
                  v-for="item in featureHobbyItems"
                  :key="item.id"
                  type="button"
                  class="featured-keyword-card"
                  :class="{ selected: isKeywordSelected(item) }"
                  @click="toggleKeywordItem(item)"
                >
                  <span>{{ item.label === "카페 투어" ? "☕" : item.label === "산책" ? "👟" : item.label === "요리" ? "🍳" : "🎵" }}</span>
                  <strong>{{ item.label }}</strong>
                  <i>{{ isKeywordSelected(item) ? "✓" : "+" }}</i>
                </button>
              </div>
            </section>

            <section>
              <h4>관심 분야</h4>
              <div class="featured-card-row">
                <button
                  v-for="item in featureInterestItems"
                  :key="item.id"
                  type="button"
                  class="featured-keyword-card interest"
                  :class="{ selected: isKeywordSelected(item) }"
                  @click="toggleKeywordItem(item)"
                >
                  <span>{{ item.label === "반려동물" ? "🐾" : item.label === "드라마" ? "🎬" : item.label === "디지털 트렌드" ? "💡" : "💗" }}</span>
                  <strong>{{ item.label }}</strong>
                  <i>{{ isKeywordSelected(item) ? "✓" : "+" }}</i>
                </button>
              </div>
            </section>
          </div>

          <section class="keyword-vault" aria-label="전체 키워드 보관함">
            <header>
              <div>
                <h3>전체 키워드 보관함</h3>
                <p>원하는 키워드를 클릭하여 선택해보세요.</p>
              </div>
              <div class="vault-actions">
                <button type="button" @click="openKeywordModal('hobby')">+ 취미 더보기</button>
                <button type="button" @click="openKeywordModal('interest')">+ 관심분야 더보기</button>
              </div>
            </header>

            <article v-for="group in vaultGroups" :key="group.title" class="keyword-group-card">
              <strong><span>{{ group.icon }}</span>{{ group.title }}</strong>
              <div>
                <button
                  v-for="item in group.items"
                  :key="`${group.title}-${item.label}`"
                  type="button"
                  class="keyword-chip"
                  :class="{ selected: isKeywordSelected(item) }"
                  @click="toggleKeywordItem(item)"
                >
                  {{ item.label }} <span>{{ isKeywordSelected(item) ? "✓" : "+" }}</span>
                </button>
              </div>
            </article>
          </section>
        </section>

        <footer class="selected-summary-card">
          <div class="summary-title">
            <span class="summary-icon">🫙</span>
            <div>
              <strong>선택한 취향 조각</strong>
              <p>{{ selectedPreferenceLabels.length }}개 선택 완료!</p>
            </div>
          </div>

          <div class="selected-chip-row">
            <button
              v-for="label in selectedPreferenceLabels.slice(0, 8)"
              :key="label"
              type="button"
              @click="removeSelectedKeyword(label, selectedHobbies.includes(label) ? 'hobby' : 'interest')"
            >
              {{ label }} ×
            </button>
          </div>

          <div class="summary-action">
            <p v-if="saveError" class="save-error">{{ saveError }}</p>
            <button class="btn primary large" type="submit" :disabled="isSaving">
              {{ isSaving ? "저장 중..." : "설정 저장하고 홈으로 ✨" }}
            </button>
          </div>
        </footer>
      </form>
    </article>

    <div v-if="activeKeywordModal" class="keyword-modal-backdrop" @click.self="closeKeywordModal">
      <section class="keyword-modal" role="dialog" aria-modal="true" :aria-label="activeModalTitle">
        <header class="keyword-modal-header">
          <h3>{{ activeModalTitle }}</h3>
          <button type="button" aria-label="닫기" @click="closeKeywordModal">×</button>
        </header>

        <label class="keyword-search">
          <input v-model="keywordSearchQuery" type="search" :placeholder="activeModalPlaceholder">
          <span>⌕</span>
        </label>

        <div class="modal-keyword-list">
          <button
            v-for="item in filteredModalItems"
            :key="item.id"
            type="button"
            class="keyword-chip modal-chip"
            :class="{ selected: isKeywordSelected(item) }"
            @click="toggleKeywordItem(item)"
          >
            {{ item.label }} <span>{{ isKeywordSelected(item) ? "✓" : "+" }}</span>
          </button>
          <p v-if="!filteredModalItems.length" class="empty-keyword-message">검색 결과가 없어요.</p>
        </div>

        <footer class="keyword-modal-footer">
          <strong>{{ activeModalCountLabel }} {{ activeModalSelected.length }}개</strong>
          <div class="selected-keyword-row">
            <button
              v-for="label in activeModalSelected"
              :key="label"
              type="button"
              class="selected-keyword-pill"
              @click="removeSelectedKeyword(label, activeKeywordModal)"
            >
              {{ label }} ×
            </button>
          </div>
          <button class="modal-complete-button" type="button" @click="closeKeywordModal">완료</button>
        </footer>
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
  .featured-card-row,
  .keyword-group-card {
    grid-template-columns: 1fr;
  }

  .preference-heading,
  .keyword-vault header {
    display: grid;
  }
}
</style>

<template>
  <div class="panel-body">
    <div class="profile-info-layout">
      <section class="card profile-card">
        <header class="profile-card-head">
          <div class="profile-portrait" aria-hidden="true">
            <img v-if="currentCharacter" :src="`/characters/${currentCharacter.id}/default.png`" :alt="currentCharacter.name" />
            <span v-else>{{ profileInitial }}</span>
          </div>
          <div class="profile-title">
            <span>ROOM PROFILE</span>
            <h3>{{ profileName }}</h3>
            <p>{{ profileCaption }}</p>
            <div class="profile-badges" aria-label="프로필 요약">
              <span>{{ profile.gender || '성별 미등록' }}</span>
              <span>{{ profile.birthDate || '생년월일 미등록' }}</span>
              <span>{{ currentCharacter?.name || '캐릭터 미선택' }}</span>
              <span>취향 {{ totalTasteCount }}개</span>
            </div>
          </div>
          <button class="profile-edit-button" type="button" @click="handleEditToggle">
            {{ profileEdit ? '완료' : '수정' }}
          </button>
        </header>

        <section class="profile-section">
          <div class="profile-section-title">
            <span>기본 정보</span>
          </div>
          <div class="form-grid two">
          <div class="field">
            <label for="profile-name">이름 또는 닉네임</label>
            <input id="profile-name" v-model="profile.name" :readonly="!profileEdit" placeholder="이름 또는 닉네임" @input="normalizeNicknameInput" />
          </div>
          <div class="field">
            <label for="profile-job">직업</label>
            <input id="profile-job" v-model="profile.job" placeholder="직업을 입력해 주세요" :readonly="!profileEdit" />
          </div>
          <div class="field">
            <label for="profile-birthdate">생년월일</label>
            <input id="profile-birthdate" v-model="profile.birthDate" placeholder="YYYY.MM.DD" :readonly="!profileEdit" @input="normalizeBirthDateInput" />
          </div>
          <div class="field">
            <label>성별</label>
            <div class="gender-toggle" role="group" aria-label="성별 선택">
              <button
                v-for="gender in ['남', '여', '선택 안 함']"
                :key="gender"
                type="button"
                :class="{ active: profile.gender === gender }"
                @click="profileEdit && (profile.gender = gender)"
                :disabled="!profileEdit"
              >
                {{ gender }}
                <i v-if="profile.gender === gender">✓</i>
              </button>
            </div>
          </div>
        </div>
        </section>

        <section class="profile-section taste-section">
          <div class="profile-section-title">
            <span>취향 조각</span>
            <strong>{{ totalTasteCount }}개 선택</strong>
          </div>
          <div class="form-grid profile-extra-grid">
          <section class="field interest-keyword-field picker-field" aria-label="관심분야 설정">
            <div class="interest-keyword-head">
              <label>관심분야 키워드</label>
              <strong>{{ profile.interests.length }}개 선택</strong>
            </div>
            <div class="interest-keyword-list">
              <span
                v-for="keyword in profile.interests"
                :key="keyword"
                class="interest-chip active"
              >
                {{ getKeywordIcon(keyword, 'interest') }} {{ keyword }}
              </span>
              <button 
                v-if="profileEdit"
                type="button" 
                class="add-button" 
                @click="togglePicker('interest')"
              >
                + 수정
              </button>
            </div>
            <!-- 관심분야 드롭다운 패널 -->
            <div v-if="activePicker === 'interest'" class="inline-dropdown">
              <div class="dropdown-header">
                <strong>관심분야 선택 (최대 3개)</strong>
                <button type="button" @click="activePicker = null">×</button>
              </div>
              <div class="dropdown-body">
                <div v-for="(items, category) in interestGroups" :key="category" class="category-group">
                  <div class="category-title">{{ category }}</div>
                  <div class="chip-list">
                     <button v-for="item in items" :key="item.label" 
                             class="interest-chip"
                             :class="{ active: profile.interests.includes(item.label) }"
                             @click.prevent="toggleKeyword('interest', item.label)">
                       {{ getKeywordIcon(item.label, 'interest') }} {{ item.label }}
                     </button>
                  </div>
                </div>
              </div>
            </div>
          </section>

          <section class="field interest-keyword-field picker-field" aria-label="취미 설정">
            <div class="interest-keyword-head">
              <label>취미</label>
              <strong>{{ profile.hobbies.length }}개 선택</strong>
            </div>
            <div class="interest-keyword-list">
              <span
                v-for="keyword in profile.hobbies"
                :key="keyword"
                class="interest-chip active hobby-chip"
              >
                {{ getKeywordIcon(keyword, 'hobby') }} {{ keyword }}
              </span>
              <button 
                v-if="profileEdit"
                type="button" 
                class="add-button" 
                @click="togglePicker('hobby')"
              >
                + 수정
              </button>
            </div>
            <!-- 취미 드롭다운 패널 -->
            <div v-if="activePicker === 'hobby'" class="inline-dropdown">
              <div class="dropdown-header">
                <strong>취미 선택 (최대 3개)</strong>
                <button type="button" @click="activePicker = null">×</button>
              </div>
              <div class="dropdown-body">
                <div v-for="(items, category) in hobbyGroups" :key="category" class="category-group">
                  <div class="category-title">{{ category }}</div>
                  <div class="chip-list">
                     <button v-for="item in items" :key="item.label" 
                             class="interest-chip hobby-chip"
                             :class="{ active: profile.hobbies.includes(item.label) }"
                             @click.prevent="toggleKeyword('hobby', item.label)">
                       {{ getKeywordIcon(item.label, 'hobby') }} {{ item.label }}
                     </button>
                  </div>
                </div>
              </div>
            </div>
          </section>
        </div>
        </section>
        <p v-if="profileSavedAt" class="notice">마지막 저장 시각: {{ profileSavedAt }}</p>
      </section>
    </div>

    <!-- Character picker popup removed as it is now inline -->
  </div>
</template>

<script>
import hobbyCsv from "../../../assets/preference_hobbies.csv?raw";
import interestCsv from "../../../assets/preference_interests.csv?raw";

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

function parseKeywordCsv(csvText, type) {
  const lines = csvText.replace(/^\uFEFF/, "").split(/\r?\n/).filter(Boolean);
  const headers = parseCsvLine(lines.shift() || "");
  
  return lines.map((line) => {
    const values = parseCsvLine(line);
    const raw = Object.fromEntries(headers.map((header, index) => [header, values[index] || ""]));
    const label = type === "hobby"
      ? raw.display_label || raw.label || raw.keyword
      : raw.label || raw.displayLabel || raw.displayText || raw.keyword;
      
    return {
      label,
      category: raw.category || "기타",
    };
  }).filter((item) => item.label);
}

function groupByCategory(items) {
  const map = {};
  items.forEach(item => {
    if (!map[item.category]) map[item.category] = [];
    if (!map[item.category].some(i => i.label === item.label)) {
      map[item.category].push(item);
    }
  });
  return map;
}

export default {
  name: "ProfilePanel",
  props: {
    profile: { type: Object, required: true },
    profileOptions: { type: Object, required: true },
    profileEdit: { type: Boolean, required: true },
    profileSavedAt: { type: String, default: "" },
    selectedCharacter: { type: String, default: "" },
    currentCharacter: { type: Object, default: null },
    characters: { type: Array, default: () => [] },
    showCharacterPicker: { type: Boolean, default: false }
  },
  emits: [
    "open-character-picker",
    "close-character-picker",
    "toggle-profile-edit",
    "choose-character"
  ],
  data() {
    return {
      activePicker: null,
      hobbyGroups: groupByCategory(parseKeywordCsv(hobbyCsv, "hobby")),
      interestGroups: groupByCategory(parseKeywordCsv(interestCsv, "interest"))
    };
  },
  computed: {
    profileName() {
      return String(this.profile?.name || "이름 미입력").trim();
    },
    profileInitial() {
      return this.profileName.slice(0, 1).toUpperCase();
    },
    profileCaption() {
      const job = String(this.profile?.job || "직업 미입력").trim();
      return job;
    },
    totalTasteCount() {
      return (this.profile?.interests?.length || 0) + (this.profile?.hobbies?.length || 0);
    }
  },
  methods: {
    togglePicker(type) {
      this.activePicker = this.activePicker === type ? null : type;
    },
    toggleKeyword(type, label) {
      if (!this.profileEdit) return;
      const targetArray = type === "hobby" ? this.profile.hobbies : this.profile.interests;
      const index = targetArray.indexOf(label);
      
      if (index > -1) {
        targetArray.splice(index, 1);
      } else {
        targetArray.push(label);
      }
    },
    getKeywordIcon(label, type) {
      const text = String(label || "");
      if (/음악|K-POP|발라드|재즈|콘서트|악기|연주/.test(text)) return "🎧";
      if (/산책|러닝|운동|헬스|요가|등산|스포츠/.test(text)) return "🚶";
      if (/카페|커피|차|맛집|요리|베이킹/.test(text)) return "☕";
      if (/영화|드라마|웹툰|예능|애니|콘텐츠|유튜브/.test(text)) return "🎬";
      if (/게임|디지털|트렌드/.test(text)) return "🎮";
      if (/독서|글쓰기|자기계발|학습|심리/.test(text)) return "📚";
      if (/사진|전시|문화|공연|창작|드로잉|표현/.test(text)) return "🖼️";
      if (/반려|동물|식물|가드닝|자연/.test(text)) return "🐾";
      if (/여행|외출|공간|팝업|캠핑/.test(text)) return "🧭";
      if (/패션|뷰티|인테리어|쇼핑/.test(text)) return "✨";
      return type === "hobby" ? "💫" : "🔖";
    },
    normalizeNicknameInput() {
      if (!this.profileEdit) return;
      this.profile.name = String(this.profile.name || "").replace(/[^A-Za-z가-힣]/g, "");
    },
    normalizeBirthDateInput() {
      if (!this.profileEdit) return;
      const digits = String(this.profile.birthDate || "").replace(/\D/g, "").slice(0, 8);
      const parts = [];

      if (digits.length > 0) parts.push(digits.slice(0, 4));
      if (digits.length > 4) parts.push(digits.slice(4, 6));
      if (digits.length > 6) parts.push(digits.slice(6, 8));

      this.profile.birthDate = parts.join(".");
    },
    handleEditToggle() {
      if (!this.profileEdit) {
        this.$emit('toggle-profile-edit');
        return;
      }
      
      const name = String(this.profile.name || "").trim();
      const birth = String(this.profile.birthDate || "").trim();
      
      if (!name || !birth) {
        alert("이름 또는 닉네임, 생년월일을 꼭 입력해 주세요.");
        return;
      }
      
      const match = birth.match(/^(\d{4})\.(\d{2})\.(\d{2})$/);
      if (!match) {
        alert("생년월일은 YYYY.MM.DD 형식으로 입력해 주세요.");
        return;
      }
      
      const totalChips = (this.profile.hobbies?.length || 0) + (this.profile.interests?.length || 0);
      if (totalChips < 3) {
        alert("취향 조각(관심분야, 취미)을 합쳐서 3개 이상 선택해 주세요.");
        return;
      }
      
      this.$emit('toggle-profile-edit');
    }
  },
  watch: {
    profileEdit(newVal) {
      if (!newVal) this.activePicker = null; // 수정 모드 종료 시 패널 닫기
    }
  }
};
</script>

<style scoped>
.picker-field {
  position: relative;
}
.add-button {
  min-height: 32px;
  padding: 0 12px;
  border: 1px dashed rgba(176, 112, 255, 0.72);
  border-radius: 999px;
  background: rgba(255, 255, 255, 0.12);
  color: #e1c5ff;
  font-weight: bold;
  font-size: 13px;
  cursor: pointer;
  margin-top: 4px;
}
.inline-dropdown {
  position: absolute;
  bottom: calc(100% + 8px);
  left: 0;
  width: 100%;
  max-width: 440px;
  max-height: 360px;
  background: linear-gradient(145deg, rgba(42, 26, 98, 0.85), rgba(23, 16, 68, 0.9));
  backdrop-filter: blur(20px);
  -webkit-backdrop-filter: blur(20px);
  border-radius: 12px;
  box-shadow: 0 -8px 30px rgba(0,0,0,0.4), inset 0 1px 0 rgba(255, 188, 226, 0.15);
  z-index: 50;
  display: flex;
  flex-direction: column;
  overflow: hidden;
  border: 1px solid rgba(255, 127, 152, 0.25);
}
.dropdown-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 12px 16px;
  background: rgba(23, 16, 68, 0.4);
  border-bottom: 1px solid rgba(255, 127, 152, 0.15);
  color: #e1c5ff;
}
.dropdown-header button {
  background: none;
  border: none;
  font-size: 20px;
  cursor: pointer;
  color: #b9acd8;
}
.dropdown-body {
  overflow-y: auto;
  padding: 12px;
  display: flex;
  flex-direction: column;
  gap: 16px;
}
.category-group {
  display: flex;
  flex-direction: column;
  gap: 8px;
}
.category-title {
  font-size: 12px;
  font-weight: bold;
  color: #b9acd8;
  padding-left: 4px;
}
.chip-list {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}
.interest-chip {
  padding: 6px 12px;
  border-radius: 999px;
  border: 1px solid rgba(176, 112, 255, 0.3);
  background: rgba(255, 255, 255, 0.05);
  color: #d7b7ff;
  font-size: 13px;
  cursor: pointer;
  transition: all 0.2s ease;
}
.interest-chip.active {
  border-color: rgba(255, 129, 174, 0.8);
  background: linear-gradient(135deg, rgba(255, 112, 168, 0.4), rgba(255, 164, 196, 0.3));
  color: #fff;
  font-weight: bold;
}
.hobby-chip.active {
  border-color: rgba(156, 91, 255, 0.8);
  background: linear-gradient(135deg, rgba(139, 92, 246, 0.4), rgba(167, 139, 250, 0.3));
  color: #fff;
}
.avatar-card {
  padding-top: 32px;
  padding-bottom: 24px;
}
.avatar-card :deep(.character) {
  transform: scale(0.9);
  margin-top: 10px;
  margin-bottom: -10px;
}
.avatar-card :deep(.character-name) {
  margin-top: 12px;
}
.nav-arrow {
  background: rgba(255, 255, 255, 0.1);
  border: 1px solid rgba(255, 255, 255, 0.2);
  border-radius: 50%;
  width: 36px;
  height: 36px;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #e1c5ff;
  font-size: 16px;
  cursor: pointer;
  transition: all 0.2s ease;
  flex-shrink: 0;
}
.nav-arrow:hover {
  background: rgba(255, 255, 255, 0.25);
  transform: scale(1.1);
  color: #fff;
}
.nav-arrow:active {
  transform: scale(0.95);
}
.gender-toggle {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 10px;
}
.gender-toggle button {
  position: relative;
  min-width: 0;
  min-height: 48px;
  border: 1px solid rgba(255, 116, 180, 0.26);
  border-radius: 14px;
  background: rgba(255, 255, 255, 0.055);
  color: rgba(255, 245, 230, 0.78);
  font-size: 15px;
  font-weight: 950;
  white-space: nowrap;
  cursor: pointer;
}
.gender-toggle button:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}
.gender-toggle button.active {
  color: #fff;
  border-color: var(--primary);
  background: linear-gradient(90deg, var(--pur), var(--blue));
}
.gender-toggle i {
  position: absolute;
  right: 10px;
  top: 50%;
  transform: translateY(-50%);
  color: #ffd37a;
  font-style: normal;
}

/* --- Premium UI Overrides --- */
.grid-2 {
  gap: 16px !important;
}
.card {
  border: 1px solid rgba(255, 116, 180, 0.22) !important;
  border-radius: 20px !important;
  background: rgba(73, 27, 88, 0.3) !important;
  padding: 20px !important;
  box-shadow: 0 12px 40px rgba(0, 0, 0, 0.25);
  backdrop-filter: blur(12px);
  -webkit-backdrop-filter: blur(12px);
}
.card h3 {
  font-size: 20px !important;
  color: #fff7df !important;
  margin: 0 !important;
  font-weight: 850 !important;
  letter-spacing: -0.02em;
}

.profile-card {
  display: grid;
  gap: 14px;
}

.profile-card-head {
  display: grid;
  grid-template-columns: 112px minmax(0, 1fr) auto;
  align-items: center;
  gap: 18px;
  min-height: 148px;
  padding: 18px;
  border: 1px solid rgba(255, 247, 223, 0.14);
  border-radius: 18px;
  background:
    radial-gradient(circle at 18% 20%, rgba(255, 211, 122, 0.2), transparent 28%),
    linear-gradient(135deg, rgba(255, 129, 174, 0.18), rgba(156, 91, 255, 0.14)),
    rgba(18, 16, 55, 0.42);
  overflow: hidden;
}

.profile-portrait {
  position: relative;
  display: grid;
  place-items: end center;
  width: 112px;
  height: 112px;
  border: 1px solid rgba(255, 247, 223, 0.24);
  border-radius: 26px;
  background:
    radial-gradient(circle at 50% 78%, rgba(255, 211, 122, 0.24), transparent 36%),
    linear-gradient(145deg, rgba(156, 91, 255, 0.72), rgba(32, 41, 105, 0.76));
  color: #fff7df;
  font-size: 34px;
  font-weight: 950;
  box-shadow: 0 12px 24px rgba(5, 2, 18, 0.24);
  overflow: hidden;
}

.profile-portrait img {
  max-width: 84%;
  max-height: 92%;
  object-fit: contain;
  filter: drop-shadow(0 16px 18px rgba(5, 2, 18, 0.46));
}

.profile-title {
  min-width: 0;
}

.profile-title span {
  display: block;
  color: #d7b7ff;
  font-size: 11px;
  font-weight: 950;
}

.profile-title h3 {
  margin-top: 4px !important;
  font-size: 24px !important;
  line-height: 1.18;
}

.profile-title p {
  margin: 4px 0 0;
  color: rgba(255, 245, 230, 0.66);
  font-size: 13px;
  line-height: 1.35;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.profile-badges {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  margin-top: 12px;
}

.profile-badges span {
  display: inline-flex;
  align-items: center;
  min-height: 28px;
  padding: 0 10px;
  border: 1px solid rgba(215, 183, 255, 0.2);
  border-radius: 999px;
  background: rgba(15, 10, 49, 0.34);
  color: rgba(255, 245, 230, 0.82);
  font-size: 12px;
  font-weight: 800;
}

.profile-edit-button {
  min-height: 38px;
  padding: 0 16px;
  border: 1px solid rgba(215, 183, 255, 0.42);
  border-radius: 12px;
  background: rgba(42, 26, 98, 0.82);
  color: #fff7df;
  font-size: 14px;
  font-weight: 900;
  white-space: nowrap;
}

.profile-edit-button:hover,
.profile-edit-button:focus-visible {
  border-color: rgba(255, 247, 223, 0.58);
  background: linear-gradient(135deg, rgba(156, 91, 255, 0.82), rgba(81, 103, 232, 0.72));
}

.profile-section {
  display: grid;
  gap: 12px;
  padding: 14px;
  border: 1px solid rgba(215, 183, 255, 0.14);
  border-radius: 16px;
  background: rgba(18, 16, 55, 0.26);
}

.profile-section-title {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
}

.profile-section-title span {
  color: #fff7df;
  font-size: 14px;
  font-weight: 900;
}

.profile-section-title strong {
  padding: 4px 10px;
  border: 1px solid rgba(215, 183, 255, 0.2);
  border-radius: 999px;
  background: rgba(32, 41, 105, 0.44);
  color: #d7b7ff;
  font-size: 12px;
  font-weight: 900;
}

/* Avatar Card Refinements */
.avatar-card {
  display: flex !important;
  flex-direction: column !important;
  justify-content: center !important;
  align-items: center !important;
  background: linear-gradient(160deg, rgba(62, 22, 82, 0.6), rgba(26, 13, 44, 0.8)) !important;
  padding-top: 16px !important;
  padding-bottom: 16px !important;
}
.character-preview-wrapper {
  margin-top: 6px;
}
.character-name {
  font-size: 16px !important;
  color: #fff7df !important;
  font-weight: 800 !important;
  margin: 12px 0 16px !important;
  text-shadow: 0 2px 8px rgba(0, 0, 0, 0.6);
  background: rgba(255, 255, 255, 0.1);
  padding: 6px 16px;
  border-radius: 999px;
  border: 1px solid rgba(255, 255, 255, 0.15);
}
.nav-arrow {
  width: 44px !important;
  height: 44px !important;
  font-size: 20px !important;
  background: rgba(255, 255, 255, 0.15) !important;
  border: 1px solid rgba(255, 255, 255, 0.3) !important;
}

/* Form Fields Refinements */
.form-grid.two {
  gap: 12px 20px !important;
}
.field {
  gap: 6px !important;
}
.field label {
  color: #fff7df !important;
  font-size: 13px !important;
  font-weight: 800 !important;
}
.field input {
  min-height: 48px !important;
  padding: 0 16px !important;
  border: 1px solid rgba(255, 116, 180, 0.34) !important;
  border-radius: 12px !important;
  background: rgba(255, 255, 255, 0.08) !important;
  color: #fffaf0 !important;
  font-size: 14px !important;
  transition: all 0.2s ease;
}
.field input:focus {
  border-color: rgba(255, 129, 150, 0.72) !important;
  box-shadow: 0 0 0 4px rgba(248, 79, 155, 0.14) !important;
  outline: none;
}
.field input[readonly] {
  background: rgba(255, 255, 255, 0.03) !important;
  border-color: rgba(255, 255, 255, 0.12) !important;
  color: rgba(255, 245, 230, 0.6) !important;
}

/* Interest Keywords */
.interest-keyword-field {
  margin-top: 0;
  padding: 12px;
  border: 1px solid rgba(255, 255, 255, 0.12);
  border-radius: 14px;
  background: rgba(255, 255, 255, 0.035);
}
.interest-keyword-head strong {
  color: #fff;
  background: var(--primary);
  padding: 4px 12px;
  border-radius: 999px;
  font-size: 12px;
  font-weight: 850;
}
.interest-chip {
  padding: 8px 16px !important;
  border-radius: 14px !important;
  font-size: 14px !important;
  background: rgba(255, 255, 255, 0.08) !important;
  border: 1px solid rgba(255, 255, 255, 0.15) !important;
  color: rgba(255, 245, 230, 0.9) !important;
}
.interest-chip.active {
  background: var(--primary) !important;
  border-color: transparent !important;
  color: #fff !important;
  box-shadow: 0 4px 14px rgba(156, 91, 255, 0.35) !important;
}

/* Button Enhancements */
.actions {
  margin-top: 16px !important;
}
.secondary-button {
  border-radius: 12px !important;
  min-height: 44px !important;
  padding: 0 24px !important;
  font-size: 15px !important;
}

@media (max-width: 640px) {
  .profile-card-head {
    grid-template-columns: 76px minmax(0, 1fr);
    min-height: 0;
    gap: 12px;
  }

  .profile-portrait {
    width: 76px;
    height: 76px;
    border-radius: 20px;
    font-size: 24px;
  }

  .profile-edit-button {
    grid-column: 1 / -1;
    width: 100%;
  }
}
</style>

<template>
  <div class="panel-body">
    <div class="grid-2">
      <section class="card avatar-card" aria-label="캐릭터 미리보기">
        <div class="character-preview-wrapper" style="display: flex; align-items: center; justify-content: center; gap: 16px;">
          <button v-if="characterEditMode" type="button" class="nav-arrow" @click="prevCharacter">❮</button>
          <div class="character-image-wrapper">
            <img :src="`/characters/${displayCharacter.id}/default.png`" :alt="displayCharacter.name" style="max-width: 100%; height: 215px; object-fit: contain; filter: drop-shadow(0 18px 22px rgba(5, 2, 18, 0.38)); transform-origin: center bottom; transform: scale(1.1);" />
          </div>
          <button v-if="characterEditMode" type="button" class="nav-arrow" @click="nextCharacter">❯</button>
        </div>
        <div class="character-name">
          {{ displayCharacter.name }} · {{ displayCharacter.role || displayCharacter.desc }}
        </div>
        <button v-if="!characterEditMode" class="secondary-button" type="button" @click="startCharacterEdit">캐릭터 변경</button>
        <button v-else class="primary-button" type="button" @click="finishCharacterEdit" style="margin-top: 12px; min-width: 120px;">변경 완료</button>
      </section>

      <section class="card">
        <h3>프로필 정보</h3>
        <div class="form-grid two">
          <div class="field">
            <label for="profile-name">이름 또는 닉네임</label>
            <input id="profile-name" v-model="profile.name" :readonly="!profileEdit" placeholder="이름 또는 닉네임" />
          </div>
          <div class="field">
            <label for="profile-job">직업</label>
            <input id="profile-job" v-model="profile.job" placeholder="직업을 입력해 주세요" :readonly="!profileEdit" />
          </div>
          <div class="field">
            <label for="profile-birthdate">생년월일</label>
            <input id="profile-birthdate" v-model="profile.birthDate" placeholder="YYYY.MM.DD" :readonly="!profileEdit" />
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
                {{ keyword }}
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
                       {{ item.label }}
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
                {{ keyword }}
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
                       {{ item.label }}
                     </button>
                  </div>
                </div>
              </div>
            </div>
          </section>
        </div>
        <div class="actions" style="justify-content: flex-end;">
          <button class="primary-button" type="button" @click="$emit('toggle-profile-edit')">{{ profileEdit ? '완료' : '수정' }}</button>
        </div>
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
    selectedCharacter: { type: String, required: true },
    currentCharacter: { type: Object, required: true },
    characters: { type: Array, required: true },
    showCharacterPicker: { type: Boolean, required: true }
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
      interestGroups: groupByCategory(parseKeywordCsv(interestCsv, "interest")),
      characterEditMode: false,
      previewCharacterIndex: 0
    };
  },
  computed: {
    displayCharacter() {
      if (this.characterEditMode && this.characters && this.characters.length > 0) {
        return this.characters[this.previewCharacterIndex] || this.currentCharacter;
      }
      return this.currentCharacter;
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
        if (targetArray.length >= 3) {
          alert(`최대 3개까지만 선택할 수 있습니다.`);
          return;
        }
        targetArray.push(label);
      }
    },
    startCharacterEdit() {
      this.previewCharacterIndex = this.characters.findIndex(c => c.id === this.selectedCharacter);
      if (this.previewCharacterIndex === -1) this.previewCharacterIndex = 0;
      this.characterEditMode = true;
    },
    finishCharacterEdit() {
      this.characterEditMode = false;
      const chosen = this.characters[this.previewCharacterIndex];
      if (chosen && chosen.id !== this.selectedCharacter) {
        this.$emit('choose-character', chosen.id);
      }
    },
    prevCharacter() {
      this.previewCharacterIndex = (this.previewCharacterIndex - 1 + this.characters.length) % this.characters.length;
    },
    nextCharacter() {
      this.previewCharacterIndex = (this.previewCharacterIndex + 1) % this.characters.length;
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
  margin-bottom: 16px !important;
  font-weight: 850 !important;
  letter-spacing: -0.02em;
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
  margin-top: 8px;
  padding-top: 12px;
  border-top: 1px dashed rgba(255, 255, 255, 0.15);
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
</style>

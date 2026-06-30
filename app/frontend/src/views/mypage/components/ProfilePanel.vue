<template>
  <div class="panel-body">
    <div class="grid-2">
      <section class="card avatar-card" aria-label="캐릭터 미리보기">
        <div class="character" :data-kind="selectedCharacter" :style="{
          '--hair': currentCharacter.color === 'lavender' ? '#8b5cf6' : currentCharacter.color === 'night' ? '#1e293b' : currentCharacter.color === 'coral' ? '#f43f5e' : '#fcd34d',
          '--skin': currentCharacter.color === 'lavender' ? '#f3e8ff' : currentCharacter.color === 'night' ? '#f1f5f9' : currentCharacter.color === 'coral' ? '#ffe4e6' : '#fffbeb',
          '--cloth': currentCharacter.color === 'lavender' ? '#ddd6fe' : currentCharacter.color === 'night' ? '#94a3b8' : currentCharacter.color === 'coral' ? '#fecdd3' : '#fef3c7',
          '--cloth-dark': currentCharacter.color === 'lavender' ? '#c4b5fd' : currentCharacter.color === 'night' ? '#64748b' : currentCharacter.color === 'coral' ? '#fda4af' : '#fde68a'
        }">
          <span class="hair"></span>
          <span class="face"></span>
          <span class="bang one"></span>
          <span class="bang two"></span>
          <span class="bang three"></span>
          <span class="eye left"></span>
          <span class="eye right"></span>
          <span class="cheek left"></span>
          <span class="cheek right"></span>
          <span class="mouth"></span>
          <span class="neck"></span>
          <span class="body"></span>
          <span class="collar left"></span>
          <span class="collar right"></span>
        </div>
        <div class="character-name">
          {{ currentCharacter.name }} · {{ currentCharacter.desc }}
        </div>
        <button class="secondary-button" type="button" @click="$emit('open-character-picker')">캐릭터 교체</button>
      </section>

      <section class="card">
        <h3>프로필 정보</h3>
        <div class="form-grid two">
          <div class="field">
            <label for="profile-name">이름</label>
            <input id="profile-name" v-model="profile.name" :readonly="!profileEdit" />
          </div>
          <div class="field">
            <label for="profile-gender">성별</label>
            <select id="profile-gender" v-model="profile.gender" :disabled="!profileEdit">
              <option>여성</option><option>남성</option><option>선택 안 함</option>
            </select>
          </div>
          <div class="field">
            <label for="profile-age">나이</label>
            <input id="profile-age" type="number" min="14" max="99" v-model.number="profile.age" :readonly="!profileEdit" />
          </div>
          <div class="field">
            <label for="profile-birthday">생일</label>
            <input id="profile-birthday" v-model="profile.birthday" placeholder="예: 06.23" :readonly="!profileEdit" />
          </div>
          <div class="field">
            <label for="profile-job">직업/상황</label>
            <input id="profile-job" v-model="profile.job" placeholder="예: 취업 준비, 직장인, 학생" :readonly="!profileEdit" />
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
        <div class="actions">
          <button class="primary-button" type="button" @click="$emit('toggle-profile-edit')">{{ profileEdit ? '완료' : '수정' }}</button>
        </div>
        <p v-if="profileSavedAt" class="notice">마지막 저장 시각: {{ profileSavedAt }}</p>
      </section>
    </div>

    <transition name="fade">
      <section v-if="showCharacterPicker" class="character-picker" @click.self="$emit('close-character-picker')">
        <div class="picker-dialog" role="dialog" aria-modal="true" aria-label="캐릭터 교체">
          <div class="picker-head">
            <h3>대화 대상 캐릭터 선택</h3>
            <button class="close-button" type="button" aria-label="닫기" @click="$emit('close-character-picker')">×</button>
          </div>
          <div class="character-options">
            <button class="character-option" type="button" v-for="character in characters" :key="character.id"
              :class="{ active: selectedCharacter === character.id }" @click="$emit('choose-character', character.id)">
              <div class="character-mini" :class="'mini-' + character.id"
                :style="{ 
                  '--hair': character.color === 'lavender' ? '#8b5cf6' : character.color === 'night' ? '#1e293b' : character.color === 'coral' ? '#f43f5e' : '#fcd34d',
                  '--cloth': character.color === 'lavender' ? '#ddd6fe' : character.color === 'night' ? '#94a3b8' : character.color === 'coral' ? '#fecdd3' : '#fef3c7' 
                }"></div>
              {{ character.name }}
            </button>
          </div>
        </div>
      </section>
    </transition>
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
      interestGroups: groupByCategory(parseKeywordCsv(interestCsv, "interest"))
    };
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
</style>

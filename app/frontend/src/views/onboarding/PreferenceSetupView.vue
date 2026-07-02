<script setup>
import { computed, ref } from "vue";

const emit = defineEmits(["navigate"]);

const recommendedHobbies = [
  { label: "음악 감상", icon: "🎵" },
  { label: "카페 투어", icon: "☕" },
  { label: "산책", icon: "👟" },
];

const recommendedInterests = [
  { label: "자기계발", icon: "🌱" },
  { label: "여행", icon: "🧳" },
];

const keywordGroups = [
  { title: "취미", icon: "🎵", type: "hobby", items: ["독서", "영화 감상", "운동", "사진 찍기", "요리", "드로잉", "게임", "악기 연주"] },
  { title: "관심 분야", icon: "⭐", type: "interest", items: ["자기계발", "여행", "환경/지속가능", "심리/철학", "문화/예술", "IT/테크", "금융/투자", "스타트업"] },
  { title: "라이프스타일", icon: "🌿", type: "lifestyle", items: ["미니멀 라이프", "반려동물", "인테리어", "패션/뷰티", "건강 관리", "맛집 탐방", "캠핑/아웃도어", "식물 키우기"] },
  { title: "학습/성장", icon: "🎓", type: "growth", items: ["외국어 학습", "글쓰기", "프로그래밍", "디자인", "마케팅", "창업", "자격증", "독서 모임"] },
];

const selected = ref(["음악 감상", "카페 투어", "산책"]);
const activeFilter = ref("전체");
const filters = ["전체", "취미", "관심 분야", "라이프스타일", "학습/성장"];

const selectedCount = computed(() => selected.value.length);
const progressPercent = computed(() => Math.min(100, Math.round((selectedCount.value / 6) * 100)));
const selectedChips = computed(() => selected.value.slice(0, 5));
const visibleKeywordGroups = computed(() => {
  if (activeFilter.value === "전체") return keywordGroups;
  return keywordGroups.filter((group) => group.title === activeFilter.value);
});

function isSelected(label) {
  return selected.value.includes(label);
}

function toggleKeyword(label) {
  if (isSelected(label)) {
    selected.value = selected.value.filter((item) => item !== label);
    return;
  }

  selected.value = [...selected.value, label];
}

function completePreferences() {
  localStorage.setItem("binteumsaiPreferenceDraft", JSON.stringify(selected.value));
  emit("navigate", "userinfo");
}
</script>

<template>
  <section class="view-card preference-fragment-view">
    <article class="glass-panel preference-panel">
      <header class="preference-hero">
        <div class="hero-mascot">
          <img src="/characters/bird/hurt.png" alt="" aria-hidden="true">
        </div>
        <div>
          <h2>취향 조각 수집하기 ✦</h2>
          <p>당신의 취미와 관심사를 알려주세요. 더 깊고 즐거운 대화를 함께 만들어요.</p>
        </div>
        <aside class="selection-progress">
          <strong>🔖 {{ selectedCount }} / 6 선택 완료</strong>
          <i><b :style="{ width: `${progressPercent}%` }"></b></i>
          <span>3개 이상 선택하면 대화 경험이 더 풍성해져요!</span>
        </aside>
      </header>

      <section class="recommend-grid">
        <div>
          <h3>✦ 추천 취미</h3>
          <p>많이 선택할수록 더 잘 맞는 대화를 만들어드려요!</p>
          <div class="recommend-card-row">
            <button
              v-for="item in recommendedHobbies"
              :key="item.label"
              type="button"
              class="recommend-card selected"
              @click="toggleKeyword(item.label)"
            >
              <span>{{ item.icon }}</span>
              <strong>{{ item.label }}</strong>
              <i>✓</i>
            </button>
            <button type="button" class="recommend-card more">⌕<strong>+ 더 둘러보기</strong></button>
          </div>
        </div>

        <div>
          <h3>🌹 관심 분야</h3>
          <p>마음이 가는 분야를 선택해보세요.</p>
          <div class="recommend-card-row compact">
            <button
              v-for="item in recommendedInterests"
              :key="item.label"
              type="button"
              class="recommend-card"
              :class="{ selected: isSelected(item.label) }"
              @click="toggleKeyword(item.label)"
            >
              <span>{{ item.icon }}</span>
              <strong>{{ item.label }}</strong>
              <i>{{ isSelected(item.label) ? "✓" : "+" }}</i>
            </button>
            <button type="button" class="recommend-card more">🔭<strong>+ 더 둘러보기</strong></button>
          </div>
        </div>
      </section>

      <section class="keyword-vault">
        <header>
          <div>
            <h3>📦 전체 키워드 보관함</h3>
            <p>원하는 키워드를 클릭하여 선택해보세요!</p>
          </div>
          <div class="filter-row">
            <button
              v-for="filter in filters"
              :key="filter"
              type="button"
              :class="{ active: activeFilter === filter }"
              @click="activeFilter = filter"
            >
              {{ filter }}
            </button>
          </div>
        </header>

        <div class="keyword-group-list">
          <article v-for="group in visibleKeywordGroups" :key="group.title" class="keyword-group-card">
            <strong><span>{{ group.icon }}</span>{{ group.title }}</strong>
            <div>
              <button
                v-for="item in group.items"
                :key="item"
                type="button"
                class="keyword-pill"
                :class="{ selected: isSelected(item) }"
                @click="toggleKeyword(item)"
              >
                {{ item }} <span>{{ isSelected(item) ? "✓" : "+" }}</span>
              </button>
            </div>
          </article>
        </div>
      </section>

      <footer class="selected-fragments">
        <div>
          <span class="jar">🫙</span>
          <div>
            <strong>선택한 취향 조각</strong>
            <p>{{ selectedCount }}개 선택 완료!</p>
          </div>
        </div>
        <div class="selected-chip-row">
          <button v-for="chip in selectedChips" :key="chip" type="button" @click="toggleKeyword(chip)">
            {{ chip }} ×
          </button>
        </div>
        <button class="btn primary large" type="button" @click="completePreferences">완료 ✨</button>
      </footer>
    </article>
  </section>
</template>

<style scoped>
.preference-fragment-view {
  width: min(1240px, calc(100% - 56px));
  min-height: calc(100vh - var(--bt-header-h) - 50px);
  display: grid;
  place-items: center;
  margin: 24px auto 34px;
}

.preference-panel {
  width: 100%;
  display: grid;
  gap: 24px;
  padding: clamp(28px, 3vw, 42px);
  border-radius: 28px;
  background:
    linear-gradient(145deg, rgba(62, 25, 76, 0.9), rgba(23, 10, 44, 0.88)),
    rgba(50, 24, 73, 0.76);
}

.preference-hero {
  display: grid;
  grid-template-columns: 150px minmax(0, 1fr) 360px;
  gap: 28px;
  align-items: center;
  padding-bottom: 24px;
  border-bottom: 1px solid rgba(255, 255, 255, 0.1);
}

.hero-mascot {
  display: grid;
  place-items: center;
}

.hero-mascot img {
  width: 140px;
  height: 120px;
  object-fit: contain;
  filter: drop-shadow(0 18px 24px rgba(3, 1, 18, 0.4));
}

.preference-hero h2 {
  margin: 0;
  color: #fff;
  font-size: clamp(34px, 3vw, 48px);
  line-height: 1.15;
}

.preference-hero p,
.keyword-vault p,
.recommend-grid p,
.selected-fragments p {
  margin: 8px 0 0;
  color: rgba(255, 245, 238, 0.68);
  line-height: 1.55;
}

.selection-progress {
  display: grid;
  gap: 10px;
  padding: 20px;
  border: 1px solid rgba(255, 143, 164, 0.32);
  border-radius: 22px;
  background: rgba(255, 255, 255, 0.055);
}

.selection-progress strong {
  color: #fff;
  font-size: 20px;
}

.selection-progress i {
  height: 12px;
  border-radius: 999px;
  background: rgba(255, 255, 255, 0.09);
  overflow: hidden;
}

.selection-progress b {
  display: block;
  height: 100%;
  border-radius: inherit;
  background: linear-gradient(90deg, #e73e65, #e77e6e);
}

.selection-progress span {
  color: rgba(255, 245, 238, 0.68);
  font-size: 13px;
  font-weight: 800;
}

.recommend-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 26px;
}

.recommend-grid h3,
.keyword-vault h3 {
  margin: 0;
  color: #fff1cd;
  font-size: 22px;
}

.recommend-card-row {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 12px;
  margin-top: 14px;
}

.recommend-card-row.compact {
  grid-template-columns: repeat(3, minmax(0, 1fr));
}

.recommend-card {
  position: relative;
  min-height: 92px;
  display: grid;
  place-items: center;
  gap: 6px;
  padding: 14px;
  border: 1px solid rgba(255, 143, 164, 0.22);
  border-radius: 12px;
  background: rgba(255, 255, 255, 0.055);
  color: #fff;
  cursor: pointer;
}

.recommend-card.selected {
  border-color: rgba(255, 143, 164, 0.9);
  background: linear-gradient(145deg, rgba(231, 62, 101, 0.45), rgba(231, 126, 110, 0.2));
  box-shadow: 0 0 24px rgba(231, 62, 101, 0.22);
}

.recommend-card span {
  font-size: 28px;
}

.recommend-card strong {
  font-size: 15px;
}

.recommend-card i {
  position: absolute;
  right: 8px;
  top: 8px;
  width: 24px;
  height: 24px;
  display: grid;
  place-items: center;
  border-radius: 50%;
  background: linear-gradient(135deg, #e73e65, #e77e6e);
  font-style: normal;
}

.recommend-card.more {
  color: rgba(255, 245, 238, 0.76);
}

.keyword-vault {
  display: grid;
  gap: 16px;
}

.keyword-vault header {
  display: flex;
  justify-content: space-between;
  gap: 16px;
  align-items: end;
}

.filter-row {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  justify-content: flex-end;
}

.filter-row button {
  min-height: 38px;
  padding: 0 14px;
  border: 1px solid rgba(255, 143, 164, 0.22);
  border-radius: 10px;
  background: rgba(255, 255, 255, 0.055);
  color: rgba(255, 245, 238, 0.76);
  font-weight: 900;
  cursor: pointer;
}

.filter-row button.active {
  color: #fff;
  background: linear-gradient(135deg, #e73e65, #e77e6e);
}

.keyword-group-list {
  display: grid;
  gap: 10px;
}

.keyword-group-card {
  display: grid;
  grid-template-columns: 150px minmax(0, 1fr);
  gap: 16px;
  align-items: center;
  padding: 12px 14px;
  border: 1px solid rgba(255, 143, 164, 0.18);
  border-radius: 12px;
  background: rgba(255, 255, 255, 0.04);
}

.keyword-group-card > strong {
  color: #fff1cd;
  font-size: 16px;
}

.keyword-group-card > strong span {
  margin-right: 8px;
}

.keyword-group-card div,
.selected-chip-row {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.keyword-pill,
.selected-chip-row button {
  min-height: 34px;
  padding: 0 12px;
  border: 1px solid rgba(255, 143, 164, 0.2);
  border-radius: 999px;
  background: rgba(255, 255, 255, 0.055);
  color: rgba(255, 245, 238, 0.82);
  font-weight: 850;
  cursor: pointer;
}

.keyword-pill.selected {
  border: 0;
  color: #fff;
  background: linear-gradient(135deg, #e73e65, #e77e6e);
}

.selected-fragments {
  display: grid;
  grid-template-columns: 220px minmax(0, 1fr) 300px;
  gap: 18px;
  align-items: center;
  padding: 18px;
  border: 1px solid rgba(255, 143, 164, 0.26);
  border-radius: 22px;
  background: rgba(255, 255, 255, 0.045);
}

.selected-fragments > div:first-child {
  display: flex;
  gap: 12px;
  align-items: center;
}

.jar {
  width: 58px;
  height: 58px;
  display: grid;
  place-items: center;
  border-radius: 18px;
  background: rgba(255, 255, 255, 0.08);
  font-size: 32px;
}

.selected-fragments strong {
  color: #fff;
}

.selected-fragments .btn {
  min-height: 66px;
  font-size: 19px;
}

@media (max-width: 1080px) {
  .preference-fragment-view {
    width: min(100% - 28px, 820px);
  }

  .preference-hero,
  .recommend-grid,
  .keyword-vault header,
  .keyword-group-card,
  .selected-fragments {
    grid-template-columns: 1fr;
  }

  .recommend-card-row,
  .recommend-card-row.compact {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}
</style>

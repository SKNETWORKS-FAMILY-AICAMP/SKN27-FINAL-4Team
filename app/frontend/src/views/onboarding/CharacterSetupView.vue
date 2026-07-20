<script setup>
import { computed, ref } from "vue";
import { useRoute, useRouter } from "vue-router";
import { characterApi } from "../../api/character.js";

const router = useRouter();
const route = useRoute();

const expressions = [
  { id: "joy", label: "기쁨", desc: "통통 튀는 밝은 반응" },
  { id: "sadness", label: "슬픔", desc: "고개를 살짝 숙여요" },
  { id: "anger", label: "화남", desc: "살짝 눈썹을 찌푸려요" },
  { id: "anxiety", label: "불안", desc: "눈을 동그랗게 떠요" },
];
const defaultExpression = {
  id: "default",
  label: "기본",
  desc: "기본 표정",
};

const characters = [
  {
    id: "otter",
    name: "토토",
    role: "다정한 위로형",
    tone: "부드럽고 따뜻한 말투",
    line: "오늘 마음은 제가 옆에서 같이 정리해볼게요.",
    tags: ["다정함", "포근함"],
  },
  {
    id: "cat",
    name: "까미",
    role: "시크한 직면형",
    tone: "무심하지만 핵심을 짚는 말투",
    line: "피하고 싶은 마음까지 천천히 살펴볼까요?",
    tags: ["솔직함", "냉철함"],
  },
  {
    id: "redpanda",
    name: "포리",
    role: "활발한 응원형",
    tone: "밝고 힘 있게 응원하는 말투",
    line: "작은 행동 하나만 골라서 같이 시작해봐요.",
    tags: ["에너지", "긍정적"],
  },
  {
    id: "bird",
    name: "여울",
    role: "소심한 공감형",
    tone: "조심스럽고 섬세한 말투",
    line: "괜찮아요. 천천히 말해도 제가 듣고 있을게요.",
    tags: ["조심스러움", "섬세함"],
  },
];

const storedCharacter = getStoredCharacter();
const selectedCharacter = ref(
  characters.some((character) => character.id === storedCharacter.characterId)
    ? storedCharacter.characterId
    : "cat"
);
const selectedExpression = ref(null);

const selected = computed(() => characters.find((character) => character.id === selectedCharacter.value) || characters[0]);
const selectedExpressionData = computed(
  () => expressions.find((expression) => expression.id === selectedExpression.value) || defaultExpression
);
const selectedExpressionImage = computed(() => (
  selectedExpression.value
    ? characterImage(selected.value, selectedExpression.value)
    : characterDefaultImage(selected.value)
));

function characterImage(character, expressionId = "joy") {
  return `/characters/${character.id}/${expressionId}.png`;
}

function characterDefaultImage(character) {
  return `/characters/${character.id}/default.png`;
}

function emotionClass(expressionId) {
  return expressionId ? `emotion-${expressionId}` : "";
}

function selectCharacter(characterId) {
  selectedCharacter.value = characterId;
  selectedExpression.value = null;
}

function toggleExpression(expressionId) {
  selectedExpression.value = (
    selectedExpression.value === expressionId
      ? null
      : expressionId
  );
}

function getStoredCharacter() {
  try {
    return JSON.parse(localStorage.getItem("binteumsaiCharacter") || "{}");
  } catch {
    return {};
  }
}

async function saveCharacterAndContinue() {
  const payload = {
    character_id: selected.value.id,
    expression_id: selectedExpression.value || "default",
  };

  localStorage.setItem(
    "binteumsaiCharacter",
    JSON.stringify({
      characterId: payload.character_id,
      expressionId: payload.expression_id,
    })
  );

  try {
    await characterApi.savePreference(payload);
  } catch {
    // 서버 연결이 없을 때도 온보딩을 이어갈 수 있도록 localStorage 값을 유지한다.
  }

  const redirect = String(route.query.redirect || "");
  router.push({
    path: "/onboarding/info",
    query: redirect.startsWith("/") && !redirect.startsWith("//") ? { redirect } : {},
  });
}
</script>

<template>
  <section class="view-card character-page">
    <div class="character-layout">
      <article class="glass-panel character-main-panel">
        <div class="setup-stepper" aria-label="첫 로그인 설정 단계">
          <span class="done"><b>1</b>로그인</span>
          <span class="active"><b>2</b>캐릭터 설정</span>
          <span><b>3</b>정보와 취향</span>
          <span><b>4</b>완료</span>
        </div>

        <header class="screen-heading text-area">
          <h2>대화 동행자를 선택해요 ✦</h2>
          <p>사용자와 대화할 마음 동행자의 기본 성격, 표정, 말투를 설정하는 화면이에요.</p>
        </header>

        <div class="character-grid" aria-label="캐릭터 선택">
          <button
            v-for="character in characters"
            :key="character.id"
            type="button"
            class="character-card"
            :class="{ selected: selectedCharacter === character.id }"
            @click="selectCharacter(character.id)"
          >
            <span v-if="selectedCharacter === character.id" class="selected-badge">선택됨</span>
            <span class="character-card-image image-area">
              <img
                :src="characterDefaultImage(character)"
                :alt="`${character.name} 기본 표정`"
                class="character-img"
              >
            </span>
            <span class="character-card-copy text-area">
              <strong>{{ character.name }}</strong>
              <small>{{ character.role }}</small>
              <span class="tag-row">
                <i v-for="tag in character.tags" :key="tag">{{ tag }}</i>
              </span>
            </span>
          </button>
        </div>

        <section class="expression-section">
          <div class="section-title-row">
            <h3>표정 미리보기 ✦</h3>
            <span>{{ selected.name }} · {{ selectedExpressionData.label }}</span>
          </div>

          <div class="face-options" aria-label="표정 선택">
            <button
              v-for="expression in expressions"
              :key="expression.id"
              type="button"
              class="expression-card"
              :class="{ selected: selectedExpression === expression.id }"
              :aria-pressed="selectedExpression === expression.id"
              @click="toggleExpression(expression.id)"
            >
              <span class="expression-image image-area">
                <img
                  :src="characterImage(selected, expression.id)"
                  :alt="`${selected.name} ${expression.label}`"
                >
              </span>
              <span class="expression-copy text-area">
                <strong>{{ expression.label }}</strong>
                <small>{{ expression.desc }}</small>
              </span>
            </button>
          </div>
        </section>
      </article>

      <aside class="glass-panel character-preview-panel side-panel">
        <div class="preview-image image-area">
          <img
            :src="selectedExpressionImage"
            :alt="`${selected.name} ${selectedExpressionData.label} 표정`"
            class="character-img"
            :class="emotionClass(selectedExpression)"
          >
        </div>

        <section class="preview-copy text-area">
          <h3>{{ selected.name }}</h3>
          <span>{{ selected.role }}</span>
          <p>{{ selected.role }} · {{ selected.tone }}</p>
          <blockquote>{{ selected.line }}</blockquote>
        </section>

        <button class="btn primary full save-character-button" type="button" @click="saveCharacterAndContinue">
          캐릭터 저장하고 다음 ›
        </button>
      </aside>
    </div>
  </section>
</template>

<style scoped>
.character-page {
  min-height: calc(100dvh - var(--bt-header-h));
  padding: 24px 32px 40px;
  word-break: keep-all;
  overflow-wrap: break-word;
}

.character-layout {
  width: min(100%, 1440px);
  display: grid;
  grid-template-columns: minmax(0, 1fr) minmax(340px, 420px);
  gap: 24px;
  align-items: stretch;
  margin: 0 auto;
}

.character-main-panel,
.character-preview-panel {
  border-radius: 32px;
  background:
    linear-gradient(145deg, rgba(45, 13, 63, 0.82), rgba(20, 8, 36, 0.9)),
    rgba(45, 13, 63, 0.74);
}

.character-main-panel {
  min-width: 0;
  display: grid;
  gap: 22px;
  padding: clamp(28px, 3vw, 44px);
}

.setup-stepper {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 16px;
  width: min(100%, 560px);
  max-width: 820px;
  margin: 0 auto;
}

.setup-stepper span {
  position: relative;
  display: grid;
  justify-items: center;
  gap: 8px;
  color: rgba(255, 245, 230, 0.58);
  font-size: 14px;
  font-weight: 850;
  line-height: 1.35;
}

.setup-stepper span:not(:last-child)::after {
  content: "";
  position: absolute;
  top: 20px;
  left: calc(50% + 34px);
  width: calc(100% - 46px);
  border-top: 1px dashed rgba(255, 116, 180, 0.28);
}

.setup-stepper b {
  width: 42px;
  height: 42px;
  display: grid;
  place-items: center;
  border-radius: 50%;
  border: 1px solid rgba(255, 116, 180, 0.24);
  background: rgba(255, 255, 255, 0.07);
  color: rgba(255, 245, 230, 0.74);
}

.setup-stepper .active {
  color: #fff7df;
}

.setup-stepper .active b {
  border: 0;
  color: #fff;
  background: linear-gradient(90deg, #f84f9b 0%, #ff8a57 100%);
  box-shadow: 0 0 0 6px rgba(248, 79, 155, 0.13), 0 0 24px rgba(248, 79, 155, 0.4);
}

.screen-heading h2 {
  margin: 0;
  color: #fff7df;
  font-size: clamp(32px, 3vw, 52px);
  line-height: 1.18;
  letter-spacing: -0.02em;
}

.screen-heading p {
  max-width: 860px;
  margin: 10px 0 0;
  color: rgba(255, 245, 230, 0.72);
  font-size: clamp(14px, 0.9vw, 18px);
  line-height: 1.55;
}

.character-grid {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 14px;
}

.character-card {
  position: relative;
  min-width: 0;
  min-height: 278px;
  display: grid;
  grid-template-rows: 132px minmax(0, 1fr);
  gap: 14px;
  padding: 18px;
  border: 1px solid rgba(255, 116, 180, 0.2);
  border-radius: 20px;
  background: rgba(71, 25, 86, 0.54);
  color: #fffaf0;
  cursor: pointer;
  text-align: left;
  transition: border-color 0.16s ease, box-shadow 0.16s ease, transform 0.16s ease;
}

.character-card:hover {
  transform: translateY(-2px);
  border-color: rgba(255, 129, 150, 0.52);
}

.character-card.selected {
  border-color: rgba(255, 129, 150, 0.72);
  box-shadow: 0 0 0 1px rgba(255, 129, 150, 0.28), 0 0 30px rgba(248, 79, 155, 0.28);
  background:
    linear-gradient(145deg, rgba(248, 79, 155, 0.34), rgba(255, 138, 87, 0.16)),
    rgba(71, 25, 86, 0.62);
}

.selected-badge {
  position: absolute;
  top: 12px;
  right: 12px;
  z-index: 2;
  padding: 7px 10px;
  border-radius: 999px;
  color: #fff;
  background: linear-gradient(90deg, #f84f9b 0%, #ff8a57 100%);
  font-size: 12px;
  font-weight: 950;
}

.character-card-image {
  width: 100%;
  height: 132px;
  display: flex;
  align-items: center;
  justify-content: center;
  padding-top: 6px;
}

.character-card-image img {
  max-width: 100%;
  max-height: 120px;
  object-fit: contain;
  filter: drop-shadow(0 16px 20px rgba(8, 2, 22, 0.4));
  transform-origin: 50% 82%;
}

.character-card-copy {
  min-width: 0;
  display: grid;
  align-content: start;
  gap: 8px;
}

.character-card-copy strong {
  color: #fff7df;
  font-size: 22px;
  font-weight: 950;
}

.character-card-copy small {
  color: rgba(255, 245, 230, 0.72);
  font-size: 15px;
  line-height: 1.35;
}

.tag-row {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}

.tag-row i {
  padding: 7px 10px;
  border-radius: 999px;
  background: rgba(255, 255, 255, 0.08);
  color: rgba(255, 245, 230, 0.78);
  font-size: 12px;
  font-style: normal;
  font-weight: 850;
}

.expression-section {
  display: grid;
  gap: 12px;
}

.section-title-row {
  display: flex;
  align-items: end;
  justify-content: space-between;
  gap: 16px;
}

.section-title-row h3 {
  margin: 0;
  color: #ffd37a;
  font-size: clamp(20px, 1.6vw, 28px);
}

.section-title-row span {
  color: rgba(255, 245, 230, 0.68);
  font-size: 14px;
  font-weight: 850;
}

.face-options {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  justify-content: center;
  width: min(100%, 760px);
  margin-inline: auto;
  gap: 12px;
}

.expression-card {
  min-width: 0;
  min-height: 124px;
  display: grid;
  grid-template-rows: 64px minmax(0, 1fr);
  gap: 8px;
  padding: 12px;
  border: 1px solid rgba(255, 116, 180, 0.18);
  border-radius: 16px;
  background: rgba(255, 255, 255, 0.055);
  color: #fffaf0;
  cursor: pointer;
}

.expression-card.selected {
  border-color: rgba(255, 129, 150, 0.72);
  background: linear-gradient(145deg, rgba(248, 79, 155, 0.34), rgba(255, 138, 87, 0.16));
}

.expression-image {
  height: 64px;
  display: flex;
  align-items: center;
  justify-content: center;
}

.expression-image img {
  max-width: 64px;
  max-height: 64px;
  object-fit: contain;
  transform-origin: 50% 82%;
}

.expression-copy {
  display: grid;
  gap: 4px;
  text-align: center;
}

.expression-copy strong {
  font-size: 15px;
}

.expression-copy small {
  color: rgba(255, 245, 230, 0.62);
  font-size: 12px;
  line-height: 1.35;
}

.character-preview-panel {
  min-width: 0;
  display: grid;
  align-content: start;
  gap: 20px;
  padding: clamp(24px, 2.6vw, 34px);
}

.preview-image {
  width: 100%;
  height: 220px;
  display: flex;
  align-items: center;
  justify-content: center;
}

.preview-image img {
  max-width: 100%;
  max-height: 220px;
  object-fit: contain;
  filter: drop-shadow(0 22px 26px rgba(8, 2, 22, 0.46));
  transform-origin: 50% 84%;
}

.emotion-joy {
  animation: emotionJoy 1.4s ease-in-out infinite;
}

.emotion-anger {
  animation: emotionAnger 0.42s ease-in-out infinite;
}

.emotion-sadness {
  animation: emotionSadness 1.9s ease-in-out infinite;
}

.emotion-anxiety {
  animation: emotionAnxiety 0.28s linear infinite;
}

.emotion-hurt {
  animation: emotionHurt 1.7s ease-in-out infinite;
}

.emotion-panic {
  animation: emotionPanic 0.68s ease-in-out infinite;
}

@keyframes emotionJoy {
  0%, 100% { transform: translateY(0) scale(1); }
  38% { transform: translateY(-8px) scale(1.05); }
  62% { transform: translateY(1px) scale(0.99); }
}

@keyframes emotionAnger {
  0%, 100% { transform: translateX(0) rotate(0deg); }
  25% { transform: translateX(-3px) rotate(-2deg); }
  50% { transform: translateX(3px) rotate(2deg); }
  75% { transform: translateX(-2px) rotate(-1deg); }
}

@keyframes emotionSadness {
  0%, 100% { transform: translateY(0) rotate(0deg); opacity: 1; }
  45% { transform: translateY(8px) rotate(-2deg); opacity: 0.86; }
  72% { transform: translateY(5px) rotate(1deg); opacity: 0.92; }
}

@keyframes emotionAnxiety {
  0%, 100% { transform: translate(0, 0) rotate(0deg); }
  25% { transform: translate(-1px, 1px) rotate(-0.8deg); }
  50% { transform: translate(1px, -1px) rotate(0.8deg); }
  75% { transform: translate(-1px, -1px) rotate(0.4deg); }
}

@keyframes emotionHurt {
  0%, 100% { transform: translateY(0) scale(1); filter: drop-shadow(0 16px 20px rgba(8, 2, 22, 0.4)); }
  48% { transform: translateY(5px) scale(0.96); filter: drop-shadow(0 10px 16px rgba(8, 2, 22, 0.34)); }
}

@keyframes emotionPanic {
  0%, 100% { transform: translateY(0) rotate(0deg) scale(1); }
  20% { transform: translateY(-4px) rotate(-5deg) scale(1.03); }
  40% { transform: translateY(2px) rotate(5deg) scale(0.98); }
  60% { transform: translateY(-3px) rotate(-4deg) scale(1.02); }
  80% { transform: translateY(1px) rotate(4deg) scale(1); }
}

.preview-copy h3 {
  margin: 0;
  color: #fff7df;
  font-size: 34px;
  line-height: 1.15;
}

.preview-copy > span {
  display: inline-flex;
  width: fit-content;
  margin: 8px 0 12px;
  padding: 7px 12px;
  border-radius: 999px;
  background: rgba(255, 255, 255, 0.08);
  color: rgba(255, 245, 230, 0.76);
  font-size: 13px;
  font-weight: 850;
}

.preview-copy p {
  margin: 0 0 14px;
  color: rgba(255, 245, 230, 0.74);
  line-height: 1.55;
}

.preview-copy blockquote {
  margin: 0;
  padding: 16px 18px;
  border: 1px solid rgba(255, 116, 180, 0.18);
  border-radius: 18px;
  background: rgba(255, 255, 255, 0.055);
  color: rgba(255, 245, 230, 0.9);
  font-size: 15px;
  line-height: 1.55;
}

.stat-preview {
  display: grid;
  gap: 12px;
  padding: 18px;
  border-radius: 20px;
  background: rgba(255, 255, 255, 0.055);
}

.stat-preview h4 {
  margin: 0 0 4px;
  color: #ffd37a;
  font-size: 17px;
}

.trait-row {
  display: grid;
  grid-template-columns: 92px minmax(0, 1fr) 36px;
  gap: 10px;
  align-items: center;
  color: rgba(255, 245, 230, 0.86);
  font-size: 14px;
  font-weight: 850;
}

.trait-row span {
  min-width: 0;
  display: inline-flex;
  align-items: center;
  gap: 7px;
}

.trait-row i {
  width: 24px;
  height: 24px;
  display: grid;
  place-items: center;
  flex: 0 0 auto;
  border-radius: 8px;
  background: rgba(255, 255, 255, 0.1);
  color: #ffd37a;
  font-style: normal;
}

.trait-row div {
  height: 8px;
  border-radius: 999px;
  background: rgba(255, 255, 255, 0.12);
  overflow: hidden;
}

.trait-row b {
  display: block;
  width: var(--value);
  height: 100%;
  border-radius: inherit;
  background: linear-gradient(90deg, #f84f9b 0%, #ff8a57 100%);
}

.trait-row strong {
  color: #fff7df;
  text-align: right;
}

.save-character-button {
  min-height: 60px;
  font-size: 17px;
  white-space: nowrap;
}

@media (max-width: 1180px) {
  .character-layout {
    grid-template-columns: 1fr;
  }

  .character-preview-panel {
    width: 100%;
  }
}

@media (max-width: 900px) {
  .character-page {
    padding: 20px 14px 34px;
  }

  .setup-stepper {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }

  .setup-stepper span::after {
    display: none;
  }

  .character-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }

  .face-options {
    grid-template-columns: repeat(3, minmax(0, 1fr));
  }
}

@media (max-width: 560px) {
  .character-grid,
  .face-options {
    grid-template-columns: 1fr;
  }
}
</style>

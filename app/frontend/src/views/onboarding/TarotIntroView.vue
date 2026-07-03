<script setup>
import { computed, onMounted, ref } from "vue";
import { useRouter } from "vue-router";
import { getLocalDateString } from "../../api/client.js";
import { tarotApi } from "../../api/tarot.js";
import { userApi } from "../../api/user.js";
import { getTarotCardImage } from "../../assets/tarot/cardImages.js";
import tarotCardBackImage from "../../assets/tarot/tarot-card-back.png";
import tarotDeckBoxImage from "../../assets/tarot/tarot-deck-box.png";

const router = useRouter();

const categories = [
  { id: "relationship", label: "연애", icon: "♡" },
  { id: "work", label: "일/진로", icon: "▣" },
  { id: "money", label: "재물", icon: "◎" },
  { id: "study", label: "학업", icon: "□" },
  { id: "general", label: "총운", icon: "☆" },
];

const DAILY_MAJOR_CACHE_KEY = "binteumsaiDailyMajorCard";
const USER_PROFILE_KEY = "binteumsaiUserProfile";

const dailyMajor = ref(null);
const isDailyMajorLoading = ref(false);
const dailyMajorError = ref("");
const isDailyCardRevealed = ref(false);
const currentUser = ref(null);
const authChecked = ref(false);
const isAuthenticated = computed(() => Boolean(currentUser.value));

const dailyCardImage = computed(() => getTarotCardImage(dailyMajor.value?.card_number));
const dailyPillLabel = computed(() => {
  if (!isAuthenticated.value) return "로그인 후 오늘의 카드 확인하기";
  if (isDailyMajorLoading.value) return "오늘의 카드를 불러오는 중";
  if (!dailyMajor.value) return "로그인 후 오늘의 카드 확인하기";
  if (!isDailyCardRevealed.value) return "덱을 열어 카드 확인";
  return `오늘의 메이저 카드 · ${dailyMajor.value.card_name_ko || dailyMajor.value.card_name}`;
});

const dailyCardMeaning = computed(() => {
  if (!isAuthenticated.value) {
    return "로그인 후 오늘의 카드 확인하기";
  }

  if (dailyMajor.value && !isDailyCardRevealed.value) {
    return "덱을 열어 오늘의 카드를 확인하면 카드의 정해진 의미가 표시됩니다.";
  }

  if (!dailyMajor.value) {
    return dailyMajorError.value || "생년월일을 저장하면 오늘의 카드 운세를 확인할 수 있어요.";
  }

  return dailyMajor.value.card_defined_meaning || dailyMajor.value.card_description || dailyMajor.value.message;
});

function goDraw() {
  if (!isAuthenticated.value) {
    router.push({ path: "/login", query: { redirect: "/onboarding/fortune/draw" } });
    return;
  }

  router.push({ path: "/onboarding/fortune/draw" });
}

function revealDailyCard() {
  if (!dailyMajor.value || isDailyMajorLoading.value) return;
  isDailyCardRevealed.value = true;
  saveDailyMajorCache(true);
}

function handleDailyCardClick() {
  if (!isAuthenticated.value) {
    router.push({ path: "/login", query: { redirect: "/onboarding/fortune" } });
    return;
  }

  revealDailyCard();
}

async function refreshCurrentUser() {
  try {
    const data = await userApi.getCurrentUser();
    currentUser.value = data.authenticated === false ? null : data.user || data;
  } catch {
    currentUser.value = null;
  } finally {
    authChecked.value = true;
  }
}

async function loadDailyMajor() {
  if (!isAuthenticated.value) return;

  const today = getLocalDateString();
  const cached = readDailyMajorCache(today);

  if (cached?.revealed) {
    dailyMajor.value = cached.card;
    dailyMajorError.value = "";
    isDailyCardRevealed.value = true;
    isDailyMajorLoading.value = false;
    return;
  }

  isDailyMajorLoading.value = true;
  dailyMajorError.value = "";
  isDailyCardRevealed.value = false;

  try {
    dailyMajor.value = await tarotApi.getDailyMajor(today);
  } catch (error) {
    dailyMajor.value = null;
    dailyMajorError.value = error.response?.data?.error || "오늘의 메이저 카드를 불러오지 못했어요.";
  } finally {
    isDailyMajorLoading.value = false;
  }
}

function readDailyMajorCache(date) {
  const profileSignature = getStoredProfileSignature();
  if (!profileSignature) return null;

  try {
    const cached = JSON.parse(localStorage.getItem(DAILY_MAJOR_CACHE_KEY) || "{}");
    if (
      cached.date === date &&
      cached.profileSignature === profileSignature &&
      cached.card
    ) {
      return cached;
    }
  } catch {
    return null;
  }

  return null;
}

function saveDailyMajorCache(revealed) {
  const profileSignature = getStoredProfileSignature();
  if (!profileSignature || !dailyMajor.value) return;

  localStorage.setItem(
    DAILY_MAJOR_CACHE_KEY,
    JSON.stringify({
      date: getLocalDateString(),
      profileSignature,
      revealed,
      card: dailyMajor.value,
    })
  );
}

function getStoredProfileSignature() {
  try {
    const profile = JSON.parse(localStorage.getItem(USER_PROFILE_KEY) || "{}");
    return String(profile.birth_date || profile.birthDate || profile.birthday || "").trim();
  } catch {
    return "";
  }
}

onMounted(async () => {
  await refreshCurrentUser();
  await loadDailyMajor();
});
</script>

<template>
  <section class="view-card tarot-intro-view">
    <header class="tarot-intro-hero">
      <p>오늘, 나를 위한 작은 힌트 ✦</p>
      <h1>타로 카드로 오늘의 운세를 들여다보세요</h1>
      <span>생년월일과 오늘 날짜를 바탕으로, 하루에 어울리는 카드 메시지를 전해드려요.</span>
    </header>

    <div class="tarot-panels">
      <article class="glass-panel daily-major-panel">
        <span class="panel-tab">✦ 오늘의 운세 ›</span>

        <div class="daily-main-content">
          <div class="daily-deck-stage">
            <button
              class="daily-deck-button"
              :class="{ revealed: isDailyCardRevealed }"
              type="button"
              :disabled="isDailyMajorLoading || !authChecked"
              @click="handleDailyCardClick"
            >
              <img
                v-if="isAuthenticated && isDailyCardRevealed && dailyCardImage"
                class="daily-card-image"
                :src="dailyCardImage"
                :alt="`${dailyMajor.card_name_ko} 카드`"
              >
              <img
                v-else
                class="daily-deck-box"
                :src="tarotDeckBoxImage"
                alt="오늘의 타로 덱"
              >
            </button>
          </div>

          <div class="daily-major-copy">
            <h2>오늘의 타로 운세</h2>
            <p>오늘의 메이저 카드 한 장을 뽑고, <br>하루의 운세 메시지를 확인해보세요.</p>
            <button class="tarot-glow-button" type="button" :disabled="isDailyMajorLoading || !authChecked" @click="handleDailyCardClick">
              {{ dailyPillLabel }}
            </button>
          </div>
        </div>

        <section class="meaning-box">
          <h3>✦ 카드에 담긴 의미 ✦</h3>
          <p>{{ dailyCardMeaning }}</p>
        </section>
      </article>

      <article class="glass-panel situation-panel">
        <h2>✦ 상황별 카드 운세 보러가기 ✦</h2>
        <p>궁금한 상황을 선택하고, 3장의 카드가 전하는 조언을 확인해보세요.</p>

        <div class="category-chip-row" aria-label="상황 카테고리 안내">
          <span v-for="category in categories" :key="category.id">
            <i>{{ category.icon }}</i>{{ category.label }}
          </span>
        </div>

        <div class="intro-card-spread" aria-hidden="true">
          <span><img :src="tarotCardBackImage" alt=""></span>
          <span><img :src="tarotCardBackImage" alt=""></span>
          <span><img :src="tarotCardBackImage" alt=""></span>
        </div>

        <button class="btn primary large tarot-draw-link" type="button" :disabled="!authChecked" @click="goDraw">
          카드 뽑으러 가기 ✦
        </button>
      </article>
    </div>

    <footer class="glass-panel tarot-reference-bar">
      <span>오늘의 운세카드는 하루에 한 번 확인할 수 있어요. 운세 결과는 하루를 가볍게 돌아보고 마음을 정리하는 참고용으로 활용해 주세요.</span>
      <button type="button">이용 안내 ›</button>
    </footer>
  </section>
</template>

<style scoped>
:global(html),
:global(body),
:global(#app) {
  min-height: 100%;
  overflow-x: hidden;
}

:global(body) {
  overflow-y: auto;
}

.tarot-intro-view {
  width: min(1280px, calc(100% - 64px));
  display: grid;
  gap: 22px;
  margin: 0 auto;
  padding: 28px 0 40px;
  min-height: 100vh;
  height: auto;
  overflow: visible;
}

.tarot-intro-hero {
  min-height: 220px;
  display: grid;
  place-items: center;
  align-content: center;
  gap: 14px;
  text-align: center;
}

.tarot-intro-hero p {
  margin: 0;
  color: #ffc873;
  font-size: 20px;
  font-weight: 950;
}

.tarot-intro-hero h1 {
  margin: 0;
  color: #fff1cd;
  font-size: clamp(50px, 5vw, 76px);
  line-height: 1.08;
  letter-spacing: 0;
  text-shadow: 0 16px 42px rgba(231, 62, 101, 0.28);
}

.tarot-intro-hero span {
  color: rgba(255, 245, 238, 0.82);
  font-size: 20px;
  line-height: 1.55;
}

.tarot-panels {
  display: grid;
  grid-template-columns: minmax(0, 1fr) minmax(0, 1fr);
  gap: 22px;
  align-items: start;
}

.daily-major-panel,
.situation-panel,
.tarot-reference-bar {
  border-radius: 28px;
  background:
    linear-gradient(145deg, rgba(62, 25, 76, 0.88), rgba(23, 10, 44, 0.88)),
    rgba(50, 24, 73, 0.76);
}

.daily-major-panel {
  position: relative;
  min-height: 520px;
  height: auto;
  display: flex;
  flex-direction: column;
  gap: 28px;
  align-items: stretch;
  padding: 64px 44px 38px;
  box-sizing: border-box;
  overflow: visible;
}

.daily-main-content {
  display: grid;
  grid-template-columns: minmax(160px, 0.8fr) minmax(0, 1.2fr);
  gap: 28px;
  align-items: center;
}

.panel-tab {
  position: absolute;
  left: 36px;
  top: -20px;
  height: 56px;
  display: inline-flex;
  min-height: 0;
  align-items: center;
  justify-content: center;
  gap: 8px;
  padding: 0 28px;
  border: 1px solid rgba(255, 143, 164, 0.42);
  border-radius: 0 0 18px 18px;
  background: linear-gradient(135deg, rgba(231, 62, 101, 0.42), rgba(231, 126, 110, 0.18));
  color: #fff1cd;
  font-size: 18px;
  font-weight: 950;
  line-height: 1;
  white-space: nowrap;
  box-sizing: border-box;
}

.daily-deck-stage {
  min-height: 300px;
  display: grid;
  place-items: center;
  background:
    radial-gradient(circle at center, rgba(255, 195, 102, 0.18), transparent 46%),
    radial-gradient(circle at center, rgba(231, 62, 101, 0.14), transparent 62%);
}

.daily-deck-button {
  width: min(210px, 90%);
  aspect-ratio: 0.72;
  display: grid;
  place-items: center;
  border: 0;
  background: transparent;
  cursor: pointer;
  filter: drop-shadow(0 34px 32px rgba(3, 1, 18, 0.56));
}

.daily-deck-button:disabled {
  cursor: default;
  opacity: 0.74;
}

.daily-deck-box,
.daily-card-image {
  width: 100%;
  height: 100%;
  object-fit: contain;
}

.daily-major-copy {
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: 14px;
}

.daily-major-copy h2 {
  margin: 0;
  color: #fff1cd;
  font-size: clamp(30px, 2.6vw, 42px);
  line-height: 1.2;
  word-break: keep-all;
}

.daily-major-copy p {
  margin: 0;
  color: rgba(255, 245, 238, 0.82);
  font-size: 18px;
  line-height: 1.6;
  word-break: keep-all;
  overflow-wrap: break-word;
}

.daily-pill {
  display: inline-flex;
  min-height: 36px;
  align-items: center;
  padding: 0 18px;
  border: 1px solid rgba(255, 143, 164, 0.34);
  border-radius: 999px;
  color: #ffc873;
  background: rgba(255, 255, 255, 0.06);
}

.tarot-glow-button {
  width: min(330px, 100%);
  min-height: 60px;
  margin: 10px 0 0;
  border: 1px solid rgba(255, 206, 117, 0.78);
  border-radius: 999px;
  background: linear-gradient(135deg, rgba(147, 22, 114, 0.55), rgba(231, 62, 101, 0.34));
  color: #fff1cd;
  font-size: 18px;
  font-weight: 950;
  box-shadow: 0 0 28px rgba(255, 197, 99, 0.22);
  cursor: pointer;
}

.meaning-box {
  width: 100%;
  max-height: 280px;
  overflow-y: auto;
  padding: 24px;
  border: 1px solid rgba(255, 143, 164, 0.22);
  border-radius: 18px;
  background: rgba(255, 255, 255, 0.045);
  box-sizing: border-box;
}

.meaning-box h3 {
  margin: 0 0 12px;
  color: #fff1cd;
  font-size: 20px;
  line-height: 1.3;
  word-break: keep-all;
}

.meaning-box p {
  margin: 0;
  color: rgba(255, 245, 238, 0.82);
  font-size: 16px;
  line-height: 1.7;
  word-break: keep-all;
  overflow-wrap: break-word;
  white-space: pre-line;
}

.meaning-box::-webkit-scrollbar {
  width: 6px;
}

.meaning-box::-webkit-scrollbar-thumb {
  border-radius: 999px;
  background: rgba(255, 220, 180, 0.35);
}

.meaning-box::-webkit-scrollbar-track {
  background: rgba(255, 255, 255, 0.06);
}

.situation-panel {
  min-height: 520px;
  height: auto;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 24px;
  padding: 56px 42px 38px;
  text-align: center;
  box-sizing: border-box;
  overflow: hidden;
}

.situation-panel h2 {
  max-width: 100%;
  margin: 0;
  color: #fff1cd;
  font-size: clamp(26px, 2vw, 34px);
  line-height: 1.25;
  white-space: normal;
  word-break: keep-all;
  overflow-wrap: break-word;
}

.situation-panel p {
  max-width: 500px;
  margin: 0;
  color: rgba(255, 245, 238, 0.78);
  font-size: 17px;
  line-height: 1.65;
  word-break: keep-all;
  overflow-wrap: break-word;
}

.category-chip-row {
  width: 100%;
  max-width: 520px;
  display: flex;
  flex-wrap: wrap;
  justify-content: center;
  gap: 10px;
  overflow: visible;
}

.category-chip-row span {
  min-height: 40px;
  flex: 0 1 auto;
  max-width: 100%;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  padding: 0 14px;
  border: 1px solid rgba(255, 143, 164, 0.32);
  border-radius: 999px;
  color: #fff1cd;
  background: rgba(255, 255, 255, 0.055);
  font-size: 15px;
  font-weight: 900;
  white-space: nowrap;
}

.category-chip-row i {
  color: #ff9fb2;
  font-style: normal;
}

.intro-card-spread {
  position: relative;
  width: min(300px, 80%);
  height: 170px;
  margin: 4px 0 0;
  flex: 0 0 auto;
}

.intro-card-spread span {
  position: absolute;
  left: 50%;
  bottom: 0;
  width: 104px;
  aspect-ratio: 0.68;
  transform-origin: 50% 92%;
  filter: drop-shadow(0 18px 20px rgba(3, 1, 18, 0.46));
}

.intro-card-spread span:nth-child(1) {
  transform: translateX(-116%) rotate(-13deg);
}

.intro-card-spread span:nth-child(2) {
  transform: translateX(-50%) rotate(0deg);
}

.intro-card-spread span:nth-child(3) {
  transform: translateX(16%) rotate(13deg);
}

.intro-card-spread img {
  width: 100%;
  height: 100%;
  object-fit: contain;
}

.tarot-draw-link {
  width: min(320px, 100%);
  min-height: 58px;
  flex: 0 0 auto;
  font-size: 17px;
}

.situation-panel small {
  max-width: 100%;
  color: rgba(255, 245, 238, 0.68);
  font-size: 15px;
  line-height: 1.5;
  font-weight: 850;
  word-break: keep-all;
  overflow-wrap: break-word;
}

.tarot-reference-bar {
  min-height: 78px;
  height: auto;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 18px;
  padding: 18px 32px;
}

.tarot-reference-bar span {
  color: rgba(255, 245, 238, 0.8);
  font-size: 17px;
  font-weight: 850;
}

.tarot-reference-bar button {
  min-height: 46px;
  padding: 0 22px;
  border: 1px solid rgba(255, 143, 164, 0.28);
  border-radius: 999px;
  background: rgba(255, 255, 255, 0.055);
  color: #fff1cd;
  font-weight: 950;
  cursor: pointer;
}

:global(#app .tarot-intro-view) {
  min-height: 100vh !important;
  height: auto !important;
  gap: 26px !important;
  width: min(1280px, calc(100% - 64px)) !important;
  padding: 28px 0 40px !important;
  overflow: visible !important;
}

:global(#app .tarot-intro-view .tarot-intro-hero) {
  min-height: 170px !important;
  gap: 12px !important;
}

:global(#app .tarot-intro-view .tarot-intro-hero h1) {
  font-size: clamp(48px, 6vw, 76px) !important;
  line-height: 1.05 !important;
}

:global(#app .tarot-intro-view .tarot-intro-hero p) {
  font-size: 18px !important;
  line-height: 1.7 !important;
}

:global(#app .tarot-intro-view .tarot-panels) {
  display: grid !important;
  grid-template-columns: minmax(0, 1fr) minmax(0, 1fr) !important;
  align-items: start !important;
}

:global(#app .tarot-intro-view .daily-major-panel) {
  min-height: 520px !important;
  height: auto !important;
  display: flex !important;
  flex-direction: column !important;
  align-items: stretch !important;
  gap: 28px !important;
  padding: 64px 44px 38px !important;
  overflow: visible !important;
}

:global(#app .tarot-intro-view .daily-main-content) {
  display: grid !important;
  grid-template-columns: minmax(160px, 0.8fr) minmax(0, 1.2fr) !important;
  align-items: center !important;
  gap: 28px !important;
}

:global(#app .tarot-intro-view .daily-deck-stage) {
  min-height: 300px !important;
}

:global(#app .tarot-intro-view .daily-deck-button) {
  width: min(210px, 90%) !important;
}

:global(#app .tarot-intro-view .daily-major-copy) {
  width: 100% !important;
  min-width: 0 !important;
  max-width: none !important;
  display: flex !important;
  flex-direction: column !important;
  align-items: flex-start !important;
  gap: 14px !important;
}

:global(#app .tarot-intro-view .daily-major-copy h2) {
  width: 100% !important;
  max-width: 100% !important;
  font-size: clamp(30px, 2.6vw, 42px) !important;
  line-height: 1.2 !important;
  white-space: normal !important;
  word-break: keep-all !important;
  overflow-wrap: break-word !important;
}

:global(#app .tarot-intro-view .daily-major-copy p) {
  width: 100% !important;
  max-width: 100% !important;
  white-space: normal !important;
  word-break: keep-all !important;
  overflow-wrap: break-word !important;
}

:global(#app .tarot-intro-view .tarot-glow-button) {
  min-height: 60px !important;
  margin: 10px 0 0 !important;
  font-size: 18px !important;
}

:global(#app .tarot-intro-view .meaning-box) {
  width: 100% !important;
  max-width: 100% !important;
  max-height: 280px !important;
  box-sizing: border-box !important;
  overflow-y: auto !important;
}

:global(#app .tarot-intro-view .meaning-box p) {
  display: block !important;
  overflow: visible !important;
  white-space: pre-line !important;
  -webkit-line-clamp: unset !important;
}

:global(#app .tarot-intro-view .situation-panel) {
  min-height: 520px !important;
  height: auto !important;
  display: flex !important;
  flex-direction: column !important;
  align-items: center !important;
  justify-content: center !important;
  gap: 24px !important;
  padding: 56px 42px 38px !important;
  overflow: hidden !important;
}

:global(#app .tarot-intro-view .situation-panel h2) {
  width: 100% !important;
  max-width: 100% !important;
  font-size: clamp(26px, 2vw, 34px) !important;
  line-height: 1.25 !important;
  white-space: normal !important;
  word-break: keep-all !important;
  overflow-wrap: break-word !important;
}

:global(#app .tarot-intro-view .situation-panel p) {
  display: block !important;
  overflow: visible !important;
  max-width: 500px !important;
  font-size: 17px !important;
  line-height: 1.65 !important;
  -webkit-line-clamp: unset !important;
}

:global(#app .tarot-intro-view .category-chip-row) {
  width: 100% !important;
  max-width: 520px !important;
  flex-wrap: wrap !important;
  gap: 10px !important;
  overflow: visible !important;
}

:global(#app .tarot-intro-view .category-chip-row span) {
  min-height: 40px !important;
  flex: 0 1 auto !important;
  max-width: 100% !important;
  justify-content: center !important;
  padding: 0 14px !important;
  font-size: 15px !important;
}

:global(#app .tarot-intro-view .intro-card-spread) {
  width: min(300px, 80%) !important;
  height: 170px !important;
  flex: 0 0 auto !important;
}

:global(#app .tarot-intro-view .intro-card-spread span) {
  width: 104px !important;
}

:global(#app .tarot-intro-view .tarot-draw-link) {
  width: min(320px, 100%) !important;
  min-height: 58px !important;
  font-size: 17px !important;
}

@media (max-width: 1080px) {
  .tarot-intro-view {
    width: min(calc(100% - 28px), 860px);
  }

  :global(#app .tarot-intro-view) {
    width: min(calc(100% - 28px), 860px) !important;
  }

  .tarot-panels {
    grid-template-columns: 1fr;
  }

  :global(#app .tarot-intro-view .tarot-panels) {
    grid-template-columns: 1fr !important;
  }

  .daily-main-content {
    grid-template-columns: 1fr;
    text-align: center;
  }

  :global(#app .tarot-intro-view .daily-main-content) {
    grid-template-columns: 1fr !important;
    text-align: center !important;
  }

  .daily-major-copy {
    align-items: center;
  }

  :global(#app .tarot-intro-view .daily-major-copy) {
    align-items: center !important;
  }

  .daily-major-panel {
    padding-top: 64px;
  }

  :global(#app .tarot-intro-view .daily-major-panel) {
    padding-top: 64px !important;
  }

  .daily-deck-stage {
    min-height: 260px;
  }

  :global(#app .tarot-intro-view .daily-deck-stage) {
    min-height: 260px !important;
  }

  .daily-deck-button {
    width: min(190px, 70%);
  }

  :global(#app .tarot-intro-view .daily-deck-button) {
    width: min(190px, 70%) !important;
  }
}

@media (max-width: 720px) {
  .tarot-intro-hero {
    min-height: 180px;
  }

  :global(#app .tarot-intro-view .tarot-intro-hero) {
    min-height: 180px !important;
  }

  .tarot-intro-hero h1 {
    font-size: clamp(36px, 10vw, 48px);
  }

  :global(#app .tarot-intro-view .tarot-intro-hero h1) {
    font-size: clamp(36px, 10vw, 48px) !important;
  }

  .tarot-intro-hero span {
    font-size: 16px;
  }

  .daily-major-panel,
  .situation-panel,
  .tarot-reference-bar {
    padding: 56px 24px 28px;
  }

  :global(#app .tarot-intro-view .daily-major-panel),
  :global(#app .tarot-intro-view .situation-panel),
  :global(#app .tarot-intro-view .tarot-reference-bar) {
    padding: 56px 24px 28px !important;
  }

  .panel-tab {
    left: 24px;
    top: -16px;
    height: 48px;
    padding: 0 20px;
    font-size: 16px;
  }

  .daily-main-content {
    gap: 20px;
  }

  :global(#app .tarot-intro-view .daily-main-content) {
    gap: 20px !important;
  }

  .daily-deck-stage {
    min-height: 220px;
  }

  :global(#app .tarot-intro-view .daily-deck-stage) {
    min-height: 220px !important;
  }

  .daily-major-copy h2 {
    font-size: clamp(28px, 8vw, 36px);
  }

  :global(#app .tarot-intro-view .daily-major-copy h2) {
    font-size: clamp(28px, 8vw, 36px) !important;
  }

  .meaning-box {
    max-height: 300px;
  }

  :global(#app .tarot-intro-view .meaning-box) {
    max-height: 300px !important;
  }

  .situation-panel h2 {
    white-space: normal;
  }

  .category-chip-row {
    flex-wrap: wrap;
  }

  .tarot-reference-bar {
    display: grid;
  }
}

@media (min-width: 1281px) {
  /* Keep this page in the same two-panel desktop composition. */
  :global(#app .tarot-intro-view) {
    width: 1280px !important;
    min-width: 1280px !important;
    min-height: 850px !important;
    height: auto !important;
    gap: 22px !important;
    margin: 0 auto !important;
    padding: 28px 0 40px !important;
    overflow: visible !important;
  }

  :global(#app .tarot-intro-view .tarot-intro-hero) {
    min-height: 190px !important;
    gap: 14px !important;
  }

  :global(#app .tarot-intro-view .tarot-intro-hero h1) {
    font-size: 64px !important;
    line-height: 1.08 !important;
  }

  :global(#app .tarot-intro-view .tarot-intro-hero p),
  :global(#app .tarot-intro-view .tarot-intro-hero span) {
    font-size: 19px !important;
  }

  :global(#app .tarot-intro-view .tarot-panels) {
    grid-template-columns: repeat(2, minmax(0, 1fr)) !important;
    gap: 22px !important;
  }

  :global(#app .tarot-intro-view .daily-major-panel),
  :global(#app .tarot-intro-view .situation-panel) {
    min-height: 520px !important;
    height: auto !important;
    padding: 56px 42px 38px !important;
  }

  :global(#app .tarot-intro-view .daily-main-content) {
    grid-template-columns: 190px minmax(0, 1fr) !important;
    gap: 28px !important;
    text-align: left !important;
  }

  :global(#app .tarot-intro-view .daily-deck-stage) {
    min-height: 300px !important;
  }

  :global(#app .tarot-intro-view .daily-deck-button) {
    width: 210px !important;
  }

  :global(#app .tarot-intro-view .daily-major-copy) {
    align-items: flex-start !important;
  }

  :global(#app .tarot-intro-view .daily-major-copy h2),
  :global(#app .tarot-intro-view .situation-panel h2) {
    font-size: 34px !important;
    line-height: 1.25 !important;
  }

  :global(#app .tarot-intro-view .daily-major-copy p),
  :global(#app .tarot-intro-view .situation-panel p) {
    font-size: 17px !important;
    line-height: 1.6 !important;
  }

  :global(#app .tarot-intro-view .intro-card-spread) {
    width: 300px !important;
    height: 170px !important;
  }

  :global(#app .tarot-intro-view .intro-card-spread span) {
    width: 104px !important;
  }
}

@media (max-width: 1280px) {
  :global(#app .tarot-intro-view) {
    width: calc(100% - 48px) !important;
    max-width: 1180px !important;
    min-width: 0 !important;
    min-height: auto !important;
  }

  :global(#app .tarot-intro-view .tarot-panels) {
    grid-template-columns: repeat(2, minmax(0, 1fr)) !important;
  }
}

@media (max-width: 1024px) {
  :global(#app .tarot-intro-view) {
    width: min(calc(100% - 40px), 900px) !important;
  }

  :global(#app .tarot-intro-view .tarot-panels),
  :global(#app .tarot-intro-view .daily-main-content) {
    grid-template-columns: 1fr !important;
  }
}

@media (max-width: 720px) {
  :global(#app .tarot-intro-view) {
    width: calc(100% - 24px) !important;
  }
}
</style>

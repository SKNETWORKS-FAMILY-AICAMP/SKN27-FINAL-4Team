<script setup>
import { ref, computed, onMounted } from "vue";
import { userApi } from "../../api/user.js";

defineEmits(["navigate"]);

import mindReportIcon from "../../assets/icons/feature-mind-report.png";
import mindCalendarIcon from "../../assets/icons/feature-mind-calendar.png";

const currentUser = ref(null);
const displayName = computed(
  () => currentUser.value?.nickname || currentUser.value?.name || "회원",
);

onMounted(async () => {
  try {
    const data = await userApi.getCurrentUser();
    if (data?.authenticated) {
      currentUser.value = data.user || data;
    }
  } catch {
    // 비로그인/오류 시 기본 인사말 유지
  }
});

const features = [
  {
    id: "report",
    iconSrc: mindReportIcon,
    title: "마음 리포트",
    desc: "나의 감정 패턴과 변화\u00a0추이를\n시각적으로 확인해요."
  },
  {
    id: "calendar",
    iconSrc: mindCalendarIcon,
    title: "마음 캘린더",
    desc: "날짜별 감정과 운세\u00a0기록을\n캘린더로 모아봐요."
  }
];

const contentActions = [
  {
    id: "mycard",
    icon: "my-card",
    title: "마음 카드 만들기",
    desc: "나만의 마음 카드를 만들어\n오늘 하루를 되돌아봐요.",
  },
  {
    id: "memory-game",
    icon: "memory-game",
    title: "캐릭터 카드 맞추기",
    desc: "캐릭터 카드 짝을 맞추며\n재밌게 놀아요."
  },
  {
    id: "fortune",
    title: "카드 운세보기",
    desc: "타로 카드를 통해\n오늘의 운세를 알아봐요."
  }
];
</script>

<template>
  <section class="view-card home-view">
    <div class="home-copy-zone">
      <div class="eyebrow">
        <span aria-hidden="true">✦</span>
        반가워요, {{ displayName }}님 <span aria-hidden="true">✦</span>
      </div>
      <h1>오늘도 수고했어요.<br>당신의 마음이 쉬어갈 수 있는 곳,<br><em>빈틈사이✨</em></h1>
      <p class="hero-copy">
        잠시 멈춘 하루의 틈에서 감정을 기록하고,<br>다정한 대화로 마음의 온도를 천천히 올려보세요.
      </p>

      <div class="hero-actions">
        <button class="btn primary large" type="button" @click="$emit('navigate', 'chat')">
          마음 대화 시작하기
        </button>
        <button class="btn secondary large" type="button" @click="$emit('navigate', 'my')">
          다락방 둘러보기
        </button>
      </div>
    </div>

    <aside class="feature-dock" aria-label="핵심 기능">
      <button
        v-for="feature in features"
        :key="feature.id"
        class="feature-card"
        type="button"
        @click="$emit('navigate', feature.id)"
      >
        <img class="feature-icon" :src="feature.iconSrc" :alt="`${feature.title} 아이콘`">
        <span class="feature-copy"><strong>{{ feature.title }}</strong><small>{{ feature.desc }}</small></span>
        <span class="feature-meta">{{ feature.meta }}</span>
        <span class="feature-arrow" aria-hidden="true">›</span>
      </button>
    </aside>

    <div class="content-actions tarot-only-actions" aria-label="오늘의 콘텐츠 바로가기">
        <button
          v-for="action in contentActions"
          :key="action.id"
          :class="['content-action', 'tarot-game-action', 'glass-panel', action.id + '-action']"
          type="button"
          @click="$emit('navigate', action.id)"
        >
          <span class="sticker-icon" :class="action.icon"></span>
          <span>
            <strong>{{ action.title }}</strong>
            <small>{{ action.desc }}</small>
            <em>{{ action.meta }}</em>
          </span>
          <span class="content-action-arrow" aria-hidden="true">›</span>
        </button>
    </div>

    <p class="home-closing-note">☆ 기록이 모여, 당신의 마음을 더 단단하게 만들어요. <span>♥</span></p>
  </section>
</template>

<style scoped>
.home-view {
  width: min(1760px, calc(100vw - 56px));
  min-height: 850px;
  margin: 24px auto 28px;
  padding: clamp(42px, 5.8vh, 66px) 44px 34px;
  display: block !important;
  grid-template-columns: none !important;
  align-items: initial !important;
  padding: 66px 44px 72px !important;
  position: relative;
  overflow: visible;
  border: 1px solid rgba(231, 62, 101, 0.36);
  border-radius: 28px;
  background:
    linear-gradient(90deg, rgba(20, 9, 31, 0.82) 0%, rgba(20, 9, 31, 0.42) 38%, rgba(20, 9, 31, 0.06) 66%),
    linear-gradient(180deg, rgba(20, 9, 31, 0.1), rgba(20, 9, 31, 0.52)),
    url("../../assets/bg-main.png") center center / cover no-repeat;
  box-shadow: 0 28px 90px rgba(20, 9, 31, 0.42);
}

.home-copy-zone {
  position: relative;
  z-index: 1;
  max-width: 880px !important;
}

.eyebrow {
  width: fit-content;
  min-height: 46px;
  display: inline-flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 24px;
  padding: 0 22px;
  border: 1px solid rgba(231, 62, 101, 0.32);
  border-radius: 999px;
  color: #ffb49f;
  background: rgba(50, 24, 73, 0.42);
  font-weight: 900;
}

.soft-dot {
  width: 10px;
  height: 10px;
  border-radius: 50%;
  background: #e77e6e;
  box-shadow: 0 0 18px rgba(231, 126, 110, 0.7);
}

.home-copy-zone h1 {
  margin: 0 0 22px;
  color: #ffd7bd;
  font-size: clamp(42px, 3.2vw, 56px);
  line-height: 1.16;
  font-weight: 900;
  letter-spacing: 0;
  text-shadow: 0 14px 44px rgba(231, 62, 101, 0.32);
}

.hero-copy {
  max-width: 600px;
  margin: 0 0 28px;
  color: rgba(255, 245, 238, 0.84);
  font-size: 20px;
  line-height: 1.65;
}

.hero-actions {
  display: flex;
  gap: 22px;
  margin-bottom: 24px;
}

.hero-actions .btn {
  min-width: 260px;
  min-height: 64px;
  border-radius: 20px;
  font-size: 20px;
  font-weight: 900;
}

.tarot-only-actions {
  width: 100%;
  max-width: none !important;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 22px;
  margin-bottom: 22px;
}

.tarot-game-action {
  min-height: clamp(122px, 14vh, 148px);
  grid-template-columns: 120px minmax(0, 1fr) 48px !important;
  align-items: center;
  gap: 18px;
  padding: 22px 22px;
  border-radius: 22px;
  position: relative;
  overflow: hidden;
  background:
    linear-gradient(145deg, rgba(147, 22, 114, 0.44), rgba(50, 24, 73, 0.68)),
    rgba(20, 9, 31, 0.58) !important;
  border-color: rgba(231, 62, 101, 0.34) !important;
}

.tarot-game-action::after {
  content: none;
}

.tarot-game-action .sticker-icon {
  width: 112px;
  height: 96px;
  border-radius: 0;
  background:
    url("../../assets/tarot/tarot-card-back.png") left center / 52px auto no-repeat,
    url("../../assets/tarot/tarot-card-back.png") center center / 52px auto no-repeat,
    url("../../assets/tarot/tarot-card-back.png") right center / 52px auto no-repeat;
  box-shadow: none;
}

.tarot-game-action strong {
  font-size: 24px;
}

.tarot-game-action small {
  margin-top: 10px;
  font-size: 15px;
  line-height: 1.5;
}

.tarot-game-action > span:last-child::after {
  content: "›";
  position: absolute;
  right: 20px;
  top: 50%;
  width: 42px;
  height: 42px;
  display: grid;
  place-items: center;
  border: 1px solid rgba(255, 245, 238, 0.22);
  border-radius: 50%;
  color: white;
  font-size: 28px;
  transform: translateY(-50%);
}

.feature-dock {
  position: relative !important;
  left: auto !important;
  bottom: auto !important;
  z-index: 1;
  width: min(1140px, 100%);
  margin-top: 18px;
  margin-bottom: 8px;
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr)) !important;
  gap: 22px;
  background: transparent !important;
  border: 0 !important;
  box-shadow: none !important;
  backdrop-filter: none !important;
  padding: 0;
}

.feature-card {
  min-height: clamp(132px, 14vh, 154px);
  display: grid;
  grid-template-columns: 78px minmax(0, 1fr) 34px;
  align-items: center;
  gap: 20px;
  padding: 26px 24px;
  border: 1px solid rgba(231, 62, 101, 0.34);
  border-radius: 18px;
  background:
    linear-gradient(145deg, rgba(147, 22, 114, 0.32), rgba(50, 24, 73, 0.62)),
    rgba(20, 9, 31, 0.52) !important;
  box-shadow: inset 0 1px 0 rgba(255, 245, 238, 0.1);
  transition: transform 0.15s ease, border-color 0.15s ease;
}

.feature-card .sticker-icon {
  width: 72px;
  height: 72px;
  grid-row: 1 / span 2;
}

.feature-card strong {
  grid-column: 2;
  grid-row: 1;
  align-self: end;
  font-size: 26px;
}

.feature-card small {
  grid-column: 2;
  grid-row: 2;
  align-self: start;
  margin-top: 8px;
  font-size: 17px;
  line-height: 1.45;
}

.feature-card::after {
  content: "›";
  grid-column: 3;
  grid-row: 1 / span 2;
  color: rgba(255, 245, 238, 0.72);
  font-size: 26px;
}

.feature-card {
  cursor: pointer;
}

.feature-card:hover {
  transform: translateY(-2px);
  border-color: rgba(255, 129, 150, 0.55);
}

@media (max-width: 1100px) {
  .tarot-only-actions {
    grid-template-columns: 1fr;
  }
}

@media (max-width: 720px) {
  .home-view {
    padding: 28px 18px;
  }

  .hero-actions {
    flex-direction: column;
  }

  .hero-actions .btn {
    width: 100%;
    min-width: 0;
  }

  .tarot-game-action {
    grid-template-columns: 1fr !important;
    min-height: 128px;
    padding: 22px;
  }

  .feature-dock {
    width: 100%;
    grid-template-columns: 1fr !important;
  }
}
</style>

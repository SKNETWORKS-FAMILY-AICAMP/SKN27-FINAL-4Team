<script setup>
defineEmits(["navigate"]);

import mindChatIcon from "../../assets/icons/mind-chat.png";
import emotionRecordIcon from "../../assets/icons/emotion-record.png";
import mindReportIcon from "../../assets/icons/mind-report.png";

const features = [
  {
    id: "chat",
    iconSrc: mindChatIcon,
    title: "마음 대화",
    desc: "대화로 감정을 천천히 풀어내는 공간이에요."
  },
  {
    id: "my",
    iconSrc: emotionRecordIcon,
    title: "감정 기록",
    desc: "오늘의 감정과 생각을 차곡차곡 기록해요."
  },
  {
    id: "report",
    iconSrc: mindReportIcon,
    title: "마음 리포트",
    desc: "쌓인 기록을 바탕으로 감정 흐름을 살펴봐요."
  }
];

const contentActions = [
  {
    id: "mycard",
    icon: "my-card",
    title: "마음 카드 만들기",
    desc: "오늘의 마음과 장면을 담아\n나만의 카드를 만들어보세요."
  },
  {
    id: "fortune",
    title: "카드 운세 보기",
    desc: "타로카드를 통해 오늘의 운세를 확인하고,\n상황 별 조언을 들어보세요."
  },
  {
    id: "memory-game",
    icon: "memory-game",
    title: "캐릭터 카드 맞추기",
    desc: "포리와 친구들의 같은 카드를 찾아\n90초 안에 12쌍을 맞춰보세요."
  }
];
</script>

<template>
  <section class="view-card home-view">
    <div class="home-copy-zone">
      <div class="eyebrow">
        <span class="soft-dot"></span>
        오늘은 잠시 쉬어가도 괜찮아요
      </div>
      <h1>바쁜 하루의 빈틈 사이,<br>마음을 쉬어가요</h1>
      <p class="hero-copy">
        잠시 생긴 하루의 틈에서 감정을 기록하고, <br>대화와 리포트로 마음의 흐름을 천천히 정리해요.
      </p>

      <div class="hero-actions">
        <button class="btn primary large" type="button" @click="$emit('navigate', 'chat')">
          마음 대화 시작하기
        </button>
        <button class="btn secondary large" type="button" @click="$emit('navigate', 'my')">
          다락방 둘러보기
        </button>
      </div>

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
          </span>
        </button>
      </div>
    </div>

    <aside class="feature-dock" aria-label="핵심 기능">
      <article
        v-for="feature in features"
        :key="feature.id"
        class="feature-card"
      >
      <img
      class="feature-icon"
      :src="feature.iconSrc"
      :alt="`${feature.title} 아이콘`"
      />
        <strong>{{ feature.title }}</strong>
        <small>{{ feature.desc }}</small>
      </article>
    </aside>
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
  font-size: clamp(54px, 4.1vw, 70px);
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
  width: min(740px, 100%);
  max-width: 740px !important;
  grid-template-columns: 1fr;
  margin-bottom: 22px;
}

.tarot-game-action {
  min-height: clamp(142px, 16vh, 174px);
  grid-template-columns: 220px minmax(0, 1fr) 54px !important;
  align-items: center;
  gap: 28px;
  padding: 26px 28px;
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
  width: 190px;
  height: 124px;
  border-radius: 0;
  background:
    url("../../assets/tarot/tarot-card-back.png") left center / 86px auto no-repeat,
    url("../../assets/tarot/tarot-card-back.png") center center / 86px auto no-repeat,
    url("../../assets/tarot/tarot-card-back.png") right center / 86px auto no-repeat;
  box-shadow: none;
}

.tarot-game-action strong {
  font-size: 30px;
}

.tarot-game-action small {
  margin-top: 12px;
  font-size: 18px;
  line-height: 1.55;
}

.tarot-game-action > span:last-child::after {
  content: "›";
  position: absolute;
  right: 28px;
  top: 50%;
  width: 48px;
  height: 48px;
  display: grid;
  place-items: center;
  border: 1px solid rgba(255, 245, 238, 0.22);
  border-radius: 50%;
  color: white;
  font-size: 34px;
  transform: translateY(-50%);
}

.feature-dock {
  position: relative !important;
  left: auto !important;
  bottom: auto !important;
  z-index: 1;
  width: min(1140px, calc(100% - 88px));
  margin-top: 18px;
  margin-bottom: 8px;
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr)) !important;
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
  cursor: default;
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

.feature-card:hover {
  transform: none;
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

  .tarot-only-actions {
    grid-template-columns: 1fr;
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

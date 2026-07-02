<script setup>
defineEmits(["navigate"]);

const stats = [
  { value: "1,248", label: "오늘의 대화 수" },
  { value: "38K", label: "함께 걷는 사용자" },
  { value: "92K", label: "기록된 마음 일기" }
];

const features = [
  {
    id: "chat",
    icon: "talk",
    title: "마음 대화",
    desc: "마음 동행자와 지금 감정을 차분히 나눠요."
  },
  {
    id: "my",
    icon: "diary",
    title: "감정 기록",
    desc: "하루의 조각을 나만의 다락방에 남겨요."
  },
  {
    id: "report",
    icon: "chart",
    title: "마음 리포트",
    desc: "반복되는 감정 흐름을 부드럽게 살펴요."
  }
];

const contentActions = [
  {
    id: "balance",
    icon: "balance",
    title: "심리 밸런스 게임",
    desc: "가벼운 선택으로 오늘의 성향을 알아봐요."
  },
  {
    id: "fortune",
    icon: "fortune",
    title: "카드 운세 보기",
    desc: "한 장의 카드로 오늘의 조언을 받아요."
  }
];
</script>

<template>
  <section class="view-card home-view">
    <div class="home-copy-zone">
      <div class="eyebrow">
        <span class="soft-dot"></span>
        오늘도 잠시 쉬어가도 괜찮아요
      </div>
      <h1>노을 아래,<br>마음이 쉬어가는 다락방</h1>
      <p class="hero-copy">
        하루의 감정을 기록하고, AI 동행자와 함께 마음의 조각을 천천히 정리해요.
      </p>

      <div class="hero-actions">
        <button class="btn primary large" type="button" @click="$emit('navigate', 'login')">
          산책 시작하기
        </button>
        <button class="btn secondary large" type="button" @click="$emit('navigate', 'my')">
          다락방 둘러보기
        </button>
      </div>

      <div class="content-actions" aria-label="오늘의 콘텐츠 바로가기">
        <button
          v-for="action in contentActions"
          :key="action.id"
          class="content-action glass-panel"
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

      <div class="stat-strip glass-panel" aria-label="서비스 이용 상태">
        <div v-for="stat in stats" :key="stat.label" class="stat-item">
          <strong>{{ stat.value }}</strong>
          <span>{{ stat.label }}</span>
        </div>
      </div>

      <div class="mascot-note">
        <div class="tiny-mascot" aria-hidden="true">
          <span class="mascot-face"></span>
        </div>
        <p>조금 느려도 괜찮아요. 오늘의 마음부터 같이 놓아볼게요.</p>
      </div>
    </div>

    <aside class="feature-dock glass-panel" aria-label="핵심 기능">
      <button
        v-for="feature in features"
        :key="feature.id"
        class="feature-card"
        type="button"
        @click="$emit('navigate', feature.id)"
      >
        <span class="sticker-icon" :class="feature.icon"></span>
        <strong>{{ feature.title }}</strong>
        <small>{{ feature.desc }}</small>
      </button>
    </aside>
  </section>
</template>

<script setup>
import { ref } from "vue";

defineEmits(["navigate"]);

const selected = ref("B");
const categories = ["관계", "취미", "휴식", "종합"];
const options = [
  {
    id: "A",
    title: "익숙한 사람과 깊은 대화",
    desc: "좁고 단단한 연결에서 마음이 편해져요."
  },
  {
    id: "B",
    title: "새로운 사람과 가벼운 산책",
    desc: "낯선 자극이 생각을 환기해줘요."
  }
];
const traits = [
  { label: "안정 추구", value: 68 },
  { label: "새로움 수용", value: 54 },
  { label: "감정 표현", value: 76 }
];

function choose(option) {
  selected.value = option;
}
</script>

<template>
  <section class="view-card content-view balance-view">
    <article class="glass-panel content-main-panel">
      <div class="content-heading">
        <div>
          <p class="section-kicker">Balance game</p>
          <h2>심리 밸런스 게임</h2>
          <p>가벼운 선택으로 오늘의 성향 데이터를 모으고, 해온이가 대화 톤을 더 섬세하게 맞춰요.</p>
        </div>
        <button class="btn secondary small" type="button" @click="$emit('navigate', 'home')">홈으로</button>
      </div>

      <div class="category-tabs">
        <button v-for="category in categories" :key="category" type="button" :class="{ active: category === '관계' }">
          {{ category }}
        </button>
      </div>

      <section class="question-card">
        <div class="question-meta">
          <span>질문 03 / 08</span>
          <strong>지금 더 끌리는 쪽은?</strong>
        </div>
        <div class="balance-options">
          <button
            v-for="option in options"
            :key="option.id"
            type="button"
            :class="{ selected: selected === option.id }"
            @click="choose(option.id)"
          >
            <span>{{ option.id }}</span>
            <strong>{{ option.title }}</strong>
            <small>{{ option.desc }}</small>
          </button>
        </div>
        <div class="progress-track"><i></i></div>
      </section>
    </article>

    <aside class="glass-panel content-side-panel">
      <div class="tiny-mascot mini" aria-hidden="true">
        <span class="mascot-face"></span>
      </div>
      <h3>선택 후 바로 저장돼요</h3>
      <p>중간에 나가도 진행률과 선택 상태를 이어갈 수 있는 흐름으로 설계했어요.</p>
      <div class="trait-list">
        <div v-for="trait in traits" :key="trait.label" class="trait-row" :style="{ '--value': trait.value + '%' }">
          <span>{{ trait.label }}</span>
          <div><i></i></div>
          <strong>{{ trait.value }}%</strong>
        </div>
      </div>
      <button class="btn primary full" type="button">다음 질문</button>
    </aside>
  </section>
</template>

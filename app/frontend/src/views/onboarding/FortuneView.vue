<script setup>
import { ref } from "vue";

defineEmits(["navigate"]);

const selectedCategory = ref("관계");
const selectedCard = ref(2);
const categories = ["관계", "재물", "성공", "직업운"];
const cards = [
  { id: 1, title: "첫 번째 카드" },
  { id: 2, title: "두 번째 카드" },
  { id: 3, title: "세 번째 카드" },
  { id: 4, title: "네 번째 카드" },
  { id: 5, title: "다섯 번째 카드" }
];

function pickCard(card) {
  selectedCard.value = card;
}
</script>

<template>
  <section class="view-card content-view fortune-view">
    <article class="glass-panel content-main-panel">
      <div class="content-heading">
        <div>
          <p class="section-kicker">Card fortune</p>
          <h2>카드 운세 보기</h2>
          <p>카테고리를 고르고 마음이 끌리는 카드 한 장을 선택하면, 오늘의 짧은 조언을 보여줘요.</p>
        </div>
        <button class="btn secondary small" type="button" @click="$emit('navigate', 'home')">홈으로</button>
      </div>

      <div class="category-tabs">
        <button
          v-for="category in categories"
          :key="category"
          type="button"
          :class="{ active: selectedCategory === category }"
          @click="selectedCategory = category"
        >
          {{ category }}
        </button>
      </div>

      <div class="fortune-deck" aria-label="운세 카드 선택">
        <button
          v-for="card in cards"
          :key="card.id"
          class="fortune-card"
          type="button"
          :class="{ selected: selectedCard === card.id }"
          @click="pickCard(card.id)"
        >
          <span class="card-orbit"></span>
          <strong>{{ card.title }}</strong>
        </button>
      </div>
    </article>

    <aside class="glass-panel content-side-panel fortune-result">
      <span class="sticker-icon fortune"></span>
      <h3>오늘의 관계운</h3>
      <p class="fortune-copy">
        오늘은 먼저 다가가기보다, 상대의 말 사이에 숨은 피로를 조용히 알아차리는 날이에요.
      </p>
      <div class="advice-box">
        <strong>오늘의 조언</strong>
        <span>짧은 안부 하나가 오래 남을 수 있어요. 답을 재촉하지 않는 문장으로 시작해봐요.</span>
      </div>
      <button class="btn primary full" type="button">운세 저장하기</button>
    </aside>
  </section>
</template>

<script setup>
import { nextTick, onMounted, ref } from "vue";

defineProps({
  status: { type: String, required: true }, // "WON" | "TIMEOUT"
  matchedPairCount: { type: Number, required: true },
  formattedTime: { type: String, required: true },
});

defineEmits(["retry", "home"]);

const firstButton = ref(null);

onMounted(async () => {
  await nextTick();
  firstButton.value?.focus();
});
</script>

<template>
  <div class="modal-backdrop" role="dialog" aria-modal="true">
    <div class="modal memory-result-modal">
      <template v-if="status === 'WON'">
        <p class="memory-result-icon" aria-hidden="true">✦</p>
        <h3>모든 짝을 찾았어요!</h3>
        <p class="memory-result-body">포리와 친구들의 카드 12쌍을 모두 맞췄어요.</p>
        <p class="memory-result-sub">남은 시간 {{ formattedTime }}</p>
        <div class="memory-result-actions">
          <button ref="firstButton" type="button" class="btn primary large" @click="$emit('retry')">한 번 더 하기</button>
          <button type="button" class="btn secondary large" @click="$emit('home')">홈으로 돌아가기</button>
        </div>
      </template>
      <template v-else>
        <h3>시간이 끝났어요</h3>
        <p class="memory-result-body">아쉽지만 괜찮아요.<br>카드를 다시 섞어 한 번 더 도전해보세요.</p>
        <p class="memory-result-sub">찾은 짝 {{ matchedPairCount }} / 12</p>
        <div class="memory-result-actions">
          <button ref="firstButton" type="button" class="btn primary large" @click="$emit('retry')">다시 도전하기</button>
          <button type="button" class="btn secondary large" @click="$emit('home')">홈으로 돌아가기</button>
        </div>
      </template>
    </div>
  </div>
</template>

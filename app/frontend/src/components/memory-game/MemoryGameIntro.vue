<script setup>
defineProps({
  backImage: { type: String, default: "" },
  isLoading: { type: Boolean, default: false },
  errorMessage: { type: String, default: "" },
});

defineEmits(["start", "home"]);
</script>

<template>
  <article class="glass-panel memory-game-intro">
    <span class="memory-game-badge">제한 시간 90초</span>
    <h2 class="memory-game-title">캐릭터 카드 짝 맞추기</h2>
    <p class="memory-game-desc">
      같은 캐릭터 카드를 찾아 짝을 맞춰보세요.<br>
      90초 안에 12쌍을 모두 찾으면 완료예요.
    </p>
    <p class="memory-game-rule">카드를 두 장씩 뒤집어 같은 그림을 찾아주세요.</p>

    <div class="memory-game-back-preview" aria-hidden="true">
      <span><img v-if="backImage" :src="backImage" alt=""></span>
      <span><img v-if="backImage" :src="backImage" alt=""></span>
      <span><img v-if="backImage" :src="backImage" alt=""></span>
    </div>

    <p v-if="isLoading" class="memory-game-status">카드를 준비하고 있어요...</p>
    <p v-else-if="errorMessage" class="memory-game-status memory-game-status--error" role="alert">
      {{ errorMessage }}
    </p>

    <div class="memory-game-intro-actions">
      <button
        type="button"
        class="btn primary large"
        :disabled="isLoading"
        @click="$emit('start')"
      >
        {{ errorMessage ? "다시 시도" : "게임 시작" }}
      </button>
      <button type="button" class="btn secondary large" :disabled="isLoading" @click="$emit('home')">
        홈으로 돌아가기
      </button>
    </div>
  </article>
</template>

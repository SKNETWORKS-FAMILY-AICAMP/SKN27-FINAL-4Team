<script setup>
const props = defineProps({
  progressLabel: { type: String, required: true },
  formattedTime: { type: String, required: true },
  remainingSeconds: { type: Number, required: true },
  isPreview: { type: Boolean, default: false },
});

defineEmits(["back", "restart"]);

function timerUrgency() {
  if (props.remainingSeconds <= 10) return "urgent";
  if (props.remainingSeconds <= 30) return "warn";
  return "";
}
</script>

<template>
  <div class="memory-game-toolbar">
    <button type="button" class="memory-toolbar-back" aria-label="홈으로 돌아가기" @click="$emit('back')">
      ←
    </button>
    <strong class="memory-toolbar-title">캐릭터 카드 짝 맞추기</strong>
    <span v-if="isPreview" class="memory-toolbar-progress memory-toolbar-preview" aria-live="polite">카드를 기억하세요!</span>
    <span v-else class="memory-toolbar-progress" aria-live="polite">{{ progressLabel }}</span>
    <span class="memory-toolbar-timer" :class="isPreview ? '' : timerUrgency()" aria-live="polite">{{ isPreview ? '준비 중' : formattedTime }}</span>
    <button type="button" class="memory-toolbar-restart" @click="$emit('restart')">처음부터</button>
  </div>
</template>

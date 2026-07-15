<script setup>
const props = defineProps({
  progressLabel: { type: String, required: true },
  formattedTime: { type: String, required: true },
  remainingSeconds: { type: Number, required: true },
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
    <span class="memory-toolbar-progress" aria-live="polite">{{ progressLabel }}</span>
    <span class="memory-toolbar-timer" :class="timerUrgency()" aria-live="polite">{{ formattedTime }}</span>
    <button type="button" class="memory-toolbar-restart" @click="$emit('restart')">처음부터</button>
  </div>
</template>

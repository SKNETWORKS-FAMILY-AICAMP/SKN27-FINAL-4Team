<script setup>
const props = defineProps({
  card: { type: Object, required: true },
  backImage: { type: String, default: "" },
});

const emit = defineEmits(["flip"]);

function ariaLabel() {
  if (props.card.isMatched) return "짝을 맞춘 카드";
  if (props.card.isFlipped) return "선택한 카드";
  return "뒤집히지 않은 카드";
}

function onClick() {
  emit("flip", props.card.instanceId);
}
</script>

<template>
  <button
    type="button"
    class="memory-card"
    :class="{ 'is-flipped': card.isFlipped || card.isMatched, 'is-matched': card.isMatched }"
    :disabled="card.isMatched"
    :aria-label="ariaLabel()"
    @click="onClick"
  >
    <span class="memory-card__inner">
      <span class="memory-card__face memory-card__face--back">
        <img :src="backImage" alt="" draggable="false">
      </span>
      <span class="memory-card__face memory-card__face--front">
        <img v-if="card.isFlipped || card.isMatched" :src="card.imageUrl" :alt="card.alt" draggable="false">
      </span>
    </span>
  </button>
</template>

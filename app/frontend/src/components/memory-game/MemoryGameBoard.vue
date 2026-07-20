<script setup>
import MemoryGameCard from "./MemoryGameCard.vue";

defineProps({
  cards: { type: Array, required: true },
  backImage: { type: String, default: "" },
});

const emit = defineEmits(["card-click"]);

function onFlip(instanceId) {
  emit("card-click", instanceId);
}
</script>

<template>
  <div class="memory-game-board" role="group" aria-label="카드 짝 맞추기 게임판">
    <MemoryGameCard
      v-for="card in cards"
      :key="card.instanceId"
      :card="card"
      :back-image="backImage"
      @flip="onFlip"
    />
  </div>
</template>

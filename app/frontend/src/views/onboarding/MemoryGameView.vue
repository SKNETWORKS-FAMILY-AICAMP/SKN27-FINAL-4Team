<script setup>
import { useRouter } from "vue-router";
import MemoryGameBoard from "../../components/memory-game/MemoryGameBoard.vue";
import MemoryGameIntro from "../../components/memory-game/MemoryGameIntro.vue";
import MemoryGameResultModal from "../../components/memory-game/MemoryGameResultModal.vue";
import MemoryGameToolbar from "../../components/memory-game/MemoryGameToolbar.vue";
import { useMemoryGame } from "../../composables/useMemoryGame.js";

const router = useRouter();
const {
  state,
  GAME_STATUS,
  remainingSeconds,
  formattedTime,
  progressLabel,
  isFinished,
  cardBackImage,
  startGame,
  restartGame,
  handleCardClick,
  goToIdle,
} = useMemoryGame();

function goHome() {
  goToIdle();
  router.push("/home");
}
</script>

<template>
  <section class="memory-game-view">
    <MemoryGameIntro
      v-if="state.gameStatus === GAME_STATUS.IDLE || state.gameStatus === GAME_STATUS.ERROR || (state.gameStatus === GAME_STATUS.LOADING && state.cards.length === 0)"
      :back-image="cardBackImage"
      :is-loading="state.gameStatus === GAME_STATUS.LOADING"
      :error-message="state.assetLoadError"
      @start="startGame"
      @home="goHome"
    />

    <template v-else>
      <article class="glass-panel memory-game-panel">
        <MemoryGameToolbar
          :progress-label="progressLabel"
          :formatted-time="formattedTime"
          :remaining-seconds="remainingSeconds"
          :is-preview="state.gameStatus === GAME_STATUS.PREVIEW"
          @back="goHome"
          @restart="restartGame"
        />
        <MemoryGameBoard
          :cards="state.cards"
          :back-image="cardBackImage"
          @card-click="handleCardClick"
        />
      </article>

      <MemoryGameResultModal
        v-if="isFinished"
        :status="state.gameStatus"
        :matched-pair-count="state.matchedPairCount"
        :formatted-time="formattedTime"
        @retry="restartGame"
        @home="goHome"
      />
    </template>
  </section>
</template>

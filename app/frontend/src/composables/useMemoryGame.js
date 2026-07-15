// useMemoryGame.js
// 캐릭터 카드 짝 맞추기 게임의 상태 머신, 타이머, 덱 생성, 클릭 판정을 담당한다.
// 이 파일은 DB/서버 상태를 다루지 않는다(프론트엔드 전용, 결과 저장 없음).

import { computed, onBeforeUnmount, reactive, readonly } from "vue";
import { getMissingMemoryGameAssets, memoryGameAssets, memoryGameCardBack } from "../data/memoryGameCards.js";

export const GAME_STATUS = Object.freeze({
  IDLE: "IDLE",
  LOADING: "LOADING",
  PREVIEW: "PREVIEW",
  PLAYING: "PLAYING",
  WON: "WON",
  TIMEOUT: "TIMEOUT",
  ERROR: "ERROR",
});

const GAME_DURATION_MS = 90000;
// 게임 시작 전, 전체 카드 위치/그림을 잠깐 보여주는 미리보기 시간.
const PREVIEW_DURATION_MS = 5000;
// 마지막 짝을 맞춘 뒤, 다 맞춰진 보드를 잠깐 보여주고서 결과창을 띄우기까지의 지연.
const WIN_REVEAL_DELAY_MS = 500;
const MISMATCH_DELAY_MS = 700;
// 두 카드가 동시에 딱 맞춰 닫히면 기계적으로 보이므로 살짝 시간차를 둔다.
const MISMATCH_FLIP_STAGGER_MS = 90;
const TICK_INTERVAL_MS = 150;
const UNIQUE_PAIRS_TARGET = 12;
const PICKS_PER_CHARACTER = 3;

// sort(() => Math.random() - 0.5) 대신 정석 Fisher–Yates 셔플을 사용한다.
function fisherYatesShuffle(input) {
  const arr = input.slice();
  for (let i = arr.length - 1; i > 0; i -= 1) {
    const j = Math.floor(Math.random() * (i + 1));
    [arr[i], arr[j]] = [arr[j], arr[i]];
  }
  return arr;
}

function groupByCharacter(assets) {
  const groups = new Map();
  for (const asset of assets) {
    if (!groups.has(asset.character)) groups.set(asset.character, []);
    groups.get(asset.character).push(asset);
  }
  return groups;
}

class AssetShortageError extends Error {
  constructor(character) {
    super(`캐릭터 "${character}"의 사용 가능한 카드 이미지가 ${PICKS_PER_CHARACTER}개 미만입니다.`);
    this.character = character;
  }
}

// 캐릭터별로 셔플 후 3개씩 뽑아 총 12개 고유 자산을 만든다.
function pickRoundAssets(assets) {
  const groups = groupByCharacter(assets);
  const picked = [];

  for (const [character, group] of groups) {
    if (group.length < PICKS_PER_CHARACTER) {
      throw new AssetShortageError(character);
    }
    picked.push(...fisherYatesShuffle(group).slice(0, PICKS_PER_CHARACTER));
  }

  return picked;
}

// 12개 고유 자산을 A/B 인스턴스로 복제해 24장 덱을 만들고 셔플한다.
function buildDeck(uniqueAssets) {
  const instances = uniqueAssets.flatMap((asset) => {
    return ["A", "B"].map((suffix) => ({
      instanceId: `${asset.id}-${suffix}`,
      sourceCardId: asset.id,
      character: asset.character,
      imageUrl: asset.imageUrl,
      alt: asset.alt,
      isFlipped: false,
      isMatched: false,
    }));
  });

  return fisherYatesShuffle(instances);
}

function preloadImage(url) {
  return new Promise((resolve, reject) => {
    if (!url) {
      reject(new Error("empty-url"));
      return;
    }
    const img = new Image();
    img.onload = () => resolve(url);
    img.onerror = () => reject(new Error(`load-failed:${url}`));
    img.src = url;
  });
}

async function preloadAll(urls) {
  const unique = [...new Set(urls.filter(Boolean))];
  const results = await Promise.allSettled(unique.map(preloadImage));
  const failed = results
    .map((result, index) => ({ result, url: unique[index] }))
    .filter(({ result }) => result.status === "rejected")
    .map(({ url }) => url);
  return { ok: failed.length === 0, failed };
}

export function useMemoryGame() {
  const state = reactive({
    gameStatus: GAME_STATUS.IDLE,
    cards: [],
    firstCardId: null,
    secondCardId: null,
    boardLocked: false,
    matchedPairCount: 0,
    remainingMs: GAME_DURATION_MS,
    deadline: 0,
    sessionId: 0,
    assetLoadError: "",
  });

  let countdownTimerId = null;
  let mismatchTimerId = null;
  let mismatchStaggerTimerId = null;
  let previewTimerId = null;
  let winRevealTimerId = null;

  const remainingSeconds = computed(() => Math.ceil(state.remainingMs / 1000));
  const formattedTime = computed(() => {
    const totalSeconds = Math.max(0, remainingSeconds.value);
    const minutes = String(Math.floor(totalSeconds / 60)).padStart(2, "0");
    const seconds = String(totalSeconds % 60).padStart(2, "0");
    return `${minutes}:${seconds}`;
  });
  const progressLabel = computed(() => `찾은 짝 ${state.matchedPairCount} / ${UNIQUE_PAIRS_TARGET}`);
  const isFinished = computed(() => state.gameStatus === GAME_STATUS.WON || state.gameStatus === GAME_STATUS.TIMEOUT);
  const cardBackImage = computed(() => memoryGameCardBack.imageUrl);

  function clearCountdownTimer() {
    if (countdownTimerId !== null) {
      clearInterval(countdownTimerId);
      countdownTimerId = null;
    }
  }

  function clearMismatchTimer() {
    if (mismatchTimerId !== null) {
      clearTimeout(mismatchTimerId);
      mismatchTimerId = null;
    }
    if (mismatchStaggerTimerId !== null) {
      clearTimeout(mismatchStaggerTimerId);
      mismatchStaggerTimerId = null;
    }
  }

  function clearPreviewTimer() {
    if (previewTimerId !== null) {
      clearTimeout(previewTimerId);
      previewTimerId = null;
    }
  }

  function clearWinRevealTimer() {
    if (winRevealTimerId !== null) {
      clearTimeout(winRevealTimerId);
      winRevealTimerId = null;
    }
  }

  function resetSelection() {
    state.firstCardId = null;
    state.secondCardId = null;
  }

  function tickCountdown() {
    const remaining = Math.max(0, state.deadline - Date.now());
    state.remainingMs = remaining;
    if (remaining <= 0) {
      endGame(GAME_STATUS.TIMEOUT);
    }
  }

  function startTimer() {
    clearCountdownTimer();
    state.deadline = Date.now() + GAME_DURATION_MS;
    state.remainingMs = GAME_DURATION_MS;
    countdownTimerId = setInterval(tickCountdown, TICK_INTERVAL_MS);
  }

  function handleVisibilityChange() {
    if (document.visibilityState !== "visible") return;
    if (state.gameStatus !== GAME_STATUS.PLAYING) return;
    const remaining = Math.max(0, state.deadline - Date.now());
    state.remainingMs = remaining;
    if (remaining <= 0) {
      endGame(GAME_STATUS.TIMEOUT);
    }
  }

  document.addEventListener("visibilitychange", handleVisibilityChange);

  async function startGame() {
    if (state.gameStatus === GAME_STATUS.LOADING) return;

    state.sessionId += 1;
    const sessionAtStart = state.sessionId;
    clearCountdownTimer();
    clearMismatchTimer();
    clearPreviewTimer();
    clearWinRevealTimer();
    resetSelection();
    state.boardLocked = false;
    state.matchedPairCount = 0;
    state.assetLoadError = "";
    state.gameStatus = GAME_STATUS.LOADING;

    const missing = getMissingMemoryGameAssets();
    if (missing.length > 0) {
      console.warn("[memory-game] 누락된 카드 이미지:", missing);
    }

    let uniqueAssets;
    try {
      uniqueAssets = pickRoundAssets(memoryGameAssets);
    } catch (error) {
      console.error("[memory-game] 자산 부족:", error?.message);
      if (state.sessionId !== sessionAtStart) return;
      state.gameStatus = GAME_STATUS.ERROR;
      state.assetLoadError = "게임 이미지를 준비하지 못했어요.";
      return;
    }

    const urlsToPreload = [...uniqueAssets.map((asset) => asset.imageUrl), memoryGameCardBack.imageUrl];
    const { ok, failed } = await preloadAll(urlsToPreload);

    // 준비하는 동안 restart 등으로 세션이 바뀌었으면 이 결과는 폐기한다.
    if (state.sessionId !== sessionAtStart) return;

    if (!ok) {
      console.warn("[memory-game] 이미지 로딩 실패:", failed);
      state.gameStatus = GAME_STATUS.ERROR;
      state.assetLoadError = "게임 이미지를 불러오지 못했어요. 다시 시도해 주세요.";
      return;
    }

    state.cards = buildDeck(uniqueAssets);

    // 카드를 나눠주기 전, 전체 배치와 그림을 잠깐 보여준 뒤 뒤집어서 시작한다.
    state.cards.forEach((card) => { card.isFlipped = true; });
    state.boardLocked = true;
    state.gameStatus = GAME_STATUS.PREVIEW;

    previewTimerId = setTimeout(() => {
      previewTimerId = null;
      if (state.sessionId !== sessionAtStart) return;

      state.cards.forEach((card) => { card.isFlipped = false; });
      state.boardLocked = false;
      state.gameStatus = GAME_STATUS.PLAYING;
      startTimer();
    }, PREVIEW_DURATION_MS);
  }

  function restartGame() {
    startGame();
  }

  function findCard(instanceId) {
    return state.cards.find((card) => card.instanceId === instanceId) || null;
  }

  function handleCardClick(instanceId) {
    if (state.gameStatus !== GAME_STATUS.PLAYING) return;
    if (state.boardLocked) return;
    if (state.remainingMs <= 0) return;

    const card = findCard(instanceId);
    if (!card) return;
    if (card.isMatched) return;
    if (card.isFlipped) return;

    if (state.firstCardId === null) {
      card.isFlipped = true;
      state.firstCardId = instanceId;
      return;
    }

    if (state.secondCardId !== null) return;

    card.isFlipped = true;
    state.secondCardId = instanceId;
    state.boardLocked = true;
    compareCards();
  }

  function compareCards() {
    const first = findCard(state.firstCardId);
    const second = findCard(state.secondCardId);
    if (!first || !second) {
      state.boardLocked = false;
      resetSelection();
      return;
    }

    if (first.sourceCardId === second.sourceCardId) {
      first.isMatched = true;
      second.isMatched = true;
      state.matchedPairCount += 1;
      resetSelection();
      state.boardLocked = false;

      // 마지막 짝과 시간 종료가 겹치는 경계 상황을 안전하게 처리한다.
      if (state.matchedPairCount >= UNIQUE_PAIRS_TARGET && state.remainingMs > 0) {
        // 결과창을 바로 띄우지 않고, 다 맞춰진 보드를 잠깐 보여준 뒤 결과창을 띄운다.
        clearCountdownTimer();
        state.boardLocked = true;
        const sessionAtWin = state.sessionId;
        clearWinRevealTimer();
        winRevealTimerId = setTimeout(() => {
          winRevealTimerId = null;
          if (state.sessionId !== sessionAtWin) return;
          endGame(GAME_STATUS.WON);
        }, WIN_REVEAL_DELAY_MS);
      }
      return;
    }

    const sessionAtSelection = state.sessionId;
    clearMismatchTimer();
    mismatchTimerId = setTimeout(() => {
      mismatchTimerId = null;
      if (state.sessionId !== sessionAtSelection) return;
      if (state.gameStatus !== GAME_STATUS.PLAYING) return;

      // 두 카드를 동시에 닫지 않고 살짝 시간차를 둬서 자연스럽게 보이게 한다.
      const staleFirst = findCard(first.instanceId);
      if (staleFirst) staleFirst.isFlipped = false;

      mismatchStaggerTimerId = setTimeout(() => {
        mismatchStaggerTimerId = null;
        if (state.sessionId !== sessionAtSelection) return;

        const staleSecond = findCard(second.instanceId);
        if (staleSecond) staleSecond.isFlipped = false;
        resetSelection();
        state.boardLocked = false;
      }, MISMATCH_FLIP_STAGGER_MS);
    }, MISMATCH_DELAY_MS);
  }

  function endGame(result) {
    if (state.gameStatus !== GAME_STATUS.PLAYING) return;

    state.boardLocked = true;
    clearCountdownTimer();
    clearMismatchTimer();
    resetSelection();

    if (result === GAME_STATUS.WON) {
      state.gameStatus = GAME_STATUS.WON;
      return;
    }

    state.remainingMs = 0;
    state.gameStatus = GAME_STATUS.TIMEOUT;
  }

  function goToIdle() {
    clearCountdownTimer();
    clearMismatchTimer();
    clearPreviewTimer();
    clearWinRevealTimer();
    resetSelection();
    state.gameStatus = GAME_STATUS.IDLE;
  }

  onBeforeUnmount(() => {
    clearCountdownTimer();
    clearMismatchTimer();
    clearPreviewTimer();
    clearWinRevealTimer();
    document.removeEventListener("visibilitychange", handleVisibilityChange);
  });

  return {
    state: readonly(state),
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
  };
}

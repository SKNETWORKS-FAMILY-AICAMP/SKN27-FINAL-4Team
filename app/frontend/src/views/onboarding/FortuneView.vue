<script setup>
import { computed, ref, watch } from "vue";
import { useRoute } from "vue-router";
import { tarotApi } from "../../api/tarot.js";
import tarotCsv from "../../assets/data/tarot_card_meanings.csv?raw";
import { getTarotCardImage } from "../../assets/tarot/cardImages.js";
import tarotCardBackImage from "../../assets/tarot/tarot-card-back.png";
import searchBirdImage from "../../assets/characters/search-bird.png";
import searchCatImage from "../../assets/characters/search-cat.png";
import searchOtterImage from "../../assets/characters/search-otter.png";
import searchRedPandaImage from "../../assets/characters/search-red-panda.png";

const emit = defineEmits(["navigate"]);
const route = useRoute();

const MAX_SELECTED_CARDS = 3;
const QUESTION_MAX_LENGTH = 200;
const GATHER_DURATION = 1040;
const HINDU_PACKET_DURATION = 520;
const HINDU_PACKET_GAP = 28;
const DEAL_DURATION = 1480;
const MIN_READING_LOADING_DURATION = 1900;
const HINDU_PACKETS = [
  { start: 1, end: 4 },
  { start: 5, end: 7 },
  { start: 8, end: 11 },
  { start: 12, end: 15 },
  { start: 16, end: 20 },
];
const searchCharacterImages = {
  bird: searchBirdImage,
  cat: searchCatImage,
  otter: searchOtterImage,
  redpanda: searchRedPandaImage,
};
const searchCharacterLabels = {
  bird: "뱁새",
  cat: "고양이",
  otter: "수달",
  redpanda: "레서판다",
};

const categories = [
  { id: "relationship", apiId: "relationship", label: "연애", resultLabel: "연애운" },
  { id: "work", apiId: "work", label: "업무·학업", resultLabel: "업무·학업운" },
  { id: "money", apiId: "money", label: "금전", resultLabel: "금전운" },
  { id: "success", apiId: "general", label: "성공", resultLabel: "성공운" },
  { id: "general", apiId: "general", label: "총운", resultLabel: "총운" },
];

const cardRoles = ["오늘의 흐름", "핵심 신호", "조언"];
const tarotDeck = parseTarotCsv(tarotCsv);
const selectedCategory = ref(getInitialCategory());
const cardSlots = ref(createCardSlots());
const selectedSlotIds = ref([]);
const question = ref("");
const readingResult = ref(null);
const readingError = ref("");
const isReadingLoading = ref(false);
const isResultStreaming = ref(false);
const streamedCategoryResult = ref("");
const streamedCardReadings = ref([]);
const streamingTarget = ref(null);
const streamRunId = ref(0);
const isShuffling = ref(false);
const shufflePhase = ref("idle");
const activeHinduPacket = ref(-1);
const droppedHinduPackets = ref([]);
const pickedSlotId = ref("");
const shuffleRunId = ref(0);

const selectedCategoryData = computed(() => categories.find((category) => category.id === selectedCategory.value) || categories[0]);
const selectedSlots = computed(() => selectedSlotIds.value
  .map((slotId, index) => {
    const slot = cardSlots.value.find((item) => item.id === slotId);
    return slot ? { ...slot, position: index + 1, role: cardRoles[index] } : null;
  })
  .filter(Boolean));
const selectedCount = computed(() => selectedSlots.value.length);
const canAnalyze = computed(() => (
  selectedCount.value === MAX_SELECTED_CARDS &&
  !isReadingLoading.value &&
  !isResultStreaming.value
));
const selectedCategoryResult = computed(() => {
  const categoryResults = readingResult.value?.category_results;
  const apiId = selectedCategoryData.value.apiId;
  return categoryResults?.[apiId] || readingResult.value?.summary || "";
});
const displayedCategoryResult = computed(() => {
  if (!readingResult.value) return "";
  if (isResultStreaming.value || streamedCategoryResult.value) return streamedCategoryResult.value;
  return selectedCategoryResult.value;
});
const selectedSearchCharacter = computed(() => getSelectedSearchCharacter());
const selectedSearchCharacterImage = computed(() => searchCharacterImages[selectedSearchCharacter.value] || searchCharacterImages.bird);
const selectedSearchCharacterLabel = computed(() => searchCharacterLabels[selectedSearchCharacter.value] || searchCharacterLabels.bird);
const transparentSearchCharacterImage = ref("");

watch(
  selectedSearchCharacterImage,
  async (characterImage) => {
    transparentSearchCharacterImage.value = characterImage;

    const cutoutImage = await createTransparentCharacterImage(characterImage);
    if (selectedSearchCharacterImage.value === characterImage) {
      transparentSearchCharacterImage.value = cutoutImage || characterImage;
    }
  },
  { immediate: true },
);

function createTransparentCharacterImage(src) {
  return new Promise((resolve) => {
    if (typeof window === "undefined" || !src) {
      resolve(src);
      return;
    }

    const image = new Image();
    image.crossOrigin = "anonymous";

    image.onload = () => {
      try {
        const width = image.naturalWidth || image.width;
        const height = image.naturalHeight || image.height;

        if (!width || !height) {
          resolve(src);
          return;
        }

        const canvas = document.createElement("canvas");
        const context = canvas.getContext("2d", { willReadFrequently: true });

        if (!context) {
          resolve(src);
          return;
        }

        canvas.width = width;
        canvas.height = height;
        context.drawImage(image, 0, 0, width, height);

        const imageData = context.getImageData(0, 0, width, height);
        const { data } = imageData;
        const visited = new Uint8Array(width * height);
        const queue = [];

        const getPixelOffset = (x, y) => (y * width + x) * 4;
        const isEdgeBackgroundPixel = (x, y) => {
          const offset = getPixelOffset(x, y);
          const alpha = data[offset + 3];
          const red = data[offset];
          const green = data[offset + 1];
          const blue = data[offset + 2];

          if (alpha <= 16) return true;

          const brightness = (red + green + blue) / 3;
          const maxDifference = Math.max(
            Math.abs(red - green),
            Math.abs(red - blue),
            Math.abs(green - blue),
          );

          return brightness >= 235 && maxDifference <= 22;
        };

        const enqueue = (x, y) => {
          if (x < 0 || x >= width || y < 0 || y >= height) return;

          const index = y * width + x;
          if (visited[index] || !isEdgeBackgroundPixel(x, y)) return;

          visited[index] = 1;
          queue.push([x, y]);
        };

        for (let x = 0; x < width; x += 1) {
          enqueue(x, 0);
          enqueue(x, height - 1);
        }

        for (let y = 0; y < height; y += 1) {
          enqueue(0, y);
          enqueue(width - 1, y);
        }

        while (queue.length) {
          const [x, y] = queue.shift();
          const offset = getPixelOffset(x, y);
          data[offset + 3] = 0;

          enqueue(x + 1, y);
          enqueue(x - 1, y);
          enqueue(x, y + 1);
          enqueue(x, y - 1);
        }

        context.putImageData(imageData, 0, 0);
        resolve(canvas.toDataURL("image/png"));
      } catch {
        resolve(src);
      }
    };

    image.onerror = () => resolve(src);
    image.src = src;
  });
}

function getInitialCategory() {
  const queryCategory = String(route.query.category || "");
  if (categories.some((category) => category.id === queryCategory)) return queryCategory;
  if (queryCategory === "love") return "relationship";
  if (queryCategory === "career" || queryCategory === "study") return "work";
  return "general";
}

function getSelectedSearchCharacter() {
  try {
    const stored = JSON.parse(localStorage.getItem("binteumsaiCharacter") || "{}");
    return normalizeSearchCharacterId(route.query.character || stored.characterId);
  } catch {
    return "bird";
  }
}

function normalizeSearchCharacterId(id) {
  const value = String(id || "").trim().toLowerCase().replace(/_/g, "-");

  if (value === "redpanda" || value === "red-panda" || value === "dalkong") return "redpanda";
  if (value === "haeon") return "otter";
  if (value === "greung" || value === "geureung") return "cat";
  if (["bird", "cat", "otter"].includes(value)) return value;
  return "bird";
}

function selectCategory(categoryId) {
  if (selectedCategory.value === categoryId || isReadingLoading.value) return;
  selectedCategory.value = categoryId;
  shuffleCards();
}

function selectCard(slot) {
  if (isShuffling.value) return;
  if (selectedSlotIds.value.includes(slot.id) || selectedSlotIds.value.length >= MAX_SELECTED_CARDS) return;

  selectedSlotIds.value = [...selectedSlotIds.value, slot.id];
  pickedSlotId.value = slot.id;

  window.setTimeout(() => {
    if (pickedSlotId.value === slot.id) pickedSlotId.value = "";
  }, 420);

  clearReading();
}

function removeSelectedCard(slotId) {
  selectedSlotIds.value = selectedSlotIds.value.filter((id) => id !== slotId);
  if (pickedSlotId.value === slotId) pickedSlotId.value = "";
  clearReading();
}

function resetCards() {
  shuffleCards();
}

async function shuffleCards() {
  selectedSlotIds.value = [];
  pickedSlotId.value = "";
  readingResult.value = null;
  readingError.value = "";
  resetReadingStream();

  shuffleRunId.value += 1;
  const runId = shuffleRunId.value;
  isShuffling.value = true;
  activeHinduPacket.value = -1;
  droppedHinduPackets.value = [];

  shufflePhase.value = "gather";
  await wait(GATHER_DURATION);
  if (runId !== shuffleRunId.value) return;

  shufflePhase.value = "hindu";
  for (let packetIndex = 0; packetIndex < HINDU_PACKETS.length; packetIndex += 1) {
    activeHinduPacket.value = packetIndex;
    await wait(HINDU_PACKET_DURATION);
    if (runId !== shuffleRunId.value) return;

    droppedHinduPackets.value = [...droppedHinduPackets.value, packetIndex];
    activeHinduPacket.value = -1;
    await wait(HINDU_PACKET_GAP);
    if (runId !== shuffleRunId.value) return;
  }

  applyShuffledDeckToSlots();
  shufflePhase.value = "deal";
  await wait(DEAL_DURATION);
  if (runId !== shuffleRunId.value) return;

  shufflePhase.value = "idle";
  activeHinduPacket.value = -1;
  droppedHinduPackets.value = [];
  isShuffling.value = false;
}

function wait(duration) {
  return new Promise((resolve) => {
    window.setTimeout(resolve, duration);
  });
}

function resetReadingStream() {
  streamRunId.value += 1;
  isResultStreaming.value = false;
  streamedCategoryResult.value = "";
  streamedCardReadings.value = [];
  streamingTarget.value = null;
}

function setStreamedCardReading(index, value) {
  const nextReadings = [...streamedCardReadings.value];
  nextReadings[index] = value;
  streamedCardReadings.value = nextReadings;
}

async function streamText(fullText, update, runId, delay = 16) {
  const text = String(fullText || "");

  for (let index = 0; index <= text.length; index += 1) {
    if (runId !== streamRunId.value) return;
    update(text.slice(0, index));
    await wait(delay);
  }
}

async function streamReadingResult(result) {
  const runId = streamRunId.value + 1;
  streamRunId.value = runId;
  isResultStreaming.value = true;
  streamedCategoryResult.value = "";
  streamedCardReadings.value = selectedSlots.value.map(() => "");
  streamingTarget.value = "category";

  const categoryResults = result?.category_results;
  const apiId = selectedCategoryData.value.apiId;
  const summary = categoryResults?.[apiId] || result?.summary || "";

  await streamText(
    summary,
    (value) => {
      streamedCategoryResult.value = value;
    },
    runId,
    16,
  );

  const cardTexts = selectedSlots.value.map((slot, index) => (
    result?.card_readings?.[index]?.interpretation || slot.card.uprightMeaning
  ));

  for (const [index, text] of cardTexts.entries()) {
    if (runId !== streamRunId.value) return;

    streamingTarget.value = index;
    await streamText(
      text,
      (value) => {
        setStreamedCardReading(index, value);
      },
      runId,
      12,
    );
  }

  if (runId === streamRunId.value) {
    isResultStreaming.value = false;
    streamingTarget.value = null;
  }
}

function getDisplayedCardReading(slot, index) {
  const streamedText = streamedCardReadings.value[index];

  if (isResultStreaming.value || streamedText) {
    return streamedText || "";
  }

  return readingResult.value?.card_readings?.[index]?.interpretation || slot.card.uprightMeaning;
}

function applyShuffledDeckToSlots() {
  const nextSlots = createCardSlots();
  cardSlots.value = cardSlots.value.map((slot, index) => ({
    ...nextSlots[index],
    id: slot.id,
    index: slot.index,
  }));
}

function getCardStyle(slot) {
  const row = Math.floor((slot.index - 1) / 10);
  const column = (slot.index - 1) % 10;
  const packet = getHinduPacketIndex(slot);
  const packetOffset = packet >= 0 ? slot.index - HINDU_PACKETS[packet].start : 0;
  const direction = packet % 2 === 0 ? 1 : -1;
  const idleRotate = (column - 4.5) * 0.8 + row * 0.7;
  const stackRotate = ((slot.index % 7) - 3) * 0.9;
  const liftX = direction * (18 + packet * 4) + packetOffset * 2.4;
  const dropX = direction * -10 + packetOffset * 1.2;
  const shuffleX = direction * (12 + packet * 2.2) + packetOffset * 1.8;
  const shuffleY = -8 - (packetOffset % 3) * 3;
  const shuffleBackX = direction * (-7 - packetOffset * 0.8);
  const shuffleBackY = 9 + packet * 1.8;
  const shuffleRotate = direction * (2.2 + packetOffset * 0.55);
  const shuffleBackRotate = direction * (-1.5 - packetOffset * 0.35);

  return {
    "--card-col": column,
    "--card-row": row,
    "--idle-rotate": `${idleRotate}deg`,
    "--stack-rotate": `${stackRotate}deg`,
    "--gather-delay": `${(20 - slot.index) * 12}ms`,
    "--deal-delay": `${(slot.index - 1) * 22}ms`,
    "--hindu-x": `${liftX}px`,
    "--hindu-y": `${-22 - packetOffset * 2}px`,
    "--hindu-rotate": `${direction * (3.2 + packetOffset * 0.7)}deg`,
    "--drop-x": `${dropX}px`,
    "--drop-y": `${16 + packet * 2.5}px`,
    "--drop-rotate": `${direction * -1.5}deg`,
    "--shuffle-delay": `${slot.index * -42}ms`,
    "--shuffle-x": `${shuffleX}px`,
    "--shuffle-y": `${shuffleY}px`,
    "--shuffle-rotate": `${shuffleRotate}deg`,
    "--shuffle-back-x": `${shuffleBackX}px`,
    "--shuffle-back-y": `${shuffleBackY}px`,
    "--shuffle-back-rotate": `${shuffleBackRotate}deg`,
    "--card-z": getCardZ(slot),
  };
}

function getHinduPacketIndex(slot) {
  return HINDU_PACKETS.findIndex((packet) => slot.index >= packet.start && slot.index <= packet.end);
}

function isActiveHinduPacket(slot) {
  return shufflePhase.value === "hindu" && getHinduPacketIndex(slot) === activeHinduPacket.value;
}

function isDroppedHinduPacket(slot) {
  const packetIndex = getHinduPacketIndex(slot);
  return shufflePhase.value === "hindu" && packetIndex >= 0 && droppedHinduPackets.value.includes(packetIndex);
}

function getCardZ(slot) {
  const packetIndex = getHinduPacketIndex(slot);

  if (shufflePhase.value === "hindu") {
    if (packetIndex === activeHinduPacket.value) return 90 + slot.index;
    if (packetIndex >= 0 && droppedHinduPackets.value.includes(packetIndex)) return 10 - packetIndex;
    return 48 - slot.index;
  }

  if (shufflePhase.value === "gather") return 20 + slot.index;
  if (shufflePhase.value === "deal") return 20 + slot.index;
  return 20 + slot.index;
}

async function requestTarotReading() {
  if (!canAnalyze.value) return;

  isReadingLoading.value = true;
  readingError.value = "";
  readingResult.value = null;
  resetReadingStream();
  const loadingStartedAt = Date.now();
  let nextReadingResult = null;

  try {
    const payload = {
      topic: selectedCategoryData.value.apiId,
      question: question.value.trim(),
      cards: selectedSlots.value.map((slot) => ({
        card_number: slot.card.cardNumber,
        orientation: slot.orientation,
      })),
    };
    nextReadingResult = await tarotApi.createReading(payload);
    readingResult.value = nextReadingResult;
  } catch (error) {
    readingError.value = error?.response?.data?.error || "카드 결과를 불러오지 못했어요. 잠시 후 다시 시도해 주세요.";
  } finally {
    const elapsed = Date.now() - loadingStartedAt;
    const remainingDelay = Math.max(0, MIN_READING_LOADING_DURATION - elapsed);
    if (remainingDelay) await wait(remainingDelay);
    isReadingLoading.value = false;
  }

  if (nextReadingResult) {
    await streamReadingResult(nextReadingResult);
  }
}

function clearReading() {
  readingResult.value = null;
  readingError.value = "";
  resetReadingStream();
}

function isSlotSelected(slotId) {
  return selectedSlotIds.value.includes(slotId);
}

function createCardSlots() {
  const source = tarotDeck.length ? tarotDeck : createFallbackDeck();
  const shuffled = hinduShuffleDeck(source).slice(0, 20);

  return shuffled.map((card, index) => ({
    id: `${card.cardNumber}-${index}-${Math.random().toString(36).slice(2, 7)}`,
    index: index + 1,
    card,
    orientation: Math.random() > 0.22 ? "upright" : "reversed",
  }));
}

function hinduShuffleDeck(cards) {
  let deck = [...cards];

  for (let round = 0; round < 4; round += 1) {
    const remaining = [...deck];
    let shuffled = [];

    while (remaining.length) {
      const packetSize = Math.min(remaining.length, 2 + Math.floor(Math.random() * 6));
      const packet = remaining.splice(0, packetSize);
      shuffled = [...packet, ...shuffled];
    }

    const cutPoint = Math.floor(Math.random() * shuffled.length);
    deck = [...shuffled.slice(cutPoint), ...shuffled.slice(0, cutPoint)];
  }

  return deck;
}

function parseTarotCsv(csv) {
  const lines = csv.replace(/^\uFEFF/, "").split(/\r?\n/).filter(Boolean);
  const headers = parseCsvLine(lines.shift() || "");

  return lines.map((line) => {
    const values = parseCsvLine(line);
    const raw = Object.fromEntries(headers.map((header, index) => [header, values[index] || ""]));
    const cardNumber = Number(raw.card_number || raw.cardNumber || raw.id || 0);

    return {
      cardNumber,
      englishName: raw.card_name || raw.english_name || raw.name || `Card ${cardNumber}`,
      koreanName: raw.card_name_ko || raw.korean_name || translateCardName(raw.card_name || raw.name || ""),
      uprightMeaning: raw.upright_meaning || raw.upright || raw.keywords || "차분히 흐름을 살펴보라는 신호",
      reversedMeaning: raw.reversed_meaning || raw.reversed || "조급함을 내려놓으라는 신호",
    };
  }).filter((card) => Number.isFinite(card.cardNumber));
}

function parseCsvLine(line) {
  const result = [];
  let current = "";
  let inQuotes = false;

  for (let index = 0; index < line.length; index += 1) {
    const char = line[index];
    const next = line[index + 1];

    if (char === '"' && next === '"') {
      current += '"';
      index += 1;
      continue;
    }

    if (char === '"') {
      inQuotes = !inQuotes;
      continue;
    }

    if (char === "," && !inQuotes) {
      result.push(current);
      current = "";
      continue;
    }

    current += char;
  }

  result.push(current);
  return result.map((value) => value.trim());
}

function createFallbackDeck() {
  return Array.from({ length: 22 }, (_, index) => ({
    cardNumber: index,
    englishName: `Major Arcana ${index}`,
    koreanName: `카드 ${index}`,
    uprightMeaning: "새로운 흐름을 바라보는 카드",
    reversedMeaning: "멈춤 속에서 방향을 찾는 카드",
  }));
}

function translateCardName(name) {
  const map = {
    "The Fool": "바보",
    "The Magician": "마법사",
    "The High Priestess": "여사제",
    "The Empress": "여황제",
    "The Emperor": "황제",
    "The Hierophant": "교황",
    "The Lovers": "연인",
    "The Chariot": "전차",
    Strength: "힘",
    "The Hermit": "은둔자",
    "Wheel of Fortune": "운명의 수레바퀴",
    Justice: "정의",
    "The Hanged Man": "행맨",
    Death: "죽음",
    Temperance: "절제",
    "The Devil": "악마",
    "The Tower": "탑",
    "The Star": "별",
    "The Moon": "달",
    "The Sun": "태양",
    Judgement: "심판",
    "The World": "세계",
  };
  if (map[name]) return map[name];

  const rankNames = {
    Ace: "에이스",
    Two: "2",
    Three: "3",
    Four: "4",
    Five: "5",
    Six: "6",
    Seven: "7",
    Eight: "8",
    Nine: "9",
    Ten: "10",
    Page: "페이지",
    Knight: "기사",
    Queen: "여왕",
    King: "왕",
  };
  const suitNames = {
    Wands: "완드",
    Cups: "컵",
    Swords: "소드",
    Pentacles: "펜타클",
  };

  const minorMatch = String(name || "").match(/^(.+?) of (Wands|Cups|Swords|Pentacles)$/);
  if (minorMatch) {
    const [, rank, suit] = minorMatch;
    return `${suitNames[suit]} ${rankNames[rank] || rank}`;
  }

  return name || "타로 카드";
}
</script>

<template>
  <section class="view-card tarot-draw-page">
    <div class="tarot-draw-layout">
      <article class="glass-panel tarot-main-panel">
        <header class="tarot-draw-header">
          <button class="back-button" type="button" @click="emit('navigate', 'fortune')">‹</button>
          <div class="text-area">
            <p>상황별 카드 운세</p>
            <h2>직감이 이끄는 카드 3장을 선택해 주세요</h2>
          </div>
        </header>


        <section class="category-section">
          <div class="category-chip-row">
            <button
              v-for="category in categories"
              :key="category.id"
              type="button"
              :class="{ active: selectedCategory === category.id }"
              @click="selectCategory(category.id)"
            >
              {{ category.label }}
            </button>
          </div>
        </section>

        <section class="card-spread-section">
          <div class="section-title-row">
            <strong>선택 {{ selectedCount }} / {{ MAX_SELECTED_CARDS }}</strong>
          </div>

          <div class="tarot-spread-panel" :class="[`shuffle-${shufflePhase}`, { shuffling: isShuffling }]">
            <button
              v-for="slot in cardSlots"
              :key="slot.id"
              type="button"
              class="tarot-back-card"
              :class="{
                selected: isSlotSelected(slot.id),
                disabled: selectedCount >= MAX_SELECTED_CARDS && !isSlotSelected(slot.id),
                'packet-active': isActiveHinduPacket(slot),
                'packet-dropped': isDroppedHinduPacket(slot),
                'just-picked': pickedSlotId === slot.id,
              }"
              :style="getCardStyle(slot)"
              :disabled="isShuffling || isSlotSelected(slot.id) || selectedCount >= MAX_SELECTED_CARDS"
              :aria-label="`타로 카드 선택`"
              @click="selectCard(slot)"
            >
              <img :src="tarotCardBackImage" alt="">
            </button>
          </div>
        </section>

        <section class="selected-card-zone">
          <aside class="pick-guide">
            <span>☝</span>
            <strong>직감이 이끄는 <br>카드를 선택해 보세요</strong>
            <p>마음이 이끄는 카드가 지금 당신에게 필요한 이야기를 들려줄 거예요.</p>
          </aside>

          <div class="selected-slots" aria-label="선택 카드 슬롯">
            <article v-for="position in MAX_SELECTED_CARDS" :key="position" class="selected-slot">
              <span>{{ position }}</span>
              <button
                v-if="selectedSlots[position - 1]"
                type="button"
                class="selected-card-preview"
                @click="removeSelectedCard(selectedSlots[position - 1].id)"
              >
                <img
                  v-if="getTarotCardImage(selectedSlots[position - 1].card.cardNumber)"
                  :src="getTarotCardImage(selectedSlots[position - 1].card.cardNumber)"
                  :alt="`${selectedSlots[position - 1].card.koreanName} 카드`"
                  :class="{ reversed: selectedSlots[position - 1].orientation === 'reversed' }"
                >
                <strong v-else>{{ selectedSlots[position - 1].card.koreanName }}</strong>
              </button>
              <div v-else class="empty-slot"></div>
            </article>
          </div>
        </section>
      </article>

      <aside class="glass-panel tarot-result-panel side-panel">
        <header>
          <span>♠️</span>
          <h3>오늘의 타로 결과</h3>
        </header>

        <section class="result-block">
          <h4>선택한 카테고리</h4>
          <p class="category-pill">{{ selectedCategoryData.resultLabel }}</p>
        </section>

        <section v-if="selectedSlots.length" class="selected-result-cards">
          <article v-for="slot in selectedSlots" :key="slot.id">
            <span>{{ slot.position }}</span>
            <strong>{{ slot.card.koreanName }}</strong>
            <small>{{ slot.orientation === "reversed" ? "역방향" : "정방향" }}</small>
          </article>
        </section>

        <section class="question-box">
          <label for="tarot-question">궁금한 내용을 입력해 주세요</label>
          <textarea
            id="tarot-question"
            v-model="question"
            :maxlength="QUESTION_MAX_LENGTH"
            placeholder="예) 최근 고민, 궁금한 질문, 상황 등을 자유롭게 적어보세요."
          ></textarea>
          <small>{{ question.length }} / {{ QUESTION_MAX_LENGTH }}</small>
        </section>

        <button
          class="btn primary full analyze-button"
          type="button"
          :disabled="!canAnalyze"
          @click="requestTarotReading"
        >
          {{
            isReadingLoading
              ? "선택한 카드 분석 중..."
              : isResultStreaming
                ? "결과를 작성하는 중..."
                : "선택한 카드 분석하기"
          }}
        </button>

        <p v-if="selectedCount < MAX_SELECTED_CARDS && !readingResult" class="result-help">카드 3장을 선택해야 분석할 수 있어요.</p>
        <p v-if="readingError" class="reading-error">{{ readingError }}</p>

        <section v-if="readingResult" class="reading-result-card">
          <h4>{{ selectedCategoryData.resultLabel }} 결과</h4>
          <p class="streaming-text" :class="{ streaming: isResultStreaming && streamingTarget === 'category' }">{{ displayedCategoryResult }}</p>

          <div class="card-reading-list">
            <article v-for="(slot, index) in selectedSlots" :key="`reading-${slot.id}`">
              <strong>{{ cardRoles[index] }} · {{ slot.card.koreanName }}</strong>
              <p class="streaming-text" :class="{ streaming: isResultStreaming && streamingTarget === index }">{{ getDisplayedCardReading(slot, index) }}</p>
            </article>
          </div>
        </section>

        <div class="result-actions">
          <button type="button" :disabled="isShuffling" @click="resetCards">
            {{ isShuffling ? "카드 섞는 중" : "새 카드 섞기" }}
          </button>
          <button type="button" @click="emit('navigate', 'home')">홈으로 돌아가기</button>
        </div>
      </aside>
    </div>

    <div
      v-if="isReadingLoading"
      class="reading-loading-backdrop"
      role="dialog"
      aria-modal="true"
      aria-labelledby="reading-loading-title"
      aria-describedby="reading-loading-desc"
    >
      <div class="reading-loading-modal" aria-live="polite">
        <div class="loading-orbit" aria-hidden="true">
          <span></span>
          <span></span>
          <span></span>
        </div>
        <img
          class="reading-loading-character"
          :src="transparentSearchCharacterImage || selectedSearchCharacterImage"
          :alt="`${selectedSearchCharacterLabel} 캐릭터가 카드 분석을 검색하는 모습`"
        >
        <strong id="reading-loading-title">카드 분석을 검색 중이에요</strong>
        <p id="reading-loading-desc">선택한 카드와 질문의 흐름을 차분히 살펴보고 있어요.</p>
        <div class="reading-loading-dots" aria-hidden="true">
          <span></span>
          <span></span>
          <span></span>
        </div>
      </div>
    </div>

    <footer class="tarot-bottom-note glass-panel">
      <img src="/characters/bird/hurt.png" alt="" aria-hidden="true">
      <span>당신의 마음은 이미 답을 알고 있어요. 카드는 그 답을 찾아가는 작은 빛이 되어줄 거예요. ✦</span>
    </footer>
  </section>
</template>

<style scoped>
.tarot-draw-page {
  min-height: calc(100dvh - var(--bt-header-h));
  padding: 24px 32px 40px;
  word-break: keep-all;
  overflow-wrap: break-word;
}

.tarot-draw-layout {
  width: min(100%, 1440px);
  display: grid;
  grid-template-columns: minmax(0, 1fr) minmax(380px, 430px);
  gap: 24px;
  align-items: start;
  margin: 0 auto;
}

.tarot-main-panel,
.tarot-result-panel,
.tarot-bottom-note {
  border-radius: 32px;
  background:
    linear-gradient(145deg, rgba(45, 13, 63, 0.82), rgba(20, 8, 36, 0.9)),
    rgba(45, 13, 63, 0.74);
}

.tarot-main-panel {
  min-width: 0;
  display: grid;
  gap: 18px;
  padding: clamp(24px, 2.8vw, 34px);
}

.tarot-draw-header {
  display: grid;
  grid-template-columns: 42px minmax(0, 1fr);
  gap: 14px;
  align-items: start;
}

.back-button {
  width: 38px;
  height: 38px;
  border: 1px solid rgba(255, 116, 180, 0.24);
  border-radius: 50%;
  background: rgba(255, 255, 255, 0.06);
  color: #fff7df;
  font-size: 28px;
  line-height: 1;
  cursor: pointer;
}

.tarot-draw-header p {
  margin: 0 0 6px;
  color: #ffd37a;
  font-size: 15px;
  font-weight: 950;
}

.tarot-draw-header h2 {
  margin: 0;
  color: #fff7df;
  font-size: clamp(28px, 2.7vw, 44px);
  line-height: 1.18;
  letter-spacing: -0.02em;
}

.tarot-steps {
  display: grid;
  grid-template-columns: minmax(0, 1fr) 56px minmax(0, 1fr) 56px minmax(0, 1fr);
  gap: 8px;
  align-items: center;
  padding: 14px;
  border: 1px solid rgba(255, 116, 180, 0.16);
  border-radius: 20px;
  background: rgba(255, 255, 255, 0.035);
}

.tarot-steps span {
  min-width: 0;
  min-height: 42px;
  display: grid;
  place-items: center;
  border: 1px solid rgba(255, 116, 180, 0.18);
  border-radius: 999px;
  color: rgba(255, 245, 230, 0.64);
  font-weight: 900;
  text-align: center;
}

.tarot-steps span.active,
.tarot-steps span.done {
  color: #fff;
  border-color: transparent;
  background: linear-gradient(90deg, #f84f9b 0%, #ff8a57 100%);
}

.tarot-steps i {
  height: 1px;
  background: rgba(255, 116, 180, 0.32);
}

.category-section,
.card-spread-section,
.selected-card-zone {
  display: grid;
  gap: 12px;
}

.category-section h3,
.section-title-row h3 {
  margin: 0;
  color: #fff7df;
  font-size: clamp(20px, 1.6vw, 26px);
  line-height: 1.25;
}

.category-chip-row {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
}

.category-chip-row button {
  min-height: 42px;
  padding: 0 18px;
  border: 1px solid rgba(255, 116, 180, 0.26);
  border-radius: 999px;
  background: rgba(255, 255, 255, 0.055);
  color: rgba(255, 245, 230, 0.8);
  font-weight: 900;
  white-space: nowrap;
  cursor: pointer;
}

.category-chip-row button.active {
  color: #fff;
  border-color: transparent;
  background: linear-gradient(90deg, #f84f9b 0%, #ff8a57 100%);
}

.section-title-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 14px;
}

.section-title-row strong {
  color: #fff7df;
  white-space: nowrap;
}

.tarot-spread-panel {
  --card-width: 70px;
  --card-height: 104px;
  position: relative;
  min-height: 258px;
  padding: 22px;
  border: 1px solid rgba(255, 116, 180, 0.18);
  border-radius: 22px;
  background:
    radial-gradient(circle at 50% 50%, rgba(255, 211, 122, 0.12), transparent 55%),
    rgba(255, 255, 255, 0.045);
  overflow: hidden;
}

.tarot-back-card {
  position: absolute;
  top: calc(24px + (var(--card-row) * 122px));
  left: calc(7% + (var(--card-col) * 9.55%));
  z-index: var(--card-z);
  width: var(--card-width);
  height: var(--card-height);
  display: grid;
  place-items: center;
  border: 0;
  background: transparent;
  cursor: pointer;
  transform: translate(-50%, 0) rotate(var(--idle-rotate));
  transform-origin: center center;
  transition:
    top 0.92s cubic-bezier(0.2, 0.78, 0.24, 1),
    left 0.92s cubic-bezier(0.2, 0.78, 0.24, 1),
    transform 0.92s cubic-bezier(0.2, 0.78, 0.24, 1),
    opacity 0.28s ease,
    filter 0.28s ease;
  transition-delay: var(--move-delay, 0ms);
  will-change: top, left, transform, filter;
  backface-visibility: hidden;
  transform-style: preserve-3d;
}

.tarot-back-card:hover:not(:disabled) {
  transform: translate(-50%, -8px) rotate(var(--idle-rotate)) scale(1.03);
}

.tarot-back-card.selected {
  transform: translate(-50%, -10px) rotate(var(--idle-rotate)) scale(1.065);
  filter: brightness(1.15) saturate(1.12);
}

.tarot-back-card.selected img {
  outline: 3px solid rgba(255, 244, 219, 0.92);
  border: 2px solid rgba(255, 96, 160, 0.95);
  box-shadow:
    0 0 0 5px rgba(248, 79, 155, 0.28),
    0 18px 34px rgba(248, 79, 155, 0.34),
    0 0 34px rgba(255, 138, 87, 0.25);
}

.tarot-back-card.just-picked img {
  animation: tarot-card-pick-pop 0.38s cubic-bezier(0.22, 0.86, 0.24, 1);
}

.tarot-spread-panel.shuffle-gather .tarot-back-card,
.tarot-spread-panel.shuffle-hindu .tarot-back-card {
  top: 50%;
  left: 50%;
  --move-delay: var(--gather-delay);
  transform: translate(-50%, -50%) rotate(var(--stack-rotate)) scale(0.94);
  pointer-events: none;
}

.tarot-spread-panel.shuffle-hindu .tarot-back-card {
  --move-delay: 0ms;
  transition-duration: 0.54s;
  transition-timing-function: cubic-bezier(0.25, 0.82, 0.25, 1);
  animation: tarot-card-soft-shuffle 1.22s cubic-bezier(0.4, 0, 0.2, 1) infinite;
  animation-delay: var(--shuffle-delay);
}

.tarot-spread-panel.shuffle-hindu .tarot-back-card.packet-active {
  filter: brightness(1.12) saturate(1.06);
}

.tarot-spread-panel.shuffle-hindu .tarot-back-card.packet-dropped {
  filter: brightness(0.98);
}

.tarot-spread-panel.shuffle-deal .tarot-back-card {
  --move-delay: var(--deal-delay);
  top: calc(24px + (var(--card-row) * 122px));
  left: calc(7% + (var(--card-col) * 9.55%));
  transform: translate(-50%, 0) rotate(var(--idle-rotate));
  transition-duration: 0.94s;
  transition-timing-function: cubic-bezier(0.2, 0.78, 0.24, 1);
  pointer-events: none;
}

.tarot-spread-panel.shuffling .tarot-back-card {
  pointer-events: none;
}

.tarot-back-card.disabled {
  opacity: 0.42;
}

.tarot-back-card img {
  display: block;
  width: var(--card-width);
  height: var(--card-height);
  object-fit: cover;
  box-sizing: border-box;
  border-radius: 8px;
  box-shadow: 0 12px 20px rgba(7, 2, 20, 0.34);
}

@keyframes tarot-card-soft-shuffle {
  0%,
  100% {
    transform: translate(-50%, -50%) rotate(var(--stack-rotate)) scale(0.955);
  }

  32% {
    transform:
      translate(calc(-50% + var(--shuffle-x)), calc(-50% + var(--shuffle-y)))
      rotate(var(--shuffle-rotate))
      scale(0.985);
  }

  64% {
    transform:
      translate(calc(-50% + var(--shuffle-back-x)), calc(-50% + var(--shuffle-back-y)))
      rotate(var(--shuffle-back-rotate))
      scale(0.948);
  }
}

@keyframes tarot-card-pick-pop {
  0% {
    transform: scale(1);
  }

  48% {
    transform: scale(1.045);
  }

  100% {
    transform: scale(1);
  }
}

.selected-card-zone {
  grid-template-columns: 220px minmax(0, 1fr);
  align-items: center;
  padding: 18px;
  border: 1px solid rgba(255, 116, 180, 0.18);
  border-radius: 22px;
  background: rgba(255, 255, 255, 0.035);
}

.pick-guide {
  display: grid;
  gap: 8px;
  color: rgba(255, 245, 230, 0.78);
  text-align: center;
}

.pick-guide > span {
  color: #ffd37a;
  font-size: 34px;
}

.pick-guide strong {
  color: #fff7df;
  line-height: 1.35;
}

.pick-guide p {
  margin: 0;
  font-size: 14px;
  line-height: 1.5;
}

.selected-slots {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 24px;
}

.selected-slot {
  display: grid;
  justify-items: center;
  gap: 8px;
}

.selected-slot > span {
  width: 24px;
  height: 24px;
  display: grid;
  place-items: center;
  border-radius: 50%;
  background: rgba(255, 245, 230, 0.9);
  color: #2d0d3f;
  font-size: 13px;
  font-weight: 950;
}

.empty-slot,
.selected-card-preview {
  width: 96px;
  height: 142px;
  border-radius: 14px;
}

.empty-slot {
  border: 1px dashed rgba(255, 245, 230, 0.42);
  background: rgba(255, 255, 255, 0.04);
}

.selected-card-preview {
  display: grid;
  place-items: center;
  padding: 0;
  border: 1px solid rgba(255, 116, 180, 0.32);
  background: rgba(255, 255, 255, 0.08);
  cursor: pointer;
  overflow: hidden;
}

.selected-card-preview img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.selected-card-preview img.reversed {
  transform: rotate(180deg);
}

.selected-card-preview strong {
  padding: 10px;
  color: #fff7df;
  font-size: 14px;
  line-height: 1.35;
  text-align: center;
}

.tarot-result-panel {
  display: grid;
  align-content: start;
  gap: 18px;
  padding: clamp(24px, 2.6vw, 32px);
}

.tarot-result-panel header {
  display: grid;
  grid-template-columns: 46px minmax(0, 1fr);
  gap: 12px;
  align-items: center;
}

.tarot-result-panel header span {
  width: 46px;
  height: 46px;
  display: grid;
  place-items: center;
  border-radius: 14px;
  background: rgba(255, 211, 122, 0.18);
  color: #ffd37a;
}

.tarot-result-panel h3 {
  margin: 0;
  color: #fff7df;
  font-size: 28px;
  line-height: 1.2;
}

.result-block,
.question-box,
.reading-result-card {
  display: grid;
  gap: 10px;
  padding: 16px;
  border: 1px solid rgba(255, 116, 180, 0.18);
  border-radius: 18px;
  background: rgba(255, 255, 255, 0.045);
}

.result-block h4,
.question-box label,
.reading-result-card h4 {
  margin: 0;
  color: rgba(255, 245, 230, 0.82);
  font-size: 15px;
  font-weight: 950;
}

.category-pill {
  width: fit-content;
  margin: 0;
  padding: 9px 14px;
  border: 1px solid rgba(255, 116, 180, 0.32);
  border-radius: 999px;
  color: #fff7df;
  font-weight: 900;
}

.selected-result-cards {
  display: grid;
  gap: 8px;
}

.selected-result-cards article {
  display: grid;
  grid-template-columns: 28px minmax(0, 1fr) auto;
  gap: 8px;
  align-items: center;
  padding: 10px;
  border-radius: 14px;
  background: rgba(255, 255, 255, 0.05);
}

.selected-result-cards span {
  width: 24px;
  height: 24px;
  display: grid;
  place-items: center;
  border-radius: 50%;
  background: rgba(255, 245, 230, 0.86);
  color: #2d0d3f;
  font-size: 12px;
  font-weight: 950;
}

.selected-result-cards strong,
.selected-result-cards small {
  min-width: 0;
}

.selected-result-cards strong {
  color: #fff7df;
}

.selected-result-cards small {
  color: rgba(255, 245, 230, 0.62);
  white-space: nowrap;
}

.question-box textarea {
  min-height: 112px;
  resize: vertical;
  padding: 14px;
  border: 1px solid rgba(255, 116, 180, 0.24);
  border-radius: 14px;
  background: rgba(255, 255, 255, 0.06);
  color: #fffaf0;
  outline: 0;
  line-height: 1.55;
}

.question-box small {
  justify-self: end;
  color: rgba(255, 245, 230, 0.58);
}

.analyze-button {
  min-height: 58px;
  white-space: nowrap;
}

.analyze-button:disabled {
  opacity: 0.62;
  color: rgba(255, 255, 255, 0.84);
}

.reading-loading-backdrop {
  position: fixed;
  inset: 0;
  z-index: 1200;
  display: grid;
  place-items: center;
  padding: 24px;
  background:
    radial-gradient(circle at 50% 42%, rgba(255, 211, 122, 0.16), transparent 32%),
    rgba(10, 3, 24, 0.68);
  backdrop-filter: blur(10px);
}

.reading-loading-modal {
  position: relative;
  width: min(100%, 390px);
  min-height: 430px;
  display: grid;
  justify-items: center;
  align-content: center;
  gap: 14px;
  padding: 34px 28px 32px;
  border: 1px solid rgba(255, 211, 122, 0.28);
  border-radius: 28px;
  background:
    linear-gradient(145deg, rgba(64, 18, 77, 0.96), rgba(24, 9, 42, 0.98)),
    rgba(45, 13, 63, 0.92);
  box-shadow:
    0 28px 80px rgba(7, 2, 20, 0.55),
    inset 0 1px 0 rgba(255, 255, 255, 0.08);
  overflow: hidden;
}

.reading-loading-modal::before {
  content: "";
  position: absolute;
  inset: 18px;
  border: 1px solid rgba(255, 255, 255, 0.08);
  border-radius: 22px;
  pointer-events: none;
}

.loading-orbit {
  position: absolute;
  width: 250px;
  height: 250px;
  border-radius: 50%;
  animation: loading-orbit-spin 5.6s linear infinite;
}

.loading-orbit span {
  position: absolute;
  width: 10px;
  height: 10px;
  border-radius: 50%;
  background: #ffd37a;
  box-shadow: 0 0 18px rgba(255, 211, 122, 0.8);
}

.loading-orbit span:nth-child(1) {
  top: 10px;
  left: 50%;
}

.loading-orbit span:nth-child(2) {
  right: 18px;
  bottom: 62px;
  background: #ff8a57;
}

.loading-orbit span:nth-child(3) {
  left: 24px;
  bottom: 56px;
  background: #f84f9b;
}

.reading-loading-character {
  position: relative;
  z-index: 1;
  width: min(72vw, 230px);
  height: 230px;
  object-fit: contain;
  background: transparent;
  filter: drop-shadow(0 22px 24px rgba(8, 2, 22, 0.34));
  mix-blend-mode: normal;
  animation: reading-character-search 1.72s ease-in-out infinite;
  transform-origin: 50% 86%;
}

.reading-loading-modal strong,
.reading-loading-modal p,
.reading-loading-dots {
  position: relative;
  z-index: 1;
}

.reading-loading-modal strong {
  color: #fff7df;
  font-size: 24px;
  line-height: 1.25;
  text-align: center;
}

.reading-loading-modal p {
  max-width: 280px;
  margin: 0;
  color: rgba(255, 245, 230, 0.72);
  line-height: 1.5;
  text-align: center;
}

.reading-loading-dots {
  display: inline-flex;
  gap: 7px;
  margin-top: 2px;
}

.reading-loading-dots span {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: #ffd37a;
  animation: reading-dot-bounce 0.96s ease-in-out infinite;
}

.reading-loading-dots span:nth-child(2) {
  animation-delay: 0.16s;
}

.reading-loading-dots span:nth-child(3) {
  animation-delay: 0.32s;
}

@keyframes reading-character-search {
  0%,
  100% {
    transform: translateY(0) rotate(-1deg) scale(1);
  }

  48% {
    transform: translateY(-9px) rotate(1.5deg) scale(1.035);
  }
}

@keyframes loading-orbit-spin {
  to {
    transform: rotate(360deg);
  }
}

@keyframes reading-dot-bounce {
  0%,
  100% {
    transform: translateY(0);
    opacity: 0.45;
  }

  50% {
    transform: translateY(-5px);
    opacity: 1;
  }
}

.result-help,
.reading-error {
  margin: 0;
  color: rgba(255, 245, 230, 0.64);
  font-size: 14px;
  line-height: 1.45;
  text-align: center;
}

.reading-error {
  color: #ffb09a;
  font-weight: 850;
}

.reading-result-card p {
  margin: 0;
  color: rgba(255, 245, 230, 0.74);
  line-height: 1.55;
}

.streaming-text {
  position: relative;
  white-space: pre-line;
}

.streaming-text.streaming::after {
  content: "";
  display: inline-block;
  width: 2px;
  height: 1em;
  margin-left: 4px;
  border-radius: 999px;
  background: rgba(255, 245, 230, 0.86);
  vertical-align: -0.12em;
  animation: streaming-cursor-blink 0.82s steps(2, start) infinite;
}

@keyframes streaming-cursor-blink {
  0%,
  45% {
    opacity: 1;
  }

  46%,
  100% {
    opacity: 0;
  }
}

.card-reading-list {
  display: grid;
  gap: 10px;
  margin-top: 4px;
}

.card-reading-list article {
  display: grid;
  gap: 6px;
  padding: 12px;
  border-radius: 14px;
  background: rgba(255, 255, 255, 0.045);
}

.card-reading-list strong {
  color: #ffd37a;
}

.result-actions {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 10px;
}

.result-actions button {
  min-height: 46px;
  border: 1px solid rgba(255, 116, 180, 0.24);
  border-radius: 999px;
  background: rgba(255, 255, 255, 0.055);
  color: #fff7df;
  font-weight: 900;
  cursor: pointer;
}

.result-actions button:disabled {
  cursor: wait;
  opacity: 0.66;
}

.tarot-bottom-note {
  width: min(100%, 1440px);
  min-height: 52px;
  display: grid;
  grid-template-columns: 52px minmax(0, 1fr);
  gap: 12px;
  align-items: center;
  margin: 14px auto 0;
  padding: 8px 20px;
  border-radius: 22px;
}

.tarot-bottom-note img {
  width: 44px;
  height: 34px;
  object-fit: contain;
}

.tarot-bottom-note span {
  color: rgba(255, 245, 230, 0.72);
  font-size: 13.5px;
  line-height: 1.42;
  text-align: center;
}

@media (max-width: 1180px) {
  .tarot-draw-layout {
    grid-template-columns: 1fr;
  }

  .tarot-result-panel {
    width: 100%;
  }
}

@media (max-width: 900px) {
  .tarot-draw-page {
    padding: 20px 14px 34px;
  }

  .tarot-steps {
    grid-template-columns: 1fr;
  }

  .tarot-steps i {
    display: none;
  }

  .tarot-spread-panel {
    --card-width: 58px;
    --card-height: 86px;
    min-height: 238px;
    padding: 16px;
  }

  .selected-card-zone {
    grid-template-columns: 1fr;
  }

  .selected-slots {
    gap: 12px;
  }
}

@media (max-width: 620px) {
  .tarot-spread-panel {
    --card-width: 48px;
    --card-height: 72px;
    min-height: 226px;
  }

  .selected-slots,
  .result-actions,
  .tarot-bottom-note {
    grid-template-columns: 1fr;
  }

  .reading-loading-modal {
    min-height: 390px;
    padding: 30px 22px;
  }

  .reading-loading-character {
    width: min(74vw, 200px);
    height: 200px;
  }
}
</style>
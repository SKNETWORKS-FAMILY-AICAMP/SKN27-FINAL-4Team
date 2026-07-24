<script setup>
import { computed, onBeforeUnmount, onMounted, ref, watch } from "vue";
import { useRouter } from "vue-router";
import { getLocalDateString } from "../../api/client.js";
import { calendarApi } from "../../api/calendar.js";
import { tarotApi } from "../../api/tarot.js";
import calendarFortuneIcon from "../../assets/icons/calendar-fortune.png";
import calendarRecordIcon from "../../assets/icons/calendar-record.png";
import calendarStreakIcon from "../../assets/icons/calendar-streak.png";
import calendarTrendIcon from "../../assets/icons/calendar-trend.png";
import calendarEmptyIcon from "../../assets/icons/calendar-empty.png";

const today = new Date();
const router = useRouter();
const YEAR_PAGE_SIZE = 6;
const currentYear = ref(today.getFullYear());
const currentMonth = ref(today.getMonth() + 1);
const yearPageStart = ref(currentYear.value - 2);
const selectedDate = ref(toDateString(today));
const monthFortunes = ref([]);
const selectedFortune = ref(null);
const isMonthLoading = ref(false);
const isDayLoading = ref(false);
const errorMessage = ref("");
const isMonthPickerOpen = ref(false);

const CALENDAR_DAILY_MAJOR_CACHE_KEY = "binteumsaiCalendarDailyMajorCard";
const DAILY_MAJOR_CACHE_KEY = "binteumsaiDailyMajorCard";
const USER_PROFILE_KEY = "binteumsaiUserProfile";
const CHARACTER_STORAGE_KEY = "binteumsaiCharacter";
const VALID_CHARACTER_IDS = new Set(["otter", "cat", "redpanda", "bird"]);
const VALID_EXPRESSION_IDS = new Set(["joy", "anger", "sadness", "anxiety", "hurt", "panic"]);
// 백엔드 emotion_label (joy/sadness/anger/normal) → 표정 이미지 id
// (구버전 라벨 매핑으로 표정이 안 바뀌던 버그 수정 — 2026-07-03)
const EMOTION_TO_EXPRESSION = {
  joy: "joy",
  sadness: "sadness",
  anger: "anger",
  normal: null,
};
const dailyMajor = ref(null);
const isDailyMajorLoading = ref(false);
const dailyMajorError = ref("");
const storedCharacter = ref(readStoredCharacter());

const monthTitle = computed(() => `${currentYear.value}년 ${currentMonth.value}월`);
const yearOptions = computed(() =>
  Array.from({ length: YEAR_PAGE_SIZE }, (_, index) => yearPageStart.value + index)
);
const selectedDateLabel = computed(() => {
  const date = new Date(`${selectedDate.value}T00:00:00`);
  return `${date.getFullYear()}년 ${date.getMonth() + 1}월 ${date.getDate()}일`;
});
const todayString = computed(() => getLocalDateString());
const selectedDateState = computed(() => {
  if (selectedDate.value === todayString.value) return "today";
  return selectedDate.value < todayString.value ? "past" : "future";
});
const selectedDateGuide = computed(() => {
  if (selectedDateState.value === "past") {
    return "이미 지나간 시간은 바꿀 수 없지만, \n 지금 이 순간에 최선을 다해 보세요.";
  }

  if (selectedDateState.value === "future") {
    return "아직 펼쳐지지 않은 하루예요. \n다가올 시간을 기대하며 기다려볼까요?";
  }

  if (hasViewedTodayCard.value) {
    return "오늘의 카드 기록을 차분히 정리하고 있어요.";
  }

  return "오늘의 운세카드를 아직 확인하지 않았어요.";
});
const hasViewedTodayCard = computed(() => {
  if (selectedFortune.value && selectedDate.value === todayString.value) return true;

  try {
    const cached = JSON.parse(localStorage.getItem(DAILY_MAJOR_CACHE_KEY) || "{}");
    return cached.date === todayString.value && cached.revealed === true && Boolean(cached.card);
  } catch {
    return false;
  }
});
const selectedMonthHasRecords = computed(() => monthFortunes.value.length > 0);
const recordCount = computed(() => monthFortunes.value.length);
const streakCount = computed(() => getCurrentStreak(monthFortunes.value));
const selectedCharacterId = computed(() => normalizeCharacterId(storedCharacter.value.characterId));
const fallbackExpressionId = computed(() => normalizeExpressionId(storedCharacter.value.expressionId));
const selectedCharacterDefaultUrl = computed(() => getCharacterImageUrl(selectedCharacterId.value, "default"));
const selectedCalendarEntry = computed(() => fortuneByDate.value[selectedDate.value] || null);
const selectedEmotionEntry = computed(() => {
  if (selectedFortune.value || !selectedCalendarEntry.value?.emotion_label) return null;
  return selectedCalendarEntry.value;
});
const selectedDetailCharacterUrl = computed(() => {
  const record = selectedFortune.value || selectedCalendarEntry.value;
  if (!record) return selectedCharacterDefaultUrl.value;
  return getCharacterImageUrl(selectedCharacterId.value, getFortuneExpressionId(record));
});

const dailyMajorSummary = computed(() => {
  if (isDailyMajorLoading.value) {
    return "생년월일을 바탕으로 오늘의 운세 카드를 불러오고 있어요.";
  }

  if (!dailyMajor.value) {
    return dailyMajorError.value || "생년월일을 저장하면 오늘의 운세 카드 내용을 확인할 수 있어요.";
  }

  const cardName = dailyMajor.value.card_name_ko || dailyMajor.value.card_name || "";
  const cardMeaning =
    dailyMajor.value.card_defined_meaning ||
    dailyMajor.value.card_description ||
    dailyMajor.value.message ||
    "오늘의 카드가 전하는 메시지를 잠시 후 다시 확인해 주세요.";

  return cardName ? `${cardName} · ${cardMeaning}` : cardMeaning;
});

// 선택한 날짜에 저장된 그 날의 카드 내용을 표시 (오늘의 daily-major로 덮어쓰지 않음)
const selectedFortuneSummary = computed(() => {
  const fortune = selectedFortune.value;
  if (!fortune) return "";

  const storedCard = Array.isArray(fortune.cards) ? fortune.cards[0] : fortune.card;
  const cardName =
    fortune.card_name_ko ||
    fortune.card_name ||
    fortune.major_card_name ||
    storedCard?.card_name_ko ||
    storedCard?.card_name ||
    storedCard?.name_ko ||
    storedCard?.name ||
    "";
  const cardMeaning =
    fortune.card_defined_meaning ||
    fortune.card_description ||
    fortune.message ||
    fortune.summary ||
    fortune.description ||
    fortune.content ||
    fortune.keyword ||
    "";

  if (cardName && cardMeaning && cardName !== cardMeaning) {
    return `${cardName} · ${cardMeaning}`;
  }

  // 오늘 날짜이면서 그날 저장 카드에 상세 내용이 없을 때만 오늘의 카드 내용으로 보완
  if (selectedDate.value === todayString.value && dailyMajor.value) {
    return dailyMajorSummary.value;
  }

  return cardName || cardMeaning || "이 날 저장된 운세 기록이에요.";
});

const fortuneByDate = computed(() => {
  return monthFortunes.value.reduce((acc, item) => {
    acc[item.date] = item;
    return acc;
  }, {});
});

const calendarDays = computed(() => {
  const firstDate = new Date(currentYear.value, currentMonth.value - 1, 1);
  const lastDate = new Date(currentYear.value, currentMonth.value, 0);
  const days = [];

  for (let index = 0; index < firstDate.getDay(); index += 1) {
    days.push({ key: `blank-${index}`, blank: true });
  }

  for (let day = 1; day <= lastDate.getDate(); day += 1) {
    const date = toDateString(new Date(currentYear.value, currentMonth.value - 1, day));
    const fortune = fortuneByDate.value[date];
    days.push({
      key: date,
      day,
      date,
      state: fortune ? "fortune" : "empty",
      label: fortune?.keyword || (fortune ? "운세" : "기록 없음"),
      emojiUrl: fortune ? getCharacterImageUrl(selectedCharacterId.value, getFortuneExpressionId(fortune), true) : "",
      fortune,
    });
  }

  return days;
});

onMounted(() => {
  refreshStoredCharacter();
  window.addEventListener("storage", refreshStoredCharacter);
  loadMonth();
  loadDailyMajor();
});

onBeforeUnmount(() => {
  window.removeEventListener("storage", refreshStoredCharacter);
});

watch([currentYear, currentMonth], () => {
  loadMonth();
});

watch(currentYear, () => {
  syncYearPageToCurrentYear();
});

function readStoredCharacter() {
  try {
    return JSON.parse(localStorage.getItem(CHARACTER_STORAGE_KEY) || "{}");
  } catch {
    return {};
  }
}

function refreshStoredCharacter(event) {
  if (event?.key && event.key !== CHARACTER_STORAGE_KEY) return;
  storedCharacter.value = readStoredCharacter();
}

function normalizeCharacterId(value) {
  const characterId = String(value || "").trim();
  if (VALID_CHARACTER_IDS.has(characterId)) return characterId;
  if (characterId === "haeon") return "otter";
  if (characterId === "greung" || characterId === "geureung") return "cat";
  if (characterId === "dalkong") return "redpanda";
  return "otter";
}

function normalizeExpressionId(value) {
  const expressionId = String(value || "").trim();
  return VALID_EXPRESSION_IDS.has(expressionId) ? expressionId : "joy";
}

function getFortuneExpressionId(fortune) {
  const emotionExpression = EMOTION_TO_EXPRESSION[fortune?.emotion_label];
  if (emotionExpression) return emotionExpression;

  const explicitExpression =
    fortune?.expression_id ||
    fortune?.expressionId ||
    fortune?.expression ||
    fortune?.emotion_expression ||
    fortune?.emotionExpression;

  if (VALID_EXPRESSION_IDS.has(explicitExpression)) return explicitExpression;
  return fallbackExpressionId.value;
}

function getCharacterImageUrl(characterId, expressionId = "default", faceOnly = false) {
  const safeCharacterId = normalizeCharacterId(characterId);
  const safeExpressionId = expressionId === "default" ? "default" : normalizeExpressionId(expressionId);
  const prefix = faceOnly ? "/characters/faces" : "/characters";
  return `${prefix}/${safeCharacterId}/${safeExpressionId}.png`;
}

async function loadDailyMajor() {
  const todayString = getLocalDateString();
  const cached = readDailyMajorCache(todayString);

  if (cached?.card) {
    dailyMajor.value = cached.card;
    dailyMajorError.value = "";
    isDailyMajorLoading.value = false;
    return;
  }

  isDailyMajorLoading.value = true;
  dailyMajorError.value = "";

  try {
    dailyMajor.value = await tarotApi.getDailyMajor(todayString);
    saveDailyMajorCache(todayString);
  } catch (error) {
    dailyMajor.value = null;
    dailyMajorError.value =
      error.response?.data?.error || "오늘의 운세 카드를 불러오지 못했어요.";
  } finally {
    isDailyMajorLoading.value = false;
  }
}

function readDailyMajorCache(date) {
  const profileSignature = getStoredProfileSignature();
  if (!profileSignature) return null;

  try {
    const cached = JSON.parse(localStorage.getItem(CALENDAR_DAILY_MAJOR_CACHE_KEY) || "{}");
    if (
      cached.date === date &&
      cached.profileSignature === profileSignature &&
      cached.card
    ) {
      return cached;
    }
  } catch {
    return null;
  }

  return null;
}

function saveDailyMajorCache(date) {
  const profileSignature = getStoredProfileSignature();
  if (!profileSignature || !dailyMajor.value) return;

  localStorage.setItem(
    CALENDAR_DAILY_MAJOR_CACHE_KEY,
    JSON.stringify({
      date,
      profileSignature,
      card: dailyMajor.value,
    })
  );
}

function getStoredProfileSignature() {
  try {
    const profile = JSON.parse(localStorage.getItem(USER_PROFILE_KEY) || "{}");
    return String(profile.birth_date || profile.birthDate || profile.birthday || "").trim();
  } catch {
    return "";
  }
}

async function loadMonth() {
  isMonthLoading.value = true;
  errorMessage.value = "";

  try {
    monthFortunes.value = await calendarApi.getMonth(currentYear.value, currentMonth.value);
    if (!isSelectedDateInCurrentMonth()) {
      selectedDate.value = toDateString(new Date(currentYear.value, currentMonth.value - 1, 1));
    }
    await loadDay(selectedDate.value);
  } catch (error) {
    monthFortunes.value = [];
    selectedFortune.value = null;
    errorMessage.value = getErrorMessage(error);
  } finally {
    isMonthLoading.value = false;
  }
}

async function loadDay(date) {
  selectedDate.value = date;
  isDayLoading.value = true;
  errorMessage.value = "";

  try {
    const data = await calendarApi.getDay(date);
    selectedFortune.value = data.fortune;
  } catch (error) {
    selectedFortune.value = null;
    errorMessage.value = getErrorMessage(error);
  } finally {
    isDayLoading.value = false;
  }
}

function moveMonth(offset) {
  const next = new Date(currentYear.value, currentMonth.value - 1 + offset, 1);
  currentYear.value = next.getFullYear();
  currentMonth.value = next.getMonth() + 1;
  isMonthPickerOpen.value = false;
}

function goToday() {
  currentYear.value = today.getFullYear();
  currentMonth.value = today.getMonth() + 1;
  selectedDate.value = toDateString(today);
  syncYearPageToCurrentYear();
  isMonthPickerOpen.value = false;
  loadDay(selectedDate.value);
}

function goTodayFortune() {
  if (selectedDate.value !== todayString.value || hasViewedTodayCard.value) return;
  router.push("/onboarding/fortune");
}

function toggleMonthPicker() {
  isMonthPickerOpen.value = !isMonthPickerOpen.value;

  if (isMonthPickerOpen.value) {
    syncYearPageToCurrentYear();
  }
}

function moveYearRange(offset) {
  yearPageStart.value += offset * YEAR_PAGE_SIZE;
}

function selectYear(year) {
  currentYear.value = year;
}

function selectMonth(month) {
  currentMonth.value = month;
  isMonthPickerOpen.value = false;
}

function syncYearPageToCurrentYear() {
  const firstYear = yearPageStart.value;
  const lastYear = yearPageStart.value + YEAR_PAGE_SIZE - 1;

  if (currentYear.value < firstYear || currentYear.value > lastYear) {
    yearPageStart.value = currentYear.value - 2;
  }
}

function isSelectedDateInCurrentMonth() {
  return selectedDate.value.startsWith(`${currentYear.value}-${String(currentMonth.value).padStart(2, "0")}`);
}

function getCurrentStreak(records) {
  if (!records.length) return 0;
  const dates = new Set(records.map((item) => item.date));
  let cursor = new Date(`${toDateString(today)}T00:00:00`);
  let count = 0;

  while (dates.has(toDateString(cursor))) {
    count += 1;
    cursor.setDate(cursor.getDate() - 1);
  }

  return count || Math.min(records.length, 2);
}

function toDateString(date) {
  const year = date.getFullYear();
  const month = String(date.getMonth() + 1).padStart(2, "0");
  const day = String(date.getDate()).padStart(2, "0");
  return `${year}-${month}-${day}`;
}

function getErrorMessage(error) {
  return error.response?.data?.error || "캘린더 기록을 불러오지 못했어요.";
}
</script>

<template>
  <section class="view-card calendar-view">
    <article class="glass-panel calendar-board">
      <header class="calendar-heading">
        <div>
          <h2>마음 캘린더 ✦</h2>
          <p>Mind calendar</p>
          <span>날짜별로 저장된 운세 기록을 모아보고, 날짜를 선택하면 자세한 운세 내용을 확인할 수 있어요.</span>
        </div>

        <div class="calendar-legend">
          <button class="active" type="button"><i class="fortune"></i>운세 기록</button>
          <button type="button"><i class="empty"></i>기록 없음</button>
        </div>
      </header>

      <div class="calendar-toolbar">
        <div class="month-picker-wrap">
          <button
            class="month-title-button"
            type="button"
            :aria-expanded="isMonthPickerOpen"
            @click="toggleMonthPicker"
          >
            🗓 {{ monthTitle }}
          </button>

          <div v-if="isMonthPickerOpen" class="month-popover">
            <div class="year-picker">
              <button
                class="year-nav"
                type="button"
                aria-label="이전 연도 범위"
                @click.stop="moveYearRange(-1)"
              >
                ‹
              </button>

              <div class="year-list">
                <button
                  v-for="year in yearOptions"
                  :key="year"
                  type="button"
                  :class="{ active: currentYear === year }"
                  @click.stop="selectYear(year)"
                >
                  {{ year }}년
                </button>
              </div>

              <button
                class="year-nav"
                type="button"
                aria-label="다음 연도 범위"
                @click.stop="moveYearRange(1)"
              >
                ›
              </button>
            </div>

            <div class="month-grid">
              <button
                v-for="month in 12"
                :key="month"
                type="button"
                :class="{ active: currentMonth === month }"
                @click="selectMonth(month)"
              >
                {{ month }}월
              </button>
            </div>
          </div>
        </div>

        <div class="calendar-nav-buttons">
          <button class="btn secondary small" type="button" @click="moveMonth(-1)">이전</button>
          <button class="btn secondary small" type="button" @click="moveMonth(1)">다음</button>
          <button class="btn secondary small" type="button" @click="goToday">오늘</button>
        </div>
      </div>

      <section class="calendar-stats" aria-label="이번 달 기록 요약">
        <article>
          <img class="calendar-stat-icon" :src="calendarRecordIcon" alt="" aria-hidden="true">
          <div>
            <strong>{{ recordCount }}일</strong>
            <p>이번 달 기록</p>
          </div>
        </article>
        <article>
          <img class="calendar-stat-icon" :src="calendarStreakIcon" alt="" aria-hidden="true">
          <div>
            <strong>{{ streakCount }}일</strong>
            <p>현재 연속 기록</p>
          </div>
        </article>
        <article class="wide">
          <img class="calendar-stat-icon" :src="calendarTrendIcon" alt="" aria-hidden="true">
          <div>
            <p>이번 달 감정 요약</p>
          </div>
          <img class="calendar-stats-character" :src="selectedCharacterDefaultUrl" alt="" aria-hidden="true">
        </article>
      </section>

      <p v-if="errorMessage" class="calendar-error">{{ errorMessage }}</p>

      <div class="calendar-grid" :aria-label="`${monthTitle} 운세 기록`">
        <span class="weekday">일</span>
        <span class="weekday">월</span>
        <span class="weekday">화</span>
        <span class="weekday">수</span>
        <span class="weekday">목</span>
        <span class="weekday">금</span>
        <span class="weekday">토</span>

        <span v-for="day in calendarDays.filter((item) => item.blank)" :key="day.key" class="calendar-day blank"></span>

        <button
          v-for="day in calendarDays.filter((item) => !item.blank)"
          :key="day.key"
          type="button"
          class="calendar-day"
          :class="[day.state, { selected: selectedDate === day.date }]"
          @click="loadDay(day.date)"
        >
          <strong>{{ day.day }}</strong>
          <span v-if="day.emojiUrl" class="calendar-character-emoji">
            <img :src="day.emojiUrl" :alt="day.label" draggable="false">
          </span>
          <span v-else>{{ day.label }}</span>
        </button>
      </div>

      <p v-if="!isMonthLoading && !selectedMonthHasRecords" class="calendar-empty-note">
        이번 달에는 아직 저장된 운세가 없어요. 운세 화면에서 타로 결과를 생성하면 오늘 날짜에 자동 저장돼요.
      </p>
    </article>

    <aside class="glass-panel calendar-detail">
      <h3>{{ selectedDateLabel }} 기록 ✦</h3>

      <div class="calendar-detail-hero">
        <img :src="selectedDetailCharacterUrl" alt="" aria-hidden="true">
      </div>

      <template v-if="selectedFortune">
        <div class="daily-summary today-fortune-summary">
          <img class="daily-summary-icon" :src="calendarFortuneIcon" alt="" aria-hidden="true">
          <div>
            <strong>{{ selectedDate === todayString ? '오늘의 운세' : '이 날의 운세' }}</strong>
            <p>{{ selectedFortuneSummary }}</p>
          </div>
        </div>
      </template>

      <template v-else-if="selectedEmotionEntry">
        <div class="daily-summary today-fortune-summary">
          <img class="daily-summary-icon" :src="calendarRecordIcon" alt="" aria-hidden="true">
          <div>
            <strong>대화 감정 기록</strong>
          </div>
        </div>
      </template>

      <div v-else class="empty-detail-card">
        <img class="empty-detail-icon" :src="calendarEmptyIcon" alt="" aria-hidden="true">
        <strong>저장된 운세 없음</strong>
        <p class="selected-date-guide">
          {{ selectedDateGuide }}
        </p>
        <i></i>
        <template v-if="selectedDateState === 'today' && !hasViewedTodayCard">
          <h4>오늘의 카드 확인하기</h4>
          <p>오늘의 운세카드를 확인하면 캘린더에서 다시 돌아볼 수 있어요.</p>
          <button class="btn primary full" type="button" @click="goTodayFortune">오늘의 운세카드 보러가기 ›</button>
        </template>
        <template v-else>
          <h4>오늘의 마음을 지켜봐요</h4>
          <p>날짜에 맞는 기록만 차분히 확인할 수 있어요.</p>
        </template>
      </div>
    </aside>
  </section>
</template>

<style scoped>
.calendar-view {
  width: min(1560px, calc(100% - 64px));
  min-height: calc(100vh - var(--bt-header-h) - 52px);
  display: grid;
  grid-template-columns: minmax(0, 1fr) 430px;
  gap: 22px;
  margin: 28px auto 34px;
}

.calendar-board,
.calendar-detail {
  border-radius: 28px;
  background:
    linear-gradient(145deg, rgba(62, 25, 76, 0.9), rgba(23, 10, 44, 0.88)),
    rgba(50, 24, 73, 0.76);
}

.calendar-board {
  overflow: visible;
  padding: clamp(28px, 3vw, 44px);
}

.calendar-detail {
  padding: 32px 28px;
}

.calendar-heading {
  display: flex;
  justify-content: space-between;
  gap: 22px;
  align-items: start;
}

.calendar-heading h2 {
  margin: 0;
  color: #fff1cd;
  font-size: clamp(40px, 3.8vw, 56px);
  line-height: 1.08;
}

.calendar-heading p {
  margin: 8px 0 10px;
  color: #ffbd82;
  font-size: 18px;
  font-weight: 900;
}

.calendar-heading span {
  display: block;
  color: rgba(255, 245, 238, 0.72);
  font-size: 16px;
  line-height: 1.6;
}

.calendar-legend {
  display: flex;
  gap: 10px;
  flex: 0 0 auto;
}

.calendar-legend button {
  min-height: 44px;
  padding: 0 18px;
  border: 1px solid rgba(255, 143, 164, 0.34);
  border-radius: 999px;
  background: rgba(255, 255, 255, 0.06);
  color: rgba(255, 245, 238, 0.76);
  font-weight: 900;
}

.calendar-legend button.active {
  color: #fff;
  background: linear-gradient(135deg, #e73e65, #e77e6e);
}

.calendar-legend i {
  width: 8px;
  height: 8px;
  display: inline-block;
  margin-right: 8px;
  border-radius: 50%;
}

.calendar-legend .fortune {
  background: #fff1cd;
}

.calendar-legend .empty {
  background: rgba(255, 255, 255, 0.28);
}

.calendar-toolbar {
  display: flex;
  justify-content: space-between;
  gap: 18px;
  align-items: center;
  margin: 26px 0 16px;
}

.month-picker-wrap {
  position: relative;
  z-index: 50;
}

.month-title-button {
  min-height: 50px;
  padding: 0 22px;
  border: 1px solid rgba(255, 143, 164, 0.44);
  border-radius: 999px;
  background: rgba(255, 255, 255, 0.06);
  color: #fff1cd;
  font-size: 19px;
  font-weight: 950;
  cursor: pointer;
}

.month-popover {
  position: absolute;
  top: calc(100% + 10px);
  left: 0;
  z-index: 100;
  width: min(420px, calc(100vw - 40px));
  display: grid;
  gap: 12px;
  padding: 14px;
  border: 1px solid rgba(231, 62, 101, 0.42);
  border-radius: 18px;
  background: rgba(38, 14, 60, 0.96);
  box-shadow: 0 20px 50px rgba(0, 0, 0, 0.32);
}

.year-picker {
  display: grid;
  grid-template-columns: 34px minmax(0, 1fr) 34px;
  gap: 8px;
  align-items: center;
}

.year-list {
  display: grid;
  grid-template-columns: repeat(5, minmax(0, 1fr));
  gap: 6px;
}

.month-grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 8px;
}

.month-popover button {
  min-height: 38px;
  border: 0;
  border-radius: 12px;
  background: rgba(255, 255, 255, 0.07);
  color: rgba(255, 245, 238, 0.78);
  font-weight: 900;
  cursor: pointer;
}

.month-popover .year-nav {
  min-height: 34px;
  padding: 0;
  font-size: 20px;
  line-height: 1;
}

.year-list button {
  min-height: 34px;
  padding: 0 6px;
  font-size: 13px;
}

.month-popover button.active {
  color: #fff;
  background: linear-gradient(135deg, #e73e65, #e77e6e);
}

@media (max-width: 560px) {
  .month-popover {
    width: min(330px, calc(100vw - 28px));
  }

  .year-list {
    grid-template-columns: repeat(3, minmax(0, 1fr));
  }
}

.calendar-nav-buttons {
  display: flex;
  gap: 12px;
  align-items: center;
}

.calendar-stats {
  display: grid;
  grid-template-columns: 1.1fr 1.1fr 2fr;
  gap: 0;
  margin: 12px 0 22px;
  border: 1px solid rgba(255, 143, 164, 0.24);
  border-radius: 16px;
  background: rgba(255, 255, 255, 0.055);
  overflow: hidden;
}

.calendar-stats article {
  min-height: 92px;
  display: grid;
  grid-template-columns: 54px minmax(0, 1fr);
  gap: 14px;
  align-items: center;
  padding: 18px 22px;
  border-right: 1px solid rgba(255, 255, 255, 0.12);
}

.calendar-stats article:last-child {
  border-right: 0;
}

.calendar-stats span {
  width: 44px;
  height: 44px;
  display: grid;
  place-items: center;
  border-radius: 50%;
  background: rgba(255, 241, 205, 0.14);
  font-size: 23px;
}

.calendar-stat-icon {
  width: 44px;
  height: 44px;
  display: block;
  object-fit: contain;
  filter: drop-shadow(0 7px 10px rgba(20, 4, 34, 0.3));
}

.calendar-stats strong {
  color: #fff1cd;
  font-size: 28px;
  font-weight: 950;
}

.calendar-stats p {
  margin: 4px 0 0;
  color: rgba(255, 245, 238, 0.68);
  font-size: 14px;
  font-weight: 800;
}

.calendar-stats .wide {
  position: relative;
  padding-right: 106px;
}

.calendar-stats .wide strong {
  font-size: 18px;
}

.calendar-stats .wide .calendar-stats-character {
  position: absolute;
  right: 18px;
  bottom: 0;
  width: 82px;
  height: 88px;
  object-fit: contain;
}

.calendar-grid {
  display: grid;
  grid-template-columns: repeat(7, minmax(0, 1fr));
  gap: 10px;
}

.weekday {
  display: grid;
  place-items: center;
  min-height: 32px;
  color: rgba(255, 245, 238, 0.78);
  font-size: 16px;
  font-weight: 950;
}

.calendar-day {
  position: relative;
  min-height: 86px;
  display: grid;
  align-content: start;
  justify-items: start;
  gap: 12px;
  padding: 12px 14px;
  border: 1px solid rgba(255, 143, 164, 0.22);
  border-radius: 12px;
  background: rgba(255, 255, 255, 0.045);
  color: #fff;
  cursor: pointer;
}

.calendar-day.blank {
  visibility: hidden;
  pointer-events: none;
}

.calendar-day strong {
  font-size: 21px;
  font-weight: 950;
}

.calendar-day > span:not(.calendar-character-emoji) {
  color: rgba(255, 245, 238, 0.7);
  font-size: 13px;
  font-weight: 850;
}

.calendar-day.fortune {
  border-color: rgba(255, 143, 164, 0.36);
  background: rgba(255, 255, 255, 0.07);
}

.calendar-day.selected {
  border-color: rgba(255, 143, 164, 0.96);
  background: linear-gradient(135deg, #e73e65, #e77e6e);
  box-shadow: 0 14px 30px rgba(231, 62, 101, 0.3);
}

.calendar-character-emoji {
  position: absolute;
  right: 9px;
  bottom: 6px;
  width: 44px;
  height: 48px;
}

.calendar-character-emoji img {
  width: 100%;
  height: 100%;
  object-fit: contain;
}

.calendar-detail h3 {
  margin: 0;
  color: #fff1cd;
  font-size: 28px;
  line-height: 1.2;
}

.calendar-detail-hero {
  min-height: 188px;
  display: grid;
  place-items: center;
}

.calendar-detail-hero img {
  width: 182px;
  height: 182px;
  object-fit: contain;
  filter: drop-shadow(0 20px 24px rgba(3, 1, 18, 0.42));
}

.daily-summary,
.empty-detail-card {
  border: 1px solid rgba(255, 143, 164, 0.24);
  border-radius: 20px;
  background:
    linear-gradient(145deg, rgba(231, 62, 101, 0.22), rgba(231, 126, 110, 0.1)),
    rgba(255, 255, 255, 0.045);
}

.daily-summary {
  display: grid;
  grid-template-columns: 44px minmax(0, 1fr);
  gap: 14px;
  padding: 18px;
  margin-top: 14px;
}

.daily-summary-icon {
  width: 44px;
  height: 44px;
  object-fit: contain;
}

.daily-summary strong {
  color: #fff;
  font-size: 17px;
}

.daily-summary p {
  margin: 6px 0 0;
  color: rgba(255, 245, 238, 0.72);
  line-height: 1.55;
}

.empty-detail-card {
  display: grid;
  justify-items: center;
  gap: 14px;
  padding: 28px 22px;
  text-align: center;
}

.empty-detail-card > span {
  width: 74px;
  height: 74px;
  display: grid;
  place-items: center;
  border: 1px solid rgba(255, 143, 164, 0.28);
  border-radius: 22px;
  background: rgba(255, 255, 255, 0.08);
  font-size: 34px;
}

.empty-detail-icon {
  width: 74px;
  height: 74px;
  display: block;
  object-fit: contain;
  filter: drop-shadow(0 10px 14px rgba(20, 4, 34, 0.3));
}

.empty-detail-card strong,
.empty-detail-card h4 {
  margin: 0;
  color: #fff1cd;
  font-size: 22px;
  font-weight: 950;
}

.empty-detail-card p {
  margin: 0;
  color: rgba(255, 245, 238, 0.72);
  line-height: 1.65;
}

.empty-detail-card i {
  width: 70%;
  height: 1px;
  margin: 10px 0;
  background: linear-gradient(90deg, transparent, rgba(255, 143, 164, 0.42), transparent);
}

.calendar-error,
.calendar-empty-note {
  margin: 0 0 14px;
  color: #ffad9a;
  font-size: 14px;
  font-weight: 850;
}

.calendar-empty-note {
  margin-top: 16px;
  color: rgba(255, 245, 238, 0.68);
}

@media (max-width: 1180px) {
  .calendar-view {
    grid-template-columns: 1fr;
    width: min(100% - 28px, 920px);
  }
}

@media (max-width: 760px) {
  .calendar-board,
  .calendar-detail {
    padding: 22px;
  }

  .calendar-heading,
  .calendar-toolbar {
    display: grid;
  }

  .calendar-legend,
  .calendar-nav-buttons {
    flex-wrap: wrap;
  }

  .calendar-stats {
    grid-template-columns: 1fr;
  }

  .calendar-stats article {
    border-right: 0;
    border-bottom: 1px solid rgba(255, 255, 255, 0.12);
  }

  .calendar-grid {
    gap: 7px;
  }

  .calendar-day {
    min-height: 70px;
    padding: 9px;
  }

  .calendar-day > span:not(.calendar-character-emoji) {
    font-size: 11px;
  }
}

@media (max-height: 760px) {
  :global(#app .calendar-view) {
    height: auto !important;
    min-height: calc(100dvh - var(--bt-header-h) - 1px) !important;
    margin-bottom: 36px !important;
    overflow: visible !important;
  }

  :global(#app .calendar-board),
  :global(#app .calendar-detail) {
    height: auto !important;
    max-height: none !important;
    overflow: visible !important;
  }
}
</style>

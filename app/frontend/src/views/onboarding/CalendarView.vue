<script setup>
import { ref } from "vue";

const selectedDay = ref(23);
const days = [
  { day: 1, state: "mood", label: "차분" },
  { day: 2, state: "empty", label: "" },
  { day: 3, state: "fortune", label: "운세" },
  { day: 4, state: "multi", label: "대화" },
  { day: 5, state: "mood", label: "기쁨" },
  { day: 6, state: "empty", label: "" },
  { day: 7, state: "mood", label: "피로" },
  { day: 8, state: "fortune", label: "운세" },
  { day: 9, state: "mood", label: "안정" },
  { day: 10, state: "multi", label: "기록" },
  { day: 11, state: "empty", label: "" },
  { day: 12, state: "mood", label: "긴장" },
  { day: 13, state: "fortune", label: "운세" },
  { day: 14, state: "mood", label: "회복" },
  { day: 15, state: "multi", label: "대화" },
  { day: 16, state: "mood", label: "흐림" },
  { day: 17, state: "fortune", label: "운세" },
  { day: 18, state: "empty", label: "" },
  { day: 19, state: "mood", label: "평온" },
  { day: 20, state: "multi", label: "기록" },
  { day: 21, state: "mood", label: "쉼" },
  { day: 22, state: "fortune", label: "운세" },
  { day: 23, state: "multi", label: "오늘" },
  { day: 24, state: "empty", label: "" },
  { day: 25, state: "mood", label: "기대" },
  { day: 26, state: "empty", label: "" },
  { day: 27, state: "mood", label: "몰입" },
  { day: 28, state: "fortune", label: "운세" },
  { day: 29, state: "empty", label: "" },
  { day: 30, state: "mood", label: "정리" }
];
const week = [
  { day: "월", value: 42 },
  { day: "화", value: 56 },
  { day: "수", value: 48 },
  { day: "목", value: 64 },
  { day: "금", value: 52 },
  { day: "토", value: 76 },
  { day: "일", value: 68 }
];
</script>

<template>
  <section class="view-card calendar-view">
    <article class="glass-panel calendar-board">
      <div class="content-heading">
        <div>
          <p class="section-kicker">Mind calendar</p>
          <h2>마음 캘린더</h2>
          <p>하루 감정, 운세, 대화 기록을 날짜별로 모아보고 회고해요.</p>
        </div>
        <div class="calendar-legend">
          <span><i class="mood"></i>감정</span>
          <span><i class="fortune"></i>운세</span>
          <span><i class="multi"></i>여러 기록</span>
        </div>
      </div>

      <div class="calendar-grid" aria-label="2026년 6월 마음 기록">
        <span class="weekday">월</span><span class="weekday">화</span><span class="weekday">수</span><span class="weekday">목</span><span class="weekday">금</span><span class="weekday">토</span><span class="weekday">일</span>
        <button
          v-for="day in days"
          :key="day.day"
          type="button"
          class="calendar-day"
          :class="[day.state, { selected: selectedDay === day.day }]"
          @click="selectedDay = day.day"
        >
          <strong>{{ day.day }}</strong>
          <span>{{ day.label || "기록 없음" }}</span>
        </button>
      </div>
    </article>

    <aside class="glass-panel calendar-detail">
      <h3>{{ selectedDay }}일의 마음 기록</h3>
      <div class="daily-summary">
        <span class="sticker-icon calendar"></span>
        <div>
          <strong>감정 한줄평</strong>
          <p>오늘은 해야 할 일이 많았지만, 저녁에는 조금 안정감을 되찾았어요.</p>
        </div>
      </div>
      <div class="daily-summary">
        <span class="sticker-icon fortune"></span>
        <div>
          <strong>오늘의 카드 운세</strong>
          <p>작은 안부가 관계의 온도를 부드럽게 바꿀 수 있어요.</p>
        </div>
      </div>
      <section class="weekly-card">
        <h3>일주일 감정 그래프</h3>
        <div class="mini-week-chart">
          <span v-for="item in week" :key="item.day" :style="{ '--height': item.value + '%' }">
            <i></i><b>{{ item.day }}</b>
          </span>
        </div>
      </section>
    </aside>
  </section>
</template>

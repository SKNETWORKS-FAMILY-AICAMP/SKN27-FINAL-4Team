<template>
  <div class="panel-body weather-panel-body">
    <section class="weather-panel-layout">
      <aside class="weather-current-card" aria-label="현재 날씨 정보">
        <div class="weather-region-row">
          <label for="weather-region">지역</label>
          <select id="weather-region" :value="selectedRegion" @change="$emit('change-region', $event.target.value)">
            <option value="현재 위치">현재 위치</option>
            <option v-for="region in regions" :key="region" :value="region">{{ region }}</option>
          </select>
        </div>

        <div :class="['weather-visual', weatherArtClass, timeOfDayClass]">
          <div :class="['weather-illustration', weatherArtClass, timeOfDayClass]" aria-hidden="true">
            <span class="weather-art-star star-one"></span>
            <span class="weather-art-star star-two"></span>
            <span class="weather-art-star star-three"></span>
            <span class="weather-art-sun"></span>
            <span class="weather-art-moon"></span>
            <span class="weather-art-cloud cloud-main"></span>
            <span class="weather-art-cloud cloud-soft"></span>
            <span class="weather-art-drop drop-one"></span>
            <span class="weather-art-drop drop-two"></span>
            <span class="weather-art-drop drop-three"></span>
            <span class="weather-art-snow snow-one"></span>
            <span class="weather-art-snow snow-two"></span>
            <span class="weather-art-snow snow-three"></span>
          </div>
          <strong>{{ weatherCondition }}</strong>
          <span>{{ locationName }}</span>
        </div>

        <div class="weather-main-metrics">
          <div>
            <span>기온</span>
            <strong>{{ valueOrDash(weather?.temperature) }}<small>℃</small></strong>
          </div>
          <div>
            <span>습도</span>
            <strong>{{ valueOrDash(weather?.humidity) }}<small>%</small></strong>
          </div>
        </div>

        <dl class="weather-detail-list">
          <div>
            <dt>강수량</dt>
            <dd>{{ valueOrDash(weather?.rainfall_1h) }} mm</dd>
          </div>
          <div>
            <dt>풍속</dt>
            <dd>{{ valueOrDash(weather?.wind_speed) }} m/s</dd>
          </div>
          <div>
            <dt>기준 시각</dt>
            <dd>{{ formattedBaseTime }}</dd>
          </div>
        </dl>

        <p v-if="error" class="weather-error">{{ error }}</p>
        <p v-else-if="loading" class="weather-loading">날씨와 추천을 불러오는 중입니다.</p>

        <button class="weather-refresh-button" type="button" :disabled="loading" @click="$emit('refresh')">
          새로고침
        </button>
      </aside>

      <article class="weather-insight-card" aria-label="창문 밖 분위기와 오늘의 추천">
        <nav class="weather-section-tabs" aria-label="날씨 정보 섹션">
          <button
            v-for="section in weatherSections"
            :key="section.key"
            type="button"
            :class="{ active: activeWeatherSection === section.key }"
            :disabled="loading"
            @click="activeWeatherSection = section.key"
          >
            <strong>{{ section.label }}</strong>
          </button>
        </nav>

        <section v-if="loading" class="weather-section-page weather-refresh-state" aria-live="polite">
          <div class="weather-refresh-spinner" aria-hidden="true"></div>
          <strong>새 날씨를 반영하고 있어요</strong>
          <p>관측 정보와 생활 가이드를 다시 읽는 중입니다.</p>
        </section>

        <section v-else-if="activeWeatherSection === 'summary'" class="weather-section-page weather-summary-page">
          <div class="weather-section-heading">
            <span class="weather-section-label">현재 날씨</span>
            <h3>{{ insightTitle }}</h3>
            <p style="white-space: pre-wrap; line-height: 1.6;">{{ insight?.weatherAnalysis || loadingText }}</p>
          </div>

          <div class="weather-guide-grid" aria-label="오늘의 컨디션 지표">
            <article v-for="item in conditionGuide" :key="item.label" class="weather-guide-card">
              <div class="weather-guide-head">
                <strong>{{ item.label }}</strong>
                <span>{{ item.level }}</span>
              </div>
              <div class="weather-guide-meter" aria-hidden="true">
                <i :style="{ width: `${getMeterWidth(item)}%`, background: getMeterColor(item.level) }"></i>
              </div>
              <p>{{ item.reason }}</p>
            </article>
          </div>

        </section>

        <section v-else-if="activeWeatherSection === 'rhythm'" class="weather-section-page weather-rhythm-section" aria-label="시간대별 날씨 리듬">
          <div class="weather-section-heading">
            <span class="weather-section-label">시간대별 예보</span>
            <h3>초단기 날씨 흐름</h3>
            <p>앞으로의 단기적인 날씨 변화를 보여드려요.</p>
          </div>

          <div class="weather-rhythm-list" style="display: flex; gap: 1rem; overflow-x: auto; padding-bottom: 0.5rem; scrollbar-width: thin;">
            <article
              v-for="(item, index) in hourlyForecasts"
              :key="index"
              class="weather-rhythm-card"
              style="min-width: 100px; flex-shrink: 0; text-align: center; display: flex; flex-direction: column; align-items: center; justify-content: center; gap: 0.5rem;"
            >
              <span style="font-weight: 600; font-size: 1.1rem; color: var(--text-muted);">{{ item.time }}</span>
              <div style="display: flex; flex-direction: column; align-items: center;">
                <span style="font-size: 2rem; line-height: 1; margin-bottom: 0.2rem;">{{ getWeatherEmoji(item.condition, item.time) }}</span>
                <strong style="font-size: 0.85rem; color: var(--text-muted); font-weight: normal;">{{ item.condition }}</strong>
                <p style="margin: 0.3rem 0 0 0; font-size: 1.1rem; color: var(--text-main); font-weight: bold;">{{ item.temperature }}℃</p>
                <span v-if="item.rainfall && item.rainfall !== '강수없음'" style="font-size: 0.8rem; color: var(--color-blue); margin-top: 0.2rem;">{{ item.rainfall }}</span>
              </div>
            </article>
          </div>
          
          <div class="weekly-forecast-summary" style="margin-top: 1.5rem; padding: 1.2rem; border-radius: 12px; background: rgba(255, 255, 255, 0.05); border: 1px solid rgba(255, 255, 255, 0.1);">
            <h4 style="margin: 0 0 0.5rem 0; font-size: 1.1rem; color: var(--text-main);">주간 예보 요약</h4>
            <p style="margin: 0; font-size: 0.95rem; line-height: 1.5; color: var(--text-muted);">{{ weeklyForecast }}</p>
          </div>
        </section>

        <section v-else class="weather-section-page weather-recommend-section">
          <div class="weather-section-heading">
            <span class="weather-section-label">상황별 선택지</span>
            <h3>오늘 날씨에 맞춘 작은 선택</h3>
            <p>하나만 골라도 충분하도록, 상황과 바로 할 일을 같이 묶었어요.</p>
          </div>

          <div class="weather-recommend-list">
            <article
              v-for="(item, index) in recommendations"
              :key="`${item.title}-${index}`"
              class="weather-recommend-card"
            >
              <b>{{ index + 1 }}</b>
              <div>
                <strong>{{ item.title }}</strong>
                <p>{{ item.reason }}</p>
                <span>{{ item.howTo }}</span>
              </div>
            </article>
          </div>
        </section>

        <button class="weather-close-button" type="button" @click="$emit('close')">닫기</button>
      </article>
    </section>
  </div>
</template>

<script>
export default {
  name: "WeatherPanel",
  props: {
    payload: { type: Object, default: null },
    loading: { type: Boolean, default: false },
    error: { type: String, default: "" },
    location: { type: Object, default: null },
    regions: { type: Array, default: () => [] }
  },
  emits: ["refresh", "close", "change-region"],
  data() {
    return {
      activeWeatherSection: "summary",
      weatherSections: [
        { key: "summary", label: "오늘" },
        { key: "rhythm", label: "예보" },
        { key: "choices", label: "추천" }
      ]
    };
  },
  watch: {
    loading(isLoading) {
      if (isLoading) this.activeWeatherSection = "summary";
    }
  },
  computed: {
    weather() {
      return this.payload?.weather || null;
    },
    insight() {
      return this.payload?.insight || null;
    },
    locationName() {
      return this.weather?.location?.name || this.location?.region || "서울";
    },
    selectedRegion() {
      if (this.location?.mode === "auto") return "현재 위치";
      return this.location?.region || this.locationName;
    },
    weatherCondition() {
      return this.weather?.condition || "날씨 확인 중";
    },
    weatherArtClass() {
      const condition = this.weatherCondition;
      if (condition.includes("비/눈") || condition.includes("눈날림")) return "is-mixed";
      if (condition.includes("눈")) return "is-snow";
      if (condition.includes("비") || condition.includes("소나기")) return "is-rain";
      if (condition.includes("맑음")) return "is-sunny";
      if (condition.includes("흐림")) return "is-overcast";
      return "is-cloudy";
    },
    timeOfDayClass() {
      const hour = this.weatherHour;
      if (hour === null) return "is-day";
      return hour >= 6 && hour < 18 ? "is-day" : "is-night";
    },
    weatherHour() {
      const time = this.weather?.base_time;
      if (!time || time.length < 2) return null;
      const hour = Number(time.slice(0, 2));
      return Number.isFinite(hour) ? hour : null;
    },
    formattedBaseTime() {
      const date = this.weather?.base_date;
      const time = this.weather?.base_time;
      if (!date || !time) return "-";
      return `${date.slice(4, 6)}.${date.slice(6, 8)} ${time.slice(0, 2)}:${time.slice(2, 4)}`;
    },
    loadingText() {
      return this.loading ? "날씨 데이터를 분석하여 맞춤형 리포트를 준비하고 있습니다." : "새로운 날씨 리포트를 불러오는 중입니다.";
    },
    insightTitle() {
      if (this.error) return "날씨 정보를 확인할 수 없어요";
      if (this.loading) return "날씨 리포트를 작성하는 중이에요";
      return `${this.locationName}의 지금 날씨는`;
    },
    conditionGuide() {
      const items = this.insight?.conditionGuide;
      if (Array.isArray(items) && items.length) return items;
      return [
        { label: "불쾌지수", level: "보통", score: 50, reason: "날씨 정보를 불러오는 중입니다." },
        { label: "식중독지수", level: "관심", score: 30, reason: "날씨 정보를 불러오는 중입니다." },
        { label: "체감온도", level: "보통", score: 50, reason: "날씨 정보를 불러오는 중입니다." },
        { label: "감기가능지수", level: "보통", score: 50, reason: "날씨 정보를 불러오는 중입니다." }
      ];
    },
    hourlyForecasts() {
      const items = this.insight?.hourlyForecasts;
      if (Array.isArray(items) && items.length) return items;
      return [
        { time: "-", condition: "확인 중", temperature: "-", rainfall: "-" }
      ];
    },
    weeklyForecast() {
      return this.insight?.weeklyForecast || "주간 날씨 정보를 확인 중입니다.";
    },

    recommendations() {
      const items = this.insight?.recommendations;
      if (Array.isArray(items) && items.length) return items;
      return [
        {
          title: "잠깐 쉬어가기",
          reason: "날씨 정보를 불러오는 동안에도 오늘의 리듬을 잠깐 낮춰두면 좋아요.",
          howTo: "물 한 모금 마시고 어깨를 천천히 내려보세요."
        },
        {
          title: "창문 밖 확인",
          reason: "현재 위치 기준 날씨가 준비되면 더 알맞은 추천을 보여드릴게요.",
          howTo: "새로고침을 눌러 다시 확인해보세요."
        }
      ];
    }
  },
  methods: {
    getWeatherEmoji(condition, timeStr) {
      if (!condition) return "☁️";
      
      let isNight = false;
      if (timeStr) {
        const hour = parseInt(timeStr.split(":")[0], 10);
        if (!isNaN(hour) && (hour >= 19 || hour < 6)) {
          isNight = true;
        }
      } else {
        if (this.timeOfDayClass === "is-night") {
          isNight = true;
        }
      }

      if (condition.includes("비/눈") || condition.includes("눈날림")) return "🌨️";
      if (condition.includes("눈")) return "❄️";
      if (condition.includes("소나기")) return "🌦️";
      if (condition.includes("비")) return "🌧️";
      
      if (condition.includes("맑음")) return isNight ? "🌙" : "☀️";
      if (condition.includes("구름")) return isNight ? "☁️" : "⛅";
      if (condition.includes("흐림")) return "☁️";
      
      return "☁️";
    },
    getMeterColor(level) {
      if (!level) return "#8ea7ff";
      if (level.includes("매우 높음") || level.includes("위험")) return "#ff4d4f";
      if (level.includes("높음") || level.includes("경고") || level.includes("주의")) return "#ffa940";
      if (level.includes("보통") || level.includes("관심") || level.includes("낮음")) return "#73d13d";
      return "#8ea7ff";
    },
    getMeterWidth(item) {
      const score = Number(item.score || 0);
      if (item.label === "체감온도") {
        return Math.max(0, Math.min(100, ((score + 20) / 60) * 100));
      }
      return Math.max(0, Math.min(100, score));
    },
    valueOrDash(value) {
      return value === null || value === undefined || value === "" ? "-" : value;
    },
    numberValue(value) {
      const number = Number(value);
      return Number.isFinite(number) ? number : null;
    },
    scoreLevel(score) {
      if (score >= 66) return "높음";
      if (score >= 38) return "보통";
      return "낮음";
    }
  }
};
</script>

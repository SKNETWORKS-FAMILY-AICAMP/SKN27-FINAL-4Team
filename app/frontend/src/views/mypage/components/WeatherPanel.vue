<template>
  <div class="panel-body weather-panel-body">
    <section class="weather-panel-layout">
      <aside class="weather-current-card" aria-label="현재 날씨 정보" @focusout="closeRegionMenuOnFocusOut">
        <div class="weather-region-row">
          <span class="weather-region-label">지역 선택</span>
          <div class="weather-region-control">
            <span class="weather-region-pin" aria-hidden="true"></span>
            <button
              id="weather-region"
              class="weather-region-trigger"
              type="button"
              :disabled="loading"
              :aria-expanded="regionMenuOpen"
              aria-haspopup="listbox"
              @click="regionMenuOpen = !regionMenuOpen"
            >
              {{ selectedRegion }}
              <span class="weather-region-chevron" aria-hidden="true"></span>
            </button>
          </div>
        </div>

        <div v-if="regionMenuOpen" class="weather-region-menu" role="listbox" aria-label="날씨 지역 선택">
          <button
            v-for="regionName in ['현재 위치'].concat(regions || [])"
            :key="regionName"
            type="button"
            role="option"
            :aria-selected="selectedRegion === regionName"
            :class="{ selected: selectedRegion === regionName }"
            @click="selectRegion(regionName)"
          >
            <span>{{ regionName }}</span>
          </button>
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
            <dd>{{ formatRainfall(weather?.rainfall_1h, weatherCondition) }}</dd>
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
        <p v-else-if="loading" class="weather-loading">{{ selectedRegion }} 날씨와 추천을 불러오는 중입니다.</p>

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

        <section v-if="loading && (!payload || isLocationTransition)" class="weather-section-page weather-refresh-state" aria-live="polite">
          <div class="weather-refresh-spinner" aria-hidden="true"></div>
          <strong>{{ selectedRegion }} 날씨를 반영하고 있어요</strong>
          <p>이전 지역 정보는 잠시 숨기고, 새 관측 정보와 생활 가이드를 불러오는 중입니다.</p>
        </section>

        <section v-else-if="activeWeatherSection === 'summary'" class="weather-section-page weather-summary-page">
          <div class="weather-section-heading">
            <span class="weather-section-label">오늘의 날씨</span>
            <h3>{{ insightTitle }}</h3>
            <p style="white-space: pre-wrap; line-height: 1.6;">{{ insight?.weatherAnalysis || loadingText }}</p>
          </div>

          <hr class="weather-section-divider" aria-hidden="true" />

          <div class="weather-guide-grid" aria-label="오늘의 생활 참고 지표">
            <article
              v-for="item in conditionGuide"
              :key="item.label"
              class="weather-guide-card"
              :class="`is-${item.severity || 'unavailable'}`"
              :style="{ '--index-color': getMeterColor(item) }"
            >
              <div class="weather-guide-head">
                <strong>{{ item.label }}</strong>
                <span :style="{ borderColor: getMeterColor(item), color: getMeterColor(item) }">
                  {{ formatIndexValue(item) }} · {{ item.level }}
                </span>
              </div>
              <div
                class="weather-guide-meter"
                role="meter"
                :aria-label="`${item.label} ${formatIndexValue(item)}, ${item.level}`"
                :aria-valuenow="item.available === false ? undefined : item.value"
                :aria-valuemin="item.scale_min"
                :aria-valuemax="item.scale_max"
              >
                <i
                  v-if="item.available !== false"
                  class="weather-guide-fill"
                  :style="{ width: `${getMeterWidth(item)}%`, background: getMeterColor(item) }"
                ></i>
                <i
                  v-if="item.available !== false"
                  class="weather-guide-marker"
                  :style="{ left: `${getMeterWidth(item)}%`, background: getMeterColor(item) }"
                ></i>
              </div>
              <div class="weather-guide-scale" aria-hidden="true">
                <span>{{ item.scale_min_label }}</span>
                <span>{{ item.scale_max_label }}</span>
              </div>
            </article>
          </div>
          <p class="weather-index-note">생활 판단을 돕는 참고값이며, 건강 상태를 진단하거나 의료적 판단을 대신하지 않습니다.</p>

          <details class="weather-alert-card weather-alert-fold" :class="weatherAlertClass" :open="weatherAlerts.status === 'active' || undefined">
            <summary class="weather-alert-head">
              <div>
                <span class="weather-alert-icon" aria-hidden="true">!</span>
                <div>
                  <strong>현재 기상특보</strong>
                  <small>{{ weatherAlerts.region || locationName }} 기준</small>
                </div>
              </div>
              <span class="weather-alert-badge">{{ weatherAlertBadge }}</span>
            </summary>

            <div v-if="weatherAlertItems.length" class="weather-alert-summary">
              <div
                v-for="item in weatherAlertItems"
                :key="`${item.type}-${item.level}-${item.region}-${item.effective_at}`"
                class="weather-alert-row"
              >
                <strong>{{ item.type }}{{ item.level }}</strong>
                <span>{{ item.region }}</span>
                <small v-if="item.effective_at">발효 {{ formatAlertTime(item.effective_at) }}</small>
              </div>
            </div>
            <p v-else class="weather-alert-message">{{ weatherAlerts.message || "특보 현황을 확인하는 중입니다." }}</p>

            <div class="weather-alert-links">
              <span v-if="weatherAlerts.checked_at">확인 {{ formatAlertTime(weatherAlerts.checked_at) }}</span>
              <a v-if="weatherAlerts.source_url" :href="weatherAlerts.source_url" target="_blank" rel="noopener noreferrer">기상청 특보현황</a>
              <a v-if="weatherAlerts.status === 'key_required' && weatherAlerts.docs_url" :href="weatherAlerts.docs_url" target="_blank" rel="noopener noreferrer">API허브 설정</a>
            </div>
          </details>

        </section>

        <section v-else-if="activeWeatherSection === 'rhythm'" class="weather-section-page weather-rhythm-section" aria-label="시간대별 날씨 리듬">
          <div class="weather-section-heading">
            <span class="weather-section-label">오늘의 흐름</span>
            <h3>지금부터 날씨가 이렇게 흘러가요</h3>
            <p>나갈 시간을 떠올리며 가볍게 살펴보세요.</p>
          </div>

          <div class="weather-rhythm-list" aria-label="시간대별 단기 예보 목록">
            <article
              v-for="(item, index) in hourlyForecasts"
              :key="index"
              class="weather-rhythm-card"
            >
              <span class="weather-rhythm-time">{{ item.time }}</span>
              <div class="weather-rhythm-detail">
                <span class="weather-rhythm-icon">{{ getWeatherEmoji(item.condition, item.time) }}</span>
                <strong>{{ item.condition }}</strong>
                <p>{{ item.temperature }}℃</p>
                <span v-if="shouldShowRainfall(item)" class="weather-rhythm-rainfall">{{ formatRainfall(item.rainfall, item.condition) }}</span>
              </div>
            </article>
          </div>
          
          <div class="weekly-forecast-summary">
            <h4>이번 주는</h4>
            <p>{{ forecastSummary }}</p>
          </div>
        </section>

        <section v-else class="weather-section-page weather-recommend-section">
          <div class="weather-section-heading">
            <span class="weather-section-label">오늘 챙길 것</span>
            <h3>이런 준비가 잘 맞겠어요</h3>
            <p>오늘 날씨에 어울리는 것부터 하나씩 골라보세요.</p>
          </div>

          <div class="weather-recommend-list">
            <article
              v-for="(item, index) in recommendations"
              :key="`${item.title}-${index}`"
              class="weather-recommend-card"
            >
              <b class="weather-recommend-number">{{ index + 1 }}</b>
              <div class="weather-recommend-content">
                <strong>{{ item.title }}</strong>
                <p>{{ item.summary || item.reason }}</p>
                <ul>
                  <li v-for="(action, actionIndex) in recommendationActions(item)" :key="`${item.title}-${actionIndex}`">
                    {{ action }}
                  </li>
                </ul>
              </div>
            </article>
          </div>
        </section>

        <footer class="weather-provenance" aria-label="날씨 데이터 출처">
          <a
            v-if="kmaAttribution.url"
            :href="kmaAttribution.url"
            target="_blank"
            rel="noopener noreferrer"
          >출처: {{ kmaAttribution.label }}</a>
          <details v-if="webSources.length">
            <summary>웹 검색 출처 {{ webSources.length }}개</summary>
            <ul>
              <li v-for="source in webSources" :key="source.url">
                <a :href="source.url" target="_blank" rel="noopener noreferrer">{{ source.title }}</a>
              </li>
            </ul>
          </details>
          <details v-if="methodology">
            <summary>지수·그래프 계산</summary>
            <p>{{ methodology.summary }}</p>
            <p>{{ methodology.graph }}</p>
            <a v-if="methodology.formula_source_url" :href="methodology.formula_source_url" target="_blank" rel="noopener noreferrer">기상청 체감온도 산식 보기</a>
            <a v-if="methodology.discomfort_source_url" :href="methodology.discomfort_source_url" target="_blank" rel="noopener noreferrer">기상청 생활기상지수 안내 보기</a>
          </details>
          <details v-if="processingNotice || apiLimits">
            <summary>AI·API 이용 안내</summary>
            <p>{{ generationSummary }}</p>
            <p>현재 위치는 날씨 조회에만 사용하며 서버에 별도 저장하지 않습니다. OpenAI에는 선택한 취미·오늘의 감정과 지역 단위 날씨만, Tavily에는 지역명과 검색 기준일만 전송합니다.</p>
            <ul v-if="apiLimits">
              <li v-if="apiLimits.kma_api_hub"><a :href="apiLimits.kma_api_hub?.url" target="_blank" rel="noopener noreferrer">기상청 API허브</a>: {{ apiLimits.kma_api_hub?.applied }}</li>
              <li><a :href="apiLimits.tavily?.url" target="_blank" rel="noopener noreferrer">Tavily</a>: {{ apiLimits.tavily?.applied }}</li>
              <li><a :href="apiLimits.openai?.url" target="_blank" rel="noopener noreferrer">OpenAI</a>: {{ apiLimits.openai?.applied }}</li>
              <li v-if="tavilyAttribution?.terms_url"><a :href="tavilyAttribution.terms_url" target="_blank" rel="noopener noreferrer">Tavily 약관·최종 이용자 의무</a></li>
            </ul>
          </details>
        </footer>

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
      regionMenuOpen: false,
      weatherSections: [
        { key: "summary", label: "오늘" },
        { key: "rhythm", label: "예보" },
        { key: "choices", label: "추천" }
      ]
    };
  },
  watch: {
    loading(isLoading) {
      if (isLoading && (!this.payload || this.isLocationTransition)) this.activeWeatherSection = "summary";
    }
  },
  computed: {
    isLocationTransition() {
      if (!this.loading || !this.payload?.weather) return false;
      if (this.location?.mode === "auto") return true;
      const requested = String(this.location?.region || "").trim();
      const displayed = String(this.payload?.weather?.location?.name || "").trim();
      return Boolean(requested && displayed && requested !== displayed);
    },
    weather() {
      if (this.isLocationTransition) return null;
      return this.payload?.weather || null;
    },
    insight() {
      if (this.isLocationTransition) return null;
      return this.payload?.insight || null;
    },
    attributions() {
      return Array.isArray(this.payload?.attributions) ? this.payload.attributions : [];
    },
    kmaAttribution() {
      return this.attributions.find(item => item?.id === "kma") || {
        label: "기상청 API허브",
        url: "https://apihub.kma.go.kr/apiInfo.do"
      };
    },
    tavilyAttribution() {
      return this.attributions.find(item => item?.id === "tavily") || this.insight?.webSearchProvider || null;
    },
    webSources() {
      return Array.isArray(this.insight?.sources) ? this.insight.sources.filter(source => source?.url) : [];
    },
    processingNotice() {
      return this.payload?.processing_notice || null;
    },
    methodology() {
      return this.payload?.methodology || null;
    },
    apiLimits() {
      return this.payload?.api_limits || null;
    },
    generation() {
      return this.insight?.generation || null;
    },
    generationSummary() {
      if (this.generation?.status === "generated") {
        return this.generation.personalized
          ? `OpenAI가 ${this.generation.personalization_fields.join("·")}을 최소한으로 참고해 개인화 문장을 생성했습니다.`
          : "OpenAI가 기상청 관측값과 공개 검색 근거로 안내 문장을 생성했습니다.";
      }
      return "AI 생성이 제한되면 관측값 기반 기본 안내로 자동 전환됩니다.";
    },
    locationName() {
      return this.weather?.location?.name || this.location?.region || "서울";
    },
    selectedRegion() {
      if (this.location?.mode === "auto") {
        const resolvedRegion = String(this.weather?.location?.name || "").trim();
        return resolvedRegion && resolvedRegion !== "현재 위치"
          ? `현재 위치 · ${resolvedRegion} 기준`
          : "현재 위치";
      }
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
      if (this.loading) return "오늘 날씨를 살펴보고 있어요";
      return `오늘 ${this.locationName}${this.topicParticle(this.locationName)} ${this.weatherCondition}`;
    },
    conditionGuide() {
      const items = this.insight?.conditionGuide;
      if (Array.isArray(items) && items.length) return items;
      return [
        { label: "불쾌지수", level: "확인 중", severity: "unavailable", value: null, unit: "", gauge_percent: 0, scale_min: 60, scale_max: 90, scale_min_label: "60", scale_max_label: "90", status: "날씨 정보를 불러오는 중입니다.", bands: [], available: false },
        { label: "체감온도", level: "확인 중", severity: "unavailable", value: null, unit: "℃", gauge_percent: 0, scale_min: 20, scale_max: 42, scale_min_label: "20℃", scale_max_label: "42℃", status: "날씨 정보를 불러오는 중입니다.", bands: [], available: false },
        { label: "식중독지수", level: "확인 중", severity: "unavailable", value: null, unit: "", gauge_percent: 0, scale_min: 0, scale_max: 100, scale_min_label: "0", scale_max_label: "100", status: "날씨 정보를 불러오는 중입니다.", bands: [], available: false },
        { label: "자외선지수", level: "확인 중", severity: "unavailable", value: null, unit: "", gauge_percent: 0, scale_min: 0, scale_max: 15, scale_min_label: "0", scale_max_label: "15", status: "날씨 정보를 불러오는 중입니다.", bands: [], available: false }
      ];
    },
    weatherAlerts() {
      return this.weather?.weather_alerts || {
        available: false,
        status: "loading",
        items: [],
        region: this.locationName,
        message: "특보 현황을 확인하는 중입니다."
      };
    },
    weatherAlertItems() {
      return Array.isArray(this.weatherAlerts.items) ? this.weatherAlerts.items : [];
    },
    weatherAlertBadge() {
      if (this.weatherAlerts.status === "active") {
        return this.weatherAlertItems.some((item) => item.level === "경보") ? "경보 발효" : "특보 발효";
      }
      if (this.weatherAlerts.status === "none") return "발효 없음";
      if (this.weatherAlerts.status === "key_required") return "연동 필요";
      return "확인 필요";
    },
    weatherAlertClass() {
      if (this.weatherAlerts.status === "active") {
        return this.weatherAlertItems.some((item) => item.level === "경보") ? "is-danger" : "is-warning";
      }
      if (this.weatherAlerts.status === "none") return "is-clear";
      return "is-unavailable";
    },
    hourlyForecasts() {
      const items = this.insight?.hourlyForecasts;
      if (Array.isArray(items) && items.length) return items;
      return [
        { time: "-", condition: "확인 중", temperature: "-", rainfall: "-" }
      ];
    },
    forecastSummary() {
      return this.insight?.forecastSummary || this.insight?.weeklyForecast || "기상청 주간예보를 일시적으로 확인할 수 없습니다.";
    },

    recommendations() {
      const items = this.insight?.recommendations;
      if (Array.isArray(items) && items.length) return items;
      return [
        {
          kind: "general",
          title: "현재 날씨 다시 확인하기",
          summary: "관측값을 불러오면 시간대별 강수와 기온에 맞춘 준비를 표시합니다.",
          actions: ["새로고침 후 현재 위치와 기준 시각을 확인하기"]
        },
        {
          kind: "general",
          title: "외출 시각 정하기",
          summary: "현재 위치의 시간대별 예보가 준비된 뒤 출발 시각을 정하는 편이 정확합니다.",
          actions: ["시간대별 예보가 표시된 뒤 강수 구간을 확인하기"]
        },
        {
          kind: "hobby",
          title: "좋아하는 일 잠깐 즐기기",
          summary: "저장된 취미를 불러오면 오늘 날씨에 어울리는 즐기는 방법을 함께 보여드립니다.",
          actions: ["날씨 정보가 표시된 뒤 취미 추천을 확인하기"]
        }
      ];
    }
  },
  methods: {
    topicParticle(value) {
      const text = String(value || "").trim();
      if (!text) return "는";
      const lastCharacter = text[text.length - 1];
      const code = lastCharacter.charCodeAt(0);
      if (code < 0xac00 || code > 0xd7a3) return "는";
      return (code - 0xac00) % 28 === 0 ? "는" : "은";
    },
    selectRegion(region) {
      this.regionMenuOpen = false;
      if (region !== this.selectedRegion) this.$emit("change-region", region);
    },
    closeRegionMenuOnFocusOut(event) {
      if (!event.currentTarget.contains(event.relatedTarget)) this.regionMenuOpen = false;
    },
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
    getMeterColor(item) {
      const matchingBand = (item?.bands || []).find((band) => band.level === item?.level);
      if (matchingBand) return this.getBandColor(matchingBand);
      const severity = item?.severity;
      if (severity === "danger") return "#ef4444";
      if (severity === "warning") return "#f97316";
      if (severity === "caution") return "#facc15";
      if (severity === "interest") return "#3b82f6";
      if (severity === "safe") return "#22c55e";
      return "#8ea7ff";
    },
    getBandColor(band) {
      const level = String(band?.level || "");
      if (level.includes("매우 높음") || level.includes("위험")) return "#ef4444";
      if (level === "높음" || level.includes("경고")) return "#f97316";
      if (level === "보통" || level.includes("주의")) return "#facc15";
      if (level.includes("관심")) return "#3b82f6";
      if (level.includes("낮음") || level.includes("기준 미만")) return "#22c55e";
      return band?.color || "#8ea7ff";
    },
    getMeterWidth(item) {
      const percent = Number(item.gauge_percent || 0);
      return Math.max(0, Math.min(100, percent));
    },
    formatIndexValue(item) {
      if (!item || item.available === false || item.value === null || item.value === undefined) return "-";
      return `${item.value}${item.unit || ""}`;
    },
    recommendationActions(item) {
      if (Array.isArray(item?.actions) && item.actions.length) return item.actions;
      return item?.howTo ? [item.howTo] : [];
    },
    formatAlertTime(value) {
      const text = String(value || "").replace(/\D/g, "");
      if (text.length < 12) return value || "-";
      return `${text.slice(4, 6)}.${text.slice(6, 8)} ${text.slice(8, 10)}:${text.slice(10, 12)}`;
    },
    valueOrDash(value) {
      return value === null || value === undefined || value === "" ? "-" : value;
    },
    isPrecipitationCondition(condition) {
      const text = String(condition || "");
      return text.includes("비") || text.includes("눈") || text.includes("소나기");
    },
    formatRainfall(value, condition = "") {
      if (value === null || value === undefined || value === "" || value === "-") {
        return this.isPrecipitationCondition(condition) ? "측정 중" : "-";
      }
      const text = String(value).trim();
      if (text === "강수없음") return "0 mm";
      if (/mm/i.test(text)) return text;
      return `${text} mm`;
    },
    shouldShowRainfall(item) {
      if (this.isPrecipitationCondition(item?.condition)) return true;
      const value = String(item?.rainfall || "").trim();
      return Boolean(value && value !== "강수없음" && !/^0(?:\.0+)?(?:\s*mm)?$/i.test(value));
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

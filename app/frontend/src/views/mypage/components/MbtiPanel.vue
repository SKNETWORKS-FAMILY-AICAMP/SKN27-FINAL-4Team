<template>
  <div class="panel-body">
    <div class="actions mbti-refresh-actions">
      <button class="secondary-button" type="button" @click="$emit('refresh')">
        분석 결과 새로고침
      </button>
    </div>

    <template v-if="mbtiViewMode === 'onboardingType'">
      <div class="mbti-dashboard mbti-dashboard-single">
        <section class="mbti-result-board mbti-onboarding-board">
          <div>
            <span class="mbti-kicker">온보딩 MBTI 유형</span>
            <div class="mbti-type">{{ mbtiData.onboarding.type }}</div>
            <div class="mbti-confidence">{{ mbtiData.onboarding.period }}</div>
          </div>
        </section>
        <section class="card report-panel mbti-type-description">
          <h3>온보딩 MBTI 유형 설명</h3>
          <p>{{ mbtiData.onboarding.description }}</p>
          <ol class="report-lines compact-report">
            <li v-for="line in mbtiData.onboarding.report" :key="line">{{ line }}</li>
          </ol>
        </section>
      </div>
    </template>

    <template v-else-if="mbtiViewMode === 'onboardingNext'">
      <section class="card mbti-combined-card" :class="{ 'is-preparing': isMonthlyPreparing }">
        <div v-if="isMonthlyPreparing" class="mbti-preparing-banner" role="status">
          <strong>월간 MBTI 분석을 준비하고 있어요.</strong>
          <span>대화 기반 응답이 충분히 저장되면 이 화면에서 성향 그래프와 근거 리포트를 보여드릴게요.</span>
        </div>

        <div class="mbti-combined-grid">
          <div class="mbti-type-stack">
            <article class="mbti-type-panel current">
              <span>현재 기준 MBTI</span>
              <strong class="mbti-letter-row">
                <span
                  v-for="(letter, index) in currentTypeLetters"
                  :key="letter + index"
                  class="mbti-type-letter"
                  :style="{ color: isMbtiTypeLetterChanged(letter, index) ? '#ffcf5a' : 'inherit' }"
                >{{ letter }}</span>
              </strong>
              <small>{{ mbtiData.current.monthLabel }}</small>
            </article>
            <article class="mbti-type-panel previous">
              <span>이전 기준 MBTI</span>
              <strong>{{ mbtiData.previous.type }}</strong>
              <small>{{ mbtiData.previous.monthLabel }}</small>
            </article>
          </div>

          <article class="mbti-current-graph">
            <div class="mbti-combined-head">
              <div>
                <h3>{{ isMonthlyPreparing ? 'MBTI 선호성향 그래프 준비 중' : '현재 MBTI 선호성향 그래프' }}</h3>
                <p v-if="isMonthlyPreparing">아직 확정된 월간 점수가 없어 기본 상태로 표시됩니다.</p>
              </div>
              <div class="mbti-type mbti-type-current mbti-letter-row">
                <span
                  v-for="(letter, index) in currentTypeLetters"
                  :key="'header-' + letter + index"
                  class="mbti-type-letter"
                  :style="{ color: isMbtiTypeLetterChanged(letter, index) ? '#ffcf5a' : 'inherit' }"
                >{{ letter }}</span>
              </div>
            </div>
            <div class="axis-list graph-only-list">
              <div
                class="axis-item"
                v-for="axis in mbtiData.current.axes"
                :key="axis.pair"
              >
                <div class="axis-head graph-axis-head">
                  <span class="graph-axis-label">
                    <strong>{{ axis.pair }}</strong>
                    <small>{{ axis.label }} 경향</small>
                  </span>
                  <span>{{ axis.score }}%</span>
                </div>
                <div
                  class="meter"
                  :aria-label="axis.pair + ' 중 ' + axis.label + ' 경향 ' + axis.score + '%'"
                >
                  <span :style="{ width: axis.score + '%' }"></span>
                </div>
              </div>
            </div>
          </article>

          <article class="mbti-evidence-report">
            <h3>{{ isMonthlyPreparing ? '준비 중 안내' : '근거 리포트' }}</h3>
            <ol class="report-lines compact-report">
              <li v-for="line in mbtiData.report" :key="line">{{ line }}</li>
            </ol>
          </article>
        </div>
      </section>
    </template>

    <div class="actions mbti-switch-actions" aria-label="MBTI 화면 전환">
      <button
        v-for="view in mbtiViews"
        :key="view.key"
        class="secondary-button"
        :class="{ active: mbtiViewMode === view.key }"
        type="button"
        @click="$emit('set-view', view.key)"
      >
        {{ view.buttonLabel || view.shortLabel }}
      </button>
    </div>
  </div>
</template>

<script>
export default {
  name: "MbtiPanel",
  props: {
    mbtiData: { type: Object, required: true },
    mbtiViewMode: { type: String, required: true },
    mbtiViews: { type: Array, required: true },
    currentMbtiView: { type: Object, required: true }
  },
  emits: ["refresh", "set-view"],
  computed: {
    isMonthlyPreparing() {
      return this.mbtiData.current?.type === "----";
    },
    currentTypeLetters() {
      return Array.from(this.mbtiData.current?.type || "----");
    }
  },
  methods: {
    isMbtiTypeLetterChanged(letter, index) {
      if (this.isMonthlyPreparing || letter === "-") return false;
      return this.mbtiData.previous?.type?.[index] !== letter;
    }
  }
};
</script>

<template>
  <main class="archive-page" :style="{ '--report-bg': `url(${reportBg})` }">
    <div class="archive-toolbar">
      <button
        type="button"
        class="refresh-button"
        :disabled="isLoading || isRefreshing"
        title="최신 대화로 마음 리포트 새로고침"
        @click="refreshReports"
      >
        <span class="refresh-icon" :class="{ spinning: isRefreshing }" aria-hidden="true">↻</span>
        {{ isRefreshing ? '확인 중' : '새로고침' }}
      </button>
    </div>

    <section class="archive-shell" aria-label="마음 리포트 보관함">
      <aside class="archive-sidebar">
        <section class="panel">
          <div class="panel-head">
            <p>마음 리포트 보관함</p>
            <button
              type="button"
              class="filter-toggle"
              :class="{ active: isMonthFilterOpen }"
              :aria-expanded="isMonthFilterOpen"
              @click="isMonthFilterOpen = !isMonthFilterOpen"
            >
              기간 선택
            </button>
          </div>

          <div v-if="isMonthFilterOpen" class="month-filter" aria-label="월별 리포트 필터">
            <button
              v-for="month in monthOptions"
              :key="month.value"
              type="button"
              class="month-chip"
              :class="{ active: selectedMonth === month.value }"
              :aria-pressed="selectedMonth === month.value"
              @click="selectedMonth = month.value"
            >
              <span class="month-check" aria-hidden="true"></span>
              {{ month.label }}
            </button>
          </div>

          <p v-if="!isLoading && !hasReports" class="empty-report-note">
            아직 생성된 마음 리포트가 없어요.
          </p>

          <button
            v-for="period in filteredReports"
            :key="period.id"
            type="button"
            class="period-card"
            :class="{ active: selectedReportId === period.id }"
            @click="selectedReportId = period.id"
          >
            <strong>{{ period.range }}</strong>
            <span>{{ period.type }}</span>
          </button>
        </section>

        <section class="panel emotion-panel">
          <div class="panel-head">
            <p>감정 일기</p>
          </div>
          <div v-if="currentReport" class="emotion-strip" :class="{ 'emotion-strip--monthly': currentReport.emotions.length > 7 }">
            <article
              v-for="day in currentReport.emotions"
              :key="day.day"
              class="emotion-day"
              :class="emotionToneClass(day)"
            >
              <div class="mood">{{ day.icon }}</div>
              <span>{{ day.day }}</span>
            </article>
          </div>
          <p v-else class="empty-report-note">감정 기록이 더 쌓이면 이곳에 흐름이 표시돼요.</p>
        </section>
      </aside>

      <section v-if="isLoading" class="report-card report-empty-state">
        <span class="eyebrow">마음 리포트</span>
        <h1>리포트를 확인하고 있어요</h1>
        <p>저장된 마음 리포트를 불러오는 중입니다.</p>
      </section>

      <section v-else-if="fetchError" class="report-card report-empty-state report-error-state">
        <span class="eyebrow">연결 오류</span>
        <h1>마음 리포트를 불러오지 못했어요.</h1>
        <p>{{ fetchError }}</p>
      </section>

      <section v-else-if="!currentReport" class="report-card report-empty-state">
        <span class="eyebrow">데이터 부족</span>
        <h1>아직 마음 리포트를 만들 만큼의 기록이 부족해요</h1>
        <p>
          아직 표시할 마음 리포트가 없습니다.
          대화를 나눈 뒤 새로고침하면 최신 주간/월간 마음 리포트를 확인할 수 있어요.
        </p>
        <div class="report-meta">
          <span>감정 기록 0일</span>
        </div>
      </section>

      <section v-else class="report-card">
        <header class="report-header">
          <div>
            <span class="eyebrow">{{ currentReport.range }} · {{ currentReport.type }}</span>
            <h1>{{ currentReport.title }}</h1>
            <div class="report-meta">
              <span>{{ currentReport.summary }}</span>
              <span>{{ currentReport.emotions.length }}일 감정 기록</span>
            </div>
          </div>
        </header>

        <section v-if="currentReport.is_safety_response" class="safety-notice" role="alert">
          <strong>안전 확인이 먼저 필요해요</strong>
          <p>일반 활동 추천 대신 지금 도움을 받을 수 있는 방법을 안내합니다.</p>
        </section>

        <div v-if="!currentReport.is_safety_response" class="cause-spread">
          <section class="report-section">
            <h2>스트레스 원인</h2>
            <div class="tag-row danger">
              <span v-for="item in currentReport.stressCauses" :key="item">{{ item }}</span>
              <span v-if="currentReport.stressCauses.length === 0" class="cause-empty">뚜렷한 원인이 아직 확인되지 않았어요</span>
            </div>
          </section>

          <section class="report-section">
            <h2>스트레스 이완 원인</h2>
            <div class="tag-row calm">
              <span v-for="item in currentReport.reliefCauses" :key="item">{{ item }}</span>
              <span v-if="currentReport.reliefCauses.length === 0" class="cause-empty">반복적으로 확인된 원인이 아직 없어요</span>
            </div>
          </section>
        </div>

        <section class="analysis-box">
          <p v-for="paragraph in currentReport.analysis" :key="paragraph" class="analysis-line">
            <template v-if="paragraph.includes('- 왜 추천하나요?')">
              <span class="detail-label">왜 추천하나요?</span> {{ paragraph.split('왜 추천하나요? ')[1] }}
            </template>
            <template v-else-if="paragraph.includes('- 어떻게 시작할까요?')">
              <span class="detail-label">어떻게 시작할까요?</span> {{ paragraph.split('어떻게 시작할까요? ')[1] }}
            </template>
            <template v-else>
              {{ paragraph }}
            </template>
          </p>
        </section>

        <section class="report-metric-grid" aria-label="이번 주 마음 지표">
          <article class="metric-card trend-card">
            <strong>이번 주 감정 흐름</strong>
            <div class="mini-bars" aria-hidden="true">
              <i v-for="(day, index) in currentReport.emotions.slice(0, 7)" :key="day.day" :style="{ '--metric-height': `${38 + ((index * 11) % 44)}%` }"></i>
            </div>
          </article>
          <article class="metric-card temperature-card">
            <strong>마음 평균 온도</strong>
            <p><span aria-hidden="true">☾</span><b>64점</b></p>
            <small>지난 주 대비 <em>+8 ↑</em></small>
          </article>
          <article class="metric-card emotion-card">
            <strong>가장 많이 느낀 감정</strong>
            <p><span aria-hidden="true">🙂</span><b>걱정 <small>(28%)</small></b></p>
            <small>그 다음으로 불안 (21%)</small>
          </article>
        </section>

        <footer class="report-actions">
          <p>☆ 작은 기록이 모여, 당신의 내일을 더 단단하게 만듭니다. <span>♥</span></p>
          <button type="button" class="secondary-button">이미지 저장</button>
          <button type="button" class="primary-button">공유</button>
        </footer>

        <section v-if="todayAction" class="report-action-feedback" aria-labelledby="action-feedback-title">
          <div>
            <span class="eyebrow">오늘의 나 돌아보기</span>
            <h2 id="action-feedback-title">추천 행동은 어땠나요?</h2>
            <p><strong>{{ todayAction.title }}</strong>을(를) 해본 뒤, 감정 완화에 도움이 된 정도를 남겨주세요.</p>
          </div>
          <div class="report-action-score-row">
            <button
              v-for="option in feedbackOptions"
              :key="option.value"
              type="button"
              class="report-action-score"
              :class="{ active: actionFeedbackValue === option.value }"
              :aria-pressed="actionFeedbackValue === option.value"
              @click="actionFeedbackValue = option.value"
            >
              <strong>{{ option.value }}</strong>
              <span>{{ option.label }}</span>
            </button>
          </div>
          <div class="report-action-feedback-footer">
            <span v-if="actionFeedbackMessage" class="report-action-feedback-message">{{ actionFeedbackMessage }}</span>
            <button type="button" class="primary-button" :disabled="isFeedbackSaving || !actionFeedbackValue" @click="saveActionFeedback">
              {{ isFeedbackSaving ? '저장 중…' : '평가 저장' }}
            </button>
          </div>
        </section>
      </section>
    </section>
  </main>
</template>

<script setup>
import { computed, ref, watch, onMounted } from 'vue'
import { reportApi } from '../../api/report.js'
import reportBg from '../../assets/report-bg.png'

const reports = ref([])
const todayCheckin = ref(null)
const actionFeedbackValue = ref(null)
const actionFeedbackMessage = ref('')
const isFeedbackSaving = ref(false)
const feedbackOptions = [
  { value: 1, label: '별로 도움 안 됨' },
  { value: 2, label: '조금 아쉬움' },
  { value: 3, label: '보통' },
  { value: 4, label: '도움 됨' },
  { value: 5, label: '완전 도움 됨' },
]

const isLoading = ref(true)
const isRefreshing = ref(false)
const fetchError = ref('')

const normalizeReport = (report) => ({
  ...report,
  stressCauses: Array.isArray(report?.stressCauses) ? report.stressCauses : [],
  reliefCauses: Array.isArray(report?.reliefCauses) ? report.reliefCauses : [],
  emotions: Array.isArray(report?.emotions) ? report.emotions : [],
  analysis: Array.isArray(report?.analysis) ? report.analysis : [],
  recommendations: Array.isArray(report?.recommendations) ? report.recommendations : [],
  is_fallback: Boolean(report?.is_fallback),
  is_safety_response: Boolean(report?.is_safety_response),
})

const getReportStartDate = (report) => {
  if (!report || !report.range) return new Date()
  const dateStr = report.range.split(' ~ ')[0].replace(' 생성', '').replaceAll('.', '-')
  return new Date(dateStr)
}
const getReportMonth = (report) => {
  if (!report || !report.range) return ''
  return report.range.slice(0, 7)
}
const formatMonthLabel = (month) => {
  const [year, value] = month.split('.')
  return `${year}년 ${Number(value)}월`
}

const hasReports = computed(() => reports.value.length > 0)
const reportsByNewest = computed(() => [...reports.value].sort((a, b) => getReportStartDate(b) - getReportStartDate(a)))
const latestMonth = computed(() => getReportMonth(reportsByNewest.value[0]))
const isMonthFilterOpen = ref(false)
const selectedMonth = ref(latestMonth.value)
const selectedReportId = ref(reportsByNewest.value[0]?.id)

const monthOptions = computed(() => {
  const months = [...new Set(reportsByNewest.value.map(getReportMonth))]
  return months.map((month) => ({
    value: month,
    label: formatMonthLabel(month),
  }))
})

const filteredReports = computed(() => (
  reportsByNewest.value.filter((report) => getReportMonth(report) === selectedMonth.value)
))

const currentReport = computed(
  () => filteredReports.value.find((report) => report.id === selectedReportId.value) ?? filteredReports.value[0],
)
const todayAction = computed(() => todayCheckin.value?.selected_action ?? null)

watch(selectedMonth, () => {
  selectedReportId.value = filteredReports.value[0]?.id
})

watch(latestMonth, (newMonth) => {
  if (newMonth) {
    selectedMonth.value = newMonth
  }
})

const applyReports = (data) => {
  reports.value = Array.isArray(data?.reports) ? data.reports.map(normalizeReport) : []
  const firstReport = reportsByNewest.value[0]
  if (firstReport) {
    selectedMonth.value = getReportMonth(firstReport)
    selectedReportId.value = firstReport.id
  }
}

const loadReports = async () => {
  try {
    fetchError.value = ''
    applyReports(await reportApi.getReports())
  } catch (error) {
    fetchError.value = error?.message ?? '마음 리포트를 불러오지 못했습니다.'
    console.error('Failed to fetch stored reports:', error)
  } finally {
    isLoading.value = false
  }
}

const refreshReports = async () => {
  try {
    isRefreshing.value = true
    fetchError.value = ''
    applyReports(await reportApi.refreshReports())
  } catch (error) {
    fetchError.value = error?.message ?? '마음 리포트를 새로고침하지 못했습니다.'
    console.error('Failed to refresh reports:', error)
  } finally {
    isRefreshing.value = false
  }
}

const loadTodayCheckin = async () => {
  try {
    const data = await reportApi.getTodayCheckin()
    todayCheckin.value = data?.checkin ?? null
    actionFeedbackValue.value = data?.action_feedback?.helpfulness ?? null
  } catch (error) {
    // 리포트 본문은 오늘의 나 기록이 없어도 계속 표시합니다.
    console.warn('Failed to fetch today check-in:', error)
  }
}

onMounted(() => {
  loadReports()
  loadTodayCheckin()
})

async function saveActionFeedback() {
  if (!todayCheckin.value?.id || !todayAction.value?.id || !actionFeedbackValue.value || isFeedbackSaving.value) return
  isFeedbackSaving.value = true
  actionFeedbackMessage.value = ''
  try {
    await reportApi.saveActionFeedback(todayCheckin.value.id, todayAction.value.id, actionFeedbackValue.value)
    actionFeedbackMessage.value = '평가를 저장했어요. 다음 행동 추천에 참고할게요.'
  } catch (error) {
    actionFeedbackMessage.value = error?.response?.data?.error?.message ?? '평가를 저장하지 못했어요. 잠시 후 다시 시도해주세요.'
  } finally {
    isFeedbackSaving.value = false
  }
}

const emotionToneClass = (day) => {
  if (['😣', '😔'].includes(day.icon)) return 'emotion-day--very-low'
  if (['😮‍💨', '😳'].includes(day.icon)) return 'emotion-day--low'
  if (['😄', '😊'].includes(day.icon)) return 'emotion-day--very-good'
  if (['🙂', '😌', '🥲'].includes(day.icon)) return 'emotion-day--good'
  return 'emotion-day--neutral'
}
</script>


<style scoped>
button {
  font: inherit;
  cursor: pointer;
}

.archive-page {
  min-height: calc(100vh - 54px);
  padding: 40px 28px 84px;
  overflow: hidden auto;
  background-image: var(--report-bg);
  background-position: center;
  background-size: cover;
  background-attachment: fixed;
  font-family: var(--font-ui);
}

.archive-toolbar {
  display: flex;
  justify-content: flex-end;
  width: min(1080px, 100%);
  margin: 0 auto 12px;
}

.refresh-button {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 7px;
  min-height: 38px;
  padding: 8px 14px;
  border: 1px solid rgba(255, 255, 255, 0.28);
  border-radius: 6px;
  background: rgba(22, 10, 48, 0.64);
  color: #fff8ff;
  box-shadow: 0 8px 24px rgba(8, 3, 20, 0.2);
}

.refresh-button:disabled {
  cursor: wait;
  opacity: 0.58;
}

.refresh-icon {
  display: inline-block;
  line-height: 1;
}

.refresh-icon.spinning {
  animation: refresh-spin 0.8s linear infinite;
}

@keyframes refresh-spin {
  to {
    transform: rotate(360deg);
  }
}

.refresh-button:hover:not(:disabled) {
  border-color: rgba(244, 175, 170, 0.8);
  background: rgba(49, 23, 77, 0.84);
  transform: translateY(-1px);
}

.archive-shell {
  position: relative;
  display: grid;
  grid-template-columns: 270px minmax(0, 1fr);
  gap: 0;
  width: min(1080px, 100%);
  min-height: 650px;
  margin: 0 auto;
  padding: 0;
  border: 0;
  border-radius: 8px;
  background: transparent;
  box-shadow: 0 26px 64px rgba(5, 2, 14, 0.45);
  backdrop-filter: none;
  -webkit-backdrop-filter: none;
}

.archive-sidebar {
  position: relative;
  z-index: 1;
  display: block;
  min-width: 0;
  padding: 34px 24px 38px;
  overflow: hidden;
  border: 1px solid rgba(255, 255, 255, 0.16);
  border-right: 0;
  border-radius: 8px 0 0 8px;
  background: rgba(43, 20, 67, 0.96);
  color: #fff9ff;
}

.archive-sidebar::after {
  content: '';
  position: absolute;
  inset: 0 0 0 auto;
  width: 12px;
  pointer-events: none;
  background: linear-gradient(90deg, transparent, rgba(5, 2, 14, 0.48));
}

.panel,
.report-card {
  backdrop-filter: none;
  -webkit-backdrop-filter: none;
}

.panel {
  padding: 0;
  border: 0;
  border-radius: 0;
  background: transparent;
  box-shadow: none;
}

.panel + .panel {
  margin-top: 34px;
  padding-top: 28px;
  border-top: 1px dashed rgba(255, 255, 255, 0.28);
}

.panel-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 18px;
}

.panel-head p,
.report-section h2 {
  margin: 0;
  letter-spacing: 0;
}

.panel-head p {
  font-family: var(--font-soft);
  font-size: 18px;
  font-weight: 700;
}

.panel-head span,
.eyebrow {
  display: block;
  margin-top: 3px;
  color: var(--text-muted);
  font-size: 12px;
}

.empty-report-note {
  margin: 0;
  color: var(--text-muted);
  font-size: 13px;
  line-height: 1.6;
}

.period-card {
  display: grid;
  width: 100%;
  gap: 5px;
  min-height: 58px;
  margin-top: 8px;
  padding: 11px 12px;
  border: 1px solid rgba(255, 255, 255, 0.14);
  border-radius: 8px;
  background: rgba(255, 255, 255, 0.07);
  color: var(--text-secondary);
  text-align: left;
  transition: border-color 0.18s ease, background 0.18s ease, transform 0.18s ease;
}

.period-card:hover,
.period-card.active {
  transform: translateY(-1px);
  border-color: rgba(255, 179, 71, 0.58);
  background: linear-gradient(135deg, rgba(255, 179, 71, 0.16), rgba(94, 234, 212, 0.09));
  color: var(--text-primary);
}

.period-card strong {
  color: #BFF8EF;
  font-size: 13px;
}

.period-card span {
  font-size: 12px;
  color: #fff9ff;
  white-space: nowrap;
}

.filter-toggle {
  padding: 6px 9px;
  border: 0;
  border-bottom: 1px solid rgba(255, 255, 255, 0.38);
  border-radius: 0;
  background: transparent;
  color: #e8dfee;
  white-space: nowrap;
}

.filter-toggle:hover,
.filter-toggle.active {
  border-color: #f2aaa8;
  background: transparent;
  color: #ffd6d3;
}

.month-filter {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin: 0 0 18px;
  padding: 0 0 14px;
  border-bottom: 1px solid rgba(255, 255, 255, 0.12);
}

.month-chip {
  display: inline-flex;
  align-items: center;
  gap: 7px;
  padding: 7px 9px;
  border-color: rgba(255, 255, 255, 0.16);
  border-radius: 6px;
  background: rgba(255, 255, 255, 0.05);
  color: #e8dfee;
}

.month-check {
  width: 12px;
  height: 12px;
  border: 1px solid rgba(255, 255, 255, 0.35);
  border-radius: 3px;
}

.month-chip:hover,
.month-chip.active {
  border-color: rgba(242, 170, 168, 0.72);
  background: rgba(242, 170, 168, 0.12);
  color: #fff7f6;
}

.month-chip.active .month-check {
  border-color: #f2aaa8;
  background: #f2aaa8;
  box-shadow: inset 0 0 0 2px #3d214e;
}

.period-card {
  display: block;
  position: relative;
  width: 100%;
  margin: 0;
  padding: 13px 10px 13px 20px;
  border: 0;
  border-bottom: 1px solid rgba(255, 255, 255, 0.1);
  border-radius: 0;
  background: transparent;
  color: #f4ecf7;
  text-align: left;
}

.period-card::before {
  content: '';
  position: absolute;
  top: 12px;
  bottom: 12px;
  left: 3px;
  width: 3px;
  border-radius: 3px;
  background: transparent;
}

.period-card:hover,
.period-card.active {
  border-color: rgba(255, 255, 255, 0.16);
  background: rgba(255, 255, 255, 0.06);
  transform: none;
}

.period-card.active::before {
  background: #f2aaa8;
}

.period-card strong {
  display: block;
  font-size: 14px;
  color: #fffaff;
}

.period-card span {
  display: block;
  margin-top: 4px;
  font-size: 12px;
  color: #c9bcd2;
}

.empty-report-note {
  color: #cfc3d7;
}

.emotion-strip {
  display: grid;
  grid-template-columns: repeat(7, minmax(34px, 1fr));
  gap: 7px;
}

.emotion-strip--monthly {
  grid-template-columns: repeat(5, minmax(38px, 1fr));
}

.emotion-day {
  display: flex;
  align-items: center;
  justify-content: center;
  flex-direction: column;
  min-width: 0;
  padding: 8px 4px 7px;
  border: 1px solid rgba(0, 0, 0, 0.72);
  border-radius: 6px;
  background: rgba(77, 82, 96, 0.42);
}

.emotion-day--very-low {
  border-color: rgba(0, 0, 0, 0.78);
  background: linear-gradient(180deg, rgba(255, 73, 105, 0.78), rgba(122, 20, 45, 0.74));
  box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.14), 0 8px 16px rgba(255, 58, 90, 0.2);
}

.emotion-day--low {
  border-color: rgba(0, 0, 0, 0.78);
  background: linear-gradient(180deg, rgba(255, 114, 134, 0.48), rgba(112, 44, 62, 0.5));
  box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.12);
}

.emotion-day--neutral {
  border-color: rgba(0, 0, 0, 0.78);
  background: linear-gradient(180deg, rgba(170, 177, 190, 0.34), rgba(77, 82, 96, 0.42));
  box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.1);
}

.emotion-day--good {
  border-color: rgba(0, 0, 0, 0.78);
  background: linear-gradient(180deg, rgba(76, 221, 155, 0.46), rgba(26, 108, 83, 0.48));
  box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.12);
}

.emotion-day--very-good {
  border-color: rgba(0, 0, 0, 0.78);
  background: linear-gradient(180deg, rgba(76, 255, 168, 0.76), rgba(12, 132, 91, 0.72));
  box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.15), 0 8px 16px rgba(52, 211, 153, 0.18);
}

.mood {
  font-size: 24px;
}

.emotion-day span {
  margin-top: 3px;
  font-size: 11px;
  color: rgba(255, 255, 255, 0.82);
}

.report-card {
  position: relative;
  min-width: 0;
  min-height: 650px;
  padding: 44px 48px 36px 58px;
  overflow: hidden;
  border: 1px solid rgba(231, 62, 101, 0.24);
  border-radius: 0 8px 8px 0;
  background: linear-gradient(180deg, rgba(226, 213, 184, 0.97), rgba(211, 193, 158, 0.98));
  box-shadow: none;
  color: #3b2c3f;
  font-family: var(--font-soft);
}

.report-card::before {
  content: '';
  position: absolute;
  top: 0;
  bottom: 0;
  left: 24px;
  width: 1px;
  background: rgba(100, 70, 89, 0.2);
  box-shadow: 5px 0 16px rgba(54, 31, 63, 0.12);
}

.report-card::after {
  content: '';
  position: absolute;
  inset: 0;
  pointer-events: none;
  opacity: 0.18;
  background-image: radial-gradient(rgba(75, 56, 83, 0.18) 0.55px, transparent 0.65px);
  background-size: 8px 8px;
}

.report-card > * {
  position: relative;
  z-index: 1;
}

.report-empty-state {
  display: grid;
  align-content: center;
  min-height: 380px;
}

.report-empty-state h1 {
  margin: 8px 0 0;
  color: var(--text-primary);
  font-size: 26px;
  line-height: 1.35;
}

.report-empty-state p {
  max-width: 620px;
  margin: 14px 0 0;
  color: rgba(255, 255, 255, 0.78);
  font-size: 15px;
  line-height: 1.8;
}

.report-header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 24px;
  margin: 0 0 34px;
  padding: 0 0 28px;
  border-bottom: 1px solid rgba(91, 63, 101, 0.2);
}

.eyebrow {
  display: inline-block;
  padding: 5px 9px;
  border: 1px solid rgba(142, 76, 96, 0.36);
  border-radius: 4px;
  background: rgba(181, 91, 111, 0.13);
  color: #76475a;
  font-family: var(--font-ui);
  font-size: 12px;
  font-weight: 700;
  letter-spacing: 0;
}

.report-header h1,
.report-empty-state h1 {
  margin: 14px 0 13px;
  color: #38273f;
  font-family: var(--font-soft);
  font-size: clamp(25px, 2.5vw, 32px);
  line-height: 1.35;
  letter-spacing: 0;
}

.report-meta {
  display: flex;
  align-items: flex-end;
  justify-content: space-between;
  gap: 22px;
}

.report-meta span {
  padding: 0;
  border: 0;
  border-radius: 0;
  background: transparent;
  color: #66586a;
}

.report-meta span:first-child {
  max-width: 720px;
  font-size: 16px;
  line-height: 1.75;
}

.report-meta span:last-child {
  flex: 0 0 auto;
  padding-bottom: 3px;
  border-bottom: 2px solid rgba(163, 103, 74, 0.46);
  color: #76543f;
  font-family: var(--font-ui);
  font-size: 12px;
  font-weight: 700;
}

.cause-spread {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  margin: 0 0 34px;
  padding: 22px 0 26px;
  border-bottom: 1px solid rgba(91, 63, 101, 0.18);
}

.report-section {
  margin: 0;
  padding: 0 30px 0 0;
  border: 0;
}

.report-section + .report-section {
  padding: 0 0 0 30px;
  border-left: 1px dashed rgba(91, 63, 101, 0.24);
}

.report-section h2 {
  margin-bottom: 15px;
  color: #49364f;
  font-family: var(--font-soft);
  font-size: 16px;
  font-weight: 700;
}

.tag-row {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.tag-row span {
  padding: 7px 11px;
  border-radius: 5px;
  font-family: var(--font-ui);
  font-size: 13px;
  font-weight: 650;
}

.tag-row.danger span {
  border: 1px solid rgba(173, 78, 87, 0.3);
  background: rgba(190, 91, 98, 0.12);
  color: #87434e;
}

.tag-row.calm span {
  border: 1px solid rgba(57, 121, 102, 0.3);
  background: rgba(70, 139, 116, 0.11);
  color: #376b5d;
}

.tag-row .cause-empty {
  border: 0;
  background: transparent;
  color: #7c707d;
  font-weight: 500;
}

.analysis-box {
  margin: 0;
  padding: 4px 8px 10px;
  border: 0;
  border-radius: 0;
  background: repeating-linear-gradient(
    to bottom,
    transparent 0,
    transparent 31px,
    rgba(100, 115, 135, 0.17) 32px
  );
  box-shadow: none;
}

.analysis-box p {
  min-height: 32px;
  margin: 0 0 18px;
  color: #493f4d;
  font-size: 15px;
  line-height: 2.13;
}

.detail-label {
  display: inline;
  margin-right: 5px;
  padding: 2px 6px;
  border: 0;
  border-radius: 4px;
  background: rgba(128, 93, 143, 0.14);
  color: #654774;
  font-family: var(--font-ui);
  font-size: 13px;
}

.safety-notice {
  margin-bottom: 28px;
  padding: 16px 18px;
  border-color: rgba(180, 72, 85, 0.35);
  border-radius: 6px;
  background: rgba(225, 140, 148, 0.13);
  color: #773c47;
}

.safety-notice strong,
.safety-notice p {
  color: inherit;
}

.safety-notice p {
  margin: 7px 0 0;
}

.report-empty-state {
  display: flex;
  align-items: flex-start;
  justify-content: center;
  flex-direction: column;
  color: #5c4f62;
}

.report-empty-state p {
  max-width: 620px;
  color: #6c6071;
  line-height: 1.75;
}

.report-error-state {
  border-color: rgba(195, 92, 103, 0.35);
}

.report-actions {
  display: flex;
  align-items: center;
  justify-content: flex-end;
  gap: 10px;
  margin-top: 30px;
  padding-top: 22px;
  border-top: 1px solid rgba(91, 63, 101, 0.18);
}

.primary-button,
.secondary-button {
  min-height: 40px;
  padding: 9px 16px;
  border-radius: 6px;
  font-family: var(--font-ui);
}

.primary-button {
  border: 1px solid #e73e65;
  background: linear-gradient(135deg, #e73e65, #ee5d5f);
  color: #fffaff;
}

.secondary-button {
  border: 1px solid rgba(76, 91, 87, 0.48);
  background: transparent;
  color: #425f58;
}

.report-action-feedback {
  display: grid;
  gap: 16px;
  margin-top: 26px;
  padding: 20px;
  border: 1px solid rgba(255, 180, 140, 0.28);
  border-radius: 14px;
  background: linear-gradient(135deg, rgba(255, 164, 116, 0.1), rgba(94, 234, 212, 0.06));
}

.report-action-feedback h2 {
  margin: 4px 0 6px;
  color: #fff7ee;
  font-size: 18px;
}

.report-action-feedback p {
  margin: 0;
  color: rgba(255, 245, 238, 0.72);
  font-size: 13px;
  line-height: 1.6;
}

.report-action-feedback p strong {
  color: #ffd39d;
}

.report-action-score-row {
  display: grid;
  grid-template-columns: repeat(5, minmax(0, 1fr));
  gap: 8px;
}

.report-action-score {
  display: grid;
  justify-items: center;
  gap: 5px;
  min-height: 62px;
  padding: 9px 6px;
  border: 1px solid rgba(255, 190, 151, 0.32);
  border-radius: 12px;
  color: rgba(255, 236, 224, 0.75);
  background: rgba(255, 255, 255, 0.06);
  cursor: pointer;
  transition: 0.18s ease;
}

.report-action-score strong {
  color: #fff2dc;
  font-size: 18px;
}

.report-action-score span {
  font-size: 10px;
  text-align: center;
  white-space: nowrap;
}

.report-action-score:hover,
.report-action-score.active {
  border-color: rgba(255, 211, 157, 0.8);
  background: linear-gradient(135deg, rgba(231, 62, 101, 0.72), rgba(231, 126, 110, 0.64));
  color: #fff;
  transform: translateY(-1px);
}

.report-action-feedback-footer {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}

.report-action-feedback-message {
  color: #bff8ef;
  font-size: 12px;
  font-weight: 800;
}

.report-action-feedback button:disabled {
  cursor: not-allowed;
  opacity: 0.55;
}

.primary-button:hover,
.secondary-button:hover {
  transform: translateY(-1px);
}

@media (max-width: 980px) {
  .archive-page {
    padding: 22px 18px 44px;
  }

  .archive-shell {
    grid-template-columns: 250px minmax(0, 1fr);
  }

  .archive-sidebar {
    padding: 32px 22px 38px;
  }

  .report-card {
    padding: 40px 32px 34px 44px;
  }

  .cause-spread {
    grid-template-columns: 1fr;
    gap: 24px;
  }

  .report-section,
  .report-section + .report-section {
    padding: 0;
    border-left: 0;
  }

  .report-section + .report-section {
    padding-top: 24px;
    border-top: 1px dashed rgba(91, 63, 101, 0.24);
  }
}

@media (max-width: 720px) {
  .archive-page {
    padding: 70px 12px 36px;
    background-attachment: scroll;
  }

  .archive-toolbar {
    margin-bottom: 10px;
  }

  .archive-shell {
    grid-template-columns: 1fr;
    min-height: 0;
    border-radius: 8px;
  }

  .archive-sidebar {
    padding: 28px 20px 30px;
    border-right: 1px solid rgba(255, 255, 255, 0.16);
    border-bottom: 0;
    border-radius: 8px 8px 0 0;
  }

  .archive-sidebar::after {
    inset: auto 0 0;
    width: auto;
    height: 12px;
    background: linear-gradient(180deg, transparent, rgba(5, 2, 14, 0.3));
  }

  .emotion-strip--monthly {
    grid-template-columns: repeat(5, minmax(36px, 1fr));
  }

  .report-card {
    min-height: 520px;
    padding: 38px 22px 28px 28px;
    border-radius: 0 0 8px 8px;
  }

  .report-card::before {
    left: 13px;
  }

  .report-header {
    margin-bottom: 24px;
    padding-bottom: 22px;
  }

  .report-header h1,
  .report-empty-state h1 {
    font-size: 25px;
  }

  .report-meta {
    align-items: flex-start;
    flex-direction: column;
    gap: 12px;
  }

  .report-meta span:first-child {
    font-size: 15px;
  }

  .cause-spread {
    margin-bottom: 26px;
  }

  .analysis-box {
    padding-right: 0;
    padding-left: 0;
  }

  .analysis-box p {
    font-size: 14px;
  }

  .report-actions {
    justify-content: stretch;
  }

  .report-actions button {
    flex: 1;
    min-width: 0;
  }

  .report-action-score-row {
    gap: 5px;
  }

  .report-action-score span {
    font-size: 9px;
  }

  .report-action-feedback-footer {
    align-items: stretch;
    flex-direction: column;
  }
}
</style>

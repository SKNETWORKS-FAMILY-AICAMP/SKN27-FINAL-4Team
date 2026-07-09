<template>
  <main class="archive-page">
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
        <p>대화 기록을 살펴보고 데이터가 충분한지 판단하는 중입니다.</p>
      </section>

      <section v-else-if="!currentReport" class="report-card report-empty-state">
        <span class="eyebrow">데이터 부족</span>
        <h1>아직 마음 리포트를 만들 만큼의 기록이 부족해요</h1>
        <p>
          아직 표시할 마음 리포트가 없습니다.
          대화를 조금 더 나누면 주간/월간 마음 리포트가 생성돼요.
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

        <section class="report-section">
          <h2>스트레스 주요 원인.</h2>
          <div class="tag-row danger">
            <span v-for="item in currentReport.stressCauses" :key="item">{{ item }}</span>
          </div>
        </section>

        <section class="report-section">
          <h2>스트레스 이완 주요 원인</h2>
          <div class="tag-row calm">
            <span v-for="item in currentReport.reliefCauses" :key="item">{{ item }}</span>
          </div>
        </section>

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

        <footer class="report-actions">
          <button type="button" class="secondary-button">이미지 저장</button>
          <button type="button" class="primary-button">공유</button>
        </footer>
      </section>
    </section>
  </main>
</template>

<script setup>
import { computed, ref, watch, onMounted } from 'vue'
import { reportApi } from '../../api/report.js'
import reportBg from '../../assets/report-bg.png'

const reports = ref([])

const isLoading = ref(true)
const fetchError = ref('')

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

watch(selectedMonth, () => {
  selectedReportId.value = filteredReports.value[0]?.id
})

watch(latestMonth, (newMonth) => {
  if (newMonth) {
    selectedMonth.value = newMonth
  }
})

onMounted(async () => {
  try {
    const data = await reportApi.generateReport()
    if (data && data.reports && data.reports.length > 0) {
      reports.value = data.reports
      // 기본적으로 가장 첫 번째 리포트를 선택
      const firstReport = reportsByNewest.value[0]
      if (firstReport) {
        selectedMonth.value = getReportMonth(firstReport)
        selectedReportId.value = firstReport.id
      }
    }
  } catch (error) {
    fetchError.value = error?.message ?? 'Failed to fetch generated report'
    console.error('Failed to fetch generated report:', error)
  } finally {
    isLoading.value = false
  }
})

const emotionToneClass = (day) => {
  if (['😣', '😔'].includes(day.icon)) return 'emotion-day--very-low'
  if (['😮‍💨', '😳'].includes(day.icon)) return 'emotion-day--low'
  if (['😄', '😊'].includes(day.icon)) return 'emotion-day--very-good'
  if (['🙂', '😌', '🥲'].includes(day.icon)) return 'emotion-day--good'
  return 'emotion-day--neutral'
}
</script>

<style scoped>
.archive-page {
  position: relative;
  isolation: isolate;
  min-height: calc(100vh - 54px);
  padding: 34px 28px;
  overflow: hidden auto;
  background: transparent;
}

.archive-shell {
  display: grid;
  grid-template-columns: minmax(300px, 360px) minmax(0, 1fr);
  gap: 20px;
  width: min(1480px, 100%);
  margin: 0 auto;
  padding: 20px;
  border: 1px solid rgba(255, 255, 255, 0.12);
  border-radius: 8px;
  background: rgba(13, 5, 32, 0.18);
  box-shadow: 0 28px 80px rgba(0, 0, 0, 0.28);
  backdrop-filter: blur(10px);
  -webkit-backdrop-filter: blur(10px);
}

.archive-sidebar {
  display: grid;
  align-content: start;
  gap: 16px;
}

.panel,
.report-card {
  border: 1px solid rgba(255, 255, 255, 0.15);
  border-radius: 8px;
  background: linear-gradient(180deg, rgba(31, 13, 76, 0.56), rgba(18, 8, 46, 0.42));
  box-shadow: 0 18px 42px rgba(0, 0, 0, 0.24);
  backdrop-filter: blur(18px);
  -webkit-backdrop-filter: blur(18px);
}

.panel {
  padding: 16px;
}

.panel-head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 14px;
}

.panel-head p,
.report-section h2 {
  margin: 0;
  color: var(--text-primary);
  font-size: 15px;
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
}

.filter-toggle {
  min-height: 31px;
  padding: 0 10px;
  border: 1px solid rgba(255, 255, 255, 0.16);
  border-radius: 8px;
  background: rgba(255, 255, 255, 0.07);
  color: var(--text-muted);
  font-size: 12px;
  font-weight: 800;
  transition: border-color 0.18s ease, background 0.18s ease, color 0.18s ease;
}

.filter-toggle:hover,
.filter-toggle.active {
  border-color: rgba(94, 234, 212, 0.5);
  background: rgba(94, 234, 212, 0.12);
  color: #BFF8EF;
}

.month-filter {
  display: grid;
  gap: 7px;
  max-height: 128px;
  overflow-y: auto;
  overscroll-behavior: contain;
  margin-bottom: 10px;
  padding: 8px;
  border: 1px solid rgba(255, 255, 255, 0.13);
  border-radius: 8px;
  background: rgba(8, 3, 25, 0.22);
  scrollbar-width: thin;
  scrollbar-color: rgba(94, 234, 212, 0.48) rgba(255, 255, 255, 0.06);
}

.month-filter::-webkit-scrollbar {
  width: 7px;
}

.month-filter::-webkit-scrollbar-track {
  border-radius: 999px;
  background: rgba(255, 255, 255, 0.06);
}

.month-filter::-webkit-scrollbar-thumb {
  border-radius: 999px;
  background: rgba(94, 234, 212, 0.48);
}

.month-chip {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  min-height: 31px;
  padding: 0 10px;
  border: 1px solid rgba(255, 255, 255, 0.16);
  border-radius: 8px;
  background: rgba(255, 255, 255, 0.07);
  color: var(--text-muted);
  font-size: 12px;
  font-weight: 800;
  transition: border-color 0.18s ease, background 0.18s ease, color 0.18s ease;
}

.month-check {
  width: 12px;
  height: 12px;
  border: 1px solid rgba(255, 255, 255, 0.34);
  border-radius: 4px;
  background: rgba(255, 255, 255, 0.05);
}

.month-chip:hover,
.month-chip.active {
  border-color: rgba(94, 234, 212, 0.5);
  background: rgba(94, 234, 212, 0.12);
  color: #BFF8EF;
}

.month-chip.active .month-check {
  border-color: rgba(94, 234, 212, 0.85);
  background: linear-gradient(135deg, rgba(94, 234, 212, 0.95), rgba(191, 248, 239, 0.85));
  box-shadow: 0 0 8px rgba(94, 234, 212, 0.38);
}

.emotion-strip {
  display: grid;
  grid-template-columns: repeat(7, minmax(34px, 1fr));
  gap: 7px;
  overflow: visible;
  padding-bottom: 4px;
}

.emotion-strip--monthly {
  grid-template-columns: repeat(6, minmax(34px, 1fr));
}

.emotion-day {
  display: grid;
  justify-items: center;
  gap: 4px;
  min-width: 0;
  padding: 7px 3px;
  border: 1px solid rgba(0, 0, 0, 0.72);
  border-radius: 8px;
  background: rgba(255, 255, 255, 0.08);
  transition: background 0.18s ease, box-shadow 0.18s ease, transform 0.18s ease;
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
  display: grid;
  place-items: center;
  width: 28px;
  height: 28px;
  border-radius: 50%;
  background: rgba(255, 179, 71, 0.22);
  font-size: 16px;
}

.emotion-day span {
  color: var(--text-muted);
  font-size: 11px;
}

.report-card {
  padding: 24px;
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
  padding-bottom: 18px;
  border-bottom: 1px solid rgba(255, 255, 255, 0.14);
}

.report-header h1 {
  margin: 5px 0 0;
  color: var(--text-primary);
  font-size: 26px;
  line-height: 1.28;
  letter-spacing: 0;
}

.report-meta {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-top: 12px;
}

.report-meta span {
  display: inline-flex;
  align-items: center;
  min-height: 28px;
  padding: 4px 10px;
  border: 1px solid rgba(255, 179, 71, 0.26);
  border-radius: 999px;
  background: rgba(255, 179, 71, 0.1);
  color: rgba(255, 241, 214, 0.9);
  font-size: 12px;
  font-weight: 700;
}

.report-section {
  margin-top: 18px;
}

.tag-row {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-top: 10px;
}

.tag-row span {
  display: inline-flex;
  align-items: center;
  min-height: 30px;
  padding: 4px 11px;
  border-radius: 999px;
  font-size: 13px;
  font-weight: 700;
}

.tag-row.danger span {
  border: 1px solid rgba(252, 165, 165, 0.42);
  background: rgba(248, 113, 113, 0.12);
  color: #FCA5A5;
}

.tag-row.calm span {
  border: 1px solid rgba(94, 234, 212, 0.42);
  background: rgba(94, 234, 212, 0.12);
  color: #A7F3E9;
}

.analysis-box {
  display: grid;
  gap: 14px;
  margin-top: 20px;
  padding: 20px;
  border: 1px solid rgba(255, 255, 255, 0.15);
  border-radius: 8px;
  background: rgba(13, 5, 32, 0.28);
  backdrop-filter: blur(10px);
  -webkit-backdrop-filter: blur(10px);
}

.analysis-box p {
  margin: 0;
  color: rgba(255, 255, 255, 0.82);
  font-size: 14.5px;
  line-height: 1.86;
}

.detail-label {
  display: inline-block;
  background: rgba(0, 0, 0, 0.35); /* 어두운 계열의 라벨 배경 */
  padding: 3px 8px;
  margin-right: 6px;
  border-radius: 4px;
  font-size: 12px;
  font-weight: 700;
  color: #BFF8EF; /* 민트 계열 텍스트 포인트 */
  border: 1px solid rgba(255, 255, 255, 0.1);
  vertical-align: middle;
}

.report-actions {
  display: flex;
  justify-content: flex-end;
  gap: 10px;
  margin-top: 16px;
}

.primary-button,
.secondary-button {
  min-height: 38px;
  padding: 0 17px;
  border-radius: 8px;
  font-size: 14px;
  font-weight: 800;
}

.primary-button {
  background: linear-gradient(135deg, var(--accent-orange), var(--accent-gold));
  color: #1A0A00;
}

.secondary-button {
  border: 1px solid rgba(94, 234, 212, 0.56);
  background: rgba(94, 234, 212, 0.08);
  color: #BFF8EF;
}

@media (max-width: 760px) {
  .archive-page {
    padding: 20px 12px;
  }

  .archive-shell {
    grid-template-columns: 1fr;
    padding: 12px;
  }

  .emotion-strip--monthly {
    grid-template-columns: repeat(5, minmax(34px, 1fr));
  }

  .report-card {
    padding: 16px;
  }

  .report-header h1 {
    font-size: 20px;
  }

  .report-actions {
    justify-content: stretch;
  }

  .report-actions button {
    flex: 1;
  }
}
</style>

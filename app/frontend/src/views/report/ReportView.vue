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
          <div class="emotion-strip" :class="{ 'emotion-strip--monthly': currentReport.emotions.length > 7 }">
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
        </section>
      </aside>

      <section class="report-card">
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

        <section class="report-section" v-if="!currentReport.is_fallback">
          <h2>스트레스 주요 원인.</h2>
          <div class="tag-row danger">
            <span v-for="item in currentReport.stressCauses" :key="item">{{ item }}</span>
          </div>
        </section>

        <section class="report-section" v-if="!currentReport.is_fallback">
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

const monthlyEmotionIcons = [
  '🙂', '🥹', '😣', '😐', '😳', '😄', '😌', '😮‍💨', '🙂', '😣',
  '😐', '😊', '😌', '😄', '🥲', '😳', '🙂', '😔', '😐', '😌',
  '😄', '😊', '😣', '😮‍💨', '🙂', '😌', '😄', '😊', '🙂', '😌',
]

const monthlyEmotions = monthlyEmotionIcons.map((icon, index) => ({
  day: `${index + 1}일`,
  icon,
}))

const reports = ref([
  {
    id: 'monthly-202605',
    type: '월간',
    range: '2026.05.01 ~ 2026.05.31',
    title: '2026년 5월 월간 마음 리포트',
    summary: '관계 피로와 프로젝트 긴장이 함께 오른 달',
    stressCauses: ['대학교 친구', '프로젝트 경험', '부모님의 잔소리'],
    reliefCauses: ['포켓몬', '네이버웹툰', '절친'],
    emotions: monthlyEmotions,
    analysis: [
      '최근 감정의 변동은 프로젝트로 인한 학업적 긴장감과 대학교 친구 및 부모님의 잔소리에서 비롯된 관계적 피로도가 겹칠 때 주로 나타나고 있었어요. 하지만 이를 완화하기 위해 나름의 두 가지 방식의 휴식으로 감정의 균형을 잘 찾아가는 모습이 확인됩니다.',
      '포켓몬이나 네이버웹툰을 통해 개인적인 몰입의 시간을 갖거나, 절친과의 교류를 통해 안전한 소통을 하는 방식이죠. 스트레스 요인이 집중되는 날에는 이런 편안한 콘텐츠 소비 시간을 조금 더 늘리거나, 편안한 관계에 에너지를 온전히 쓰는 것이 감정 회복에 도움이 될 것으로 예상됩니다.',
    ],
  },
  {
    id: 'weekly-20260601',
    type: '주간',
    range: '2026.06.01 ~ 2026.06.07',
    title: '2026년 6월 1주차 마음 리포트',
    summary: '마감 일정 이후 회복 리듬을 찾은 주',
    stressCauses: ['과제 마감', '수면 부족', '팀 회의'],
    reliefCauses: ['산책', '따뜻한 차', '짧은 낮잠'],
    emotions: [
      { day: '1일', icon: '😐' },
      { day: '2일', icon: '😣' },
      { day: '3일', icon: '😮‍💨' },
      { day: '4일', icon: '🙂' },
      { day: '5일', icon: '😌' },
      { day: '6일', icon: '😄' },
      { day: '7일', icon: '🙂' },
    ],
    analysis: [
      '이번 주에는 과제 마감과 팀 회의가 겹치면서 초반 피로도가 높게 나타났어요. 특히 잠이 부족한 날에는 사소한 일정도 크게 부담으로 느껴지는 흐름이 보였습니다.',
      '후반으로 갈수록 산책과 짧은 낮잠처럼 몸을 바로 쉬게 해주는 행동이 감정 회복에 도움이 되었어요. 다음 주에도 긴 일정 전후에는 작은 휴식 시간을 먼저 확보하는 편이 좋겠습니다.',
    ],
  },
  {
    id: 'weekly-20260608',
    type: '주간',
    range: '2026.06.08 ~ 2026.06.14',
    title: '2026년 6월 2주차 마음 리포트',
    summary: '발표와 진로 고민을 정리해간 주',
    stressCauses: ['발표 준비', '진로 고민', '가족 대화'],
    reliefCauses: ['음악 감상', '웹툰 보기', '친구와 통화'],
    emotions: [
      { day: '8일', icon: '😳' },
      { day: '9일', icon: '😣' },
      { day: '10일', icon: '😐' },
      { day: '11일', icon: '🙂' },
      { day: '12일', icon: '😌' },
      { day: '13일', icon: '😄' },
      { day: '14일', icon: '😊' },
    ],
    analysis: [
      '발표 준비와 진로 고민이 함께 올라오면서 미래에 대한 압박감이 자주 감지됐어요. 가족과의 대화에서는 조언을 받는 상황이 때때로 평가처럼 느껴져 긴장감이 커진 것으로 보입니다.',
      '음악 감상과 웹툰 보기처럼 혼자 호흡을 정리하는 시간이 안정감을 주었고, 친구와의 통화는 생각을 정리하는 데 도움이 되었어요. 부담이 커질 때는 먼저 감정을 말로 꺼내는 루틴을 만들어보면 좋겠습니다.',
    ],
  },
])

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

const reportsByNewest = computed(() => [...reports.value].sort((a, b) => getReportStartDate(b) - getReportStartDate(a)))
const latestMonth = computed(() => getReportMonth(reportsByNewest.value[0]))
const isMonthFilterOpen = ref(false)
const selectedMonth = ref(latestMonth.value)
const selectedReportId = ref(reportsByNewest.value[0].id)

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
  selectedMonth.value = newMonth
})

onMounted(async () => {
  try {
    const data = await reportApi.generateReport()
    if (data && data.reports && data.reports.length > 0) {
      data.reports.forEach(report => {
        reports.value.push(report)
      })
      // 기본적으로 가장 첫 번째 리포트를 선택
      selectedMonth.value = getReportMonth(data.reports[0])
      selectedReportId.value = data.reports[0].id
    }
  } catch (error) {
    console.error('Failed to fetch generated report:', error)
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

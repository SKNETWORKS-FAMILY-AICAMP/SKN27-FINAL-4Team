<template>
  <main class="diary-page" :style="{ '--report-bg': `url(${reportBg})` }">
    <div class="diary-toolbar">
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

    <section class="diary-shell" aria-label="마음 리포트 보관함">
      <!-- ────── 사이드바 ────── -->
      <aside class="side">
        <div class="side-head">
          <img class="side-quill" :src="feather" alt="" aria-hidden="true" />
          <span class="side-brand">마음 리포트</span>
          <button
            type="button"
            class="filter-toggle"
            :class="{ active: isMonthFilterOpen }"
            :aria-expanded="isMonthFilterOpen"
            @click="isMonthFilterOpen = !isMonthFilterOpen"
          >기록</button>
        </div>

        <div class="side-body">
          <div v-if="isMonthFilterOpen" class="month-filter">
            <button
              v-for="month in monthOptions"
              :key="month.value"
              type="button"
              class="month-chip"
              :class="{ active: selectedMonth === month.value }"
              @click="selectedMonth = month.value"
            >{{ month.label }}</button>
          </div>
          <p v-if="!isLoading && !hasReports" class="side-empty">아직 생성된 마음 리포트가 없어요.</p>
          <ul class="report-list">
            <li v-for="period in filteredReports" :key="period.id">
              <button
                type="button"
                class="report-item"
                :class="{ active: selectedReportId === period.id }"
                @click="selectedReportId = period.id"
              >
                <span class="ri-date">{{ periodDateLabel(period) }}</span>
                <strong class="ri-title">{{ period.title }}</strong>
                <img v-if="selectedReportId === period.id" class="ri-heart" :src="heartIcon" alt="" aria-hidden="true" />
                <span v-else class="ri-lock" aria-hidden="true">🔒</span>
              </button>
            </li>
          </ul>
        </div>
      </aside>

      <!-- ────── 보드 ────── -->
      <section class="board">
        <!-- 상태 -->
        <div v-if="isLoading || fetchError || !currentReport" class="board-state">
          <img :src="bubbleHeart" class="state-icon" alt="" aria-hidden="true" />
          <template v-if="isLoading"><h1>리포트를 확인하고 있어요</h1><p>저장된 마음 리포트를 불러오는 중입니다.</p></template>
          <template v-else-if="fetchError"><h1>마음 리포트를 불러오지 못했어요.</h1><p>{{ fetchError }}</p></template>
          <template v-else><h1>아직 기록이 조금 부족해요</h1><p>대화를 나눈 뒤 새로고침하면 최신 주간·월간 마음 리포트를 확인할 수 있어요.</p></template>
        </div>

        <!-- 안전 -->
        <div v-else-if="currentReport.is_safety_response" class="board-state">
          <img :src="bubbleHeart" class="state-icon" alt="" aria-hidden="true" />
          <h1>{{ currentReport.title }}</h1>
          <p class="safety-line">지금은 안전을 먼저 확인할 시간이에요. 도움을 받을 수 있는 방법을 안내합니다.</p>
          <div class="safety-body"><p v-for="line in currentReport.analysis" :key="line">{{ line }}</p></div>
        </div>

        <!-- 본문 -->
        <template v-else>
          <header class="board-header">
            <img class="bh-icon" :src="bubbleHeart" alt="" aria-hidden="true" />
            <div class="bh-text">
              <h1>{{ currentReport.title }}<img class="title-spark" :src="sparkle" alt="" aria-hidden="true" /></h1>
              <p class="bh-sub">잘 해냈어요, 오늘도. 당신의 하루를 반짝이는 선물로 기록해요.</p>
            </div>
            <span class="bh-date">{{ headerDate }}</span>
          </header>

<<<<<<< HEAD
          <div class="board-grid">
            <!-- 한 줄 기록 -->
            <section class="card card-oneline">
              <h2 class="card-title"><img :src="feather" alt="" aria-hidden="true" />한 줄 기록</h2>
              <p class="oneline">
                {{ currentReport.summary || '기록이 모이면 이번 마음의 한 줄이 여기에 담겨요.' }}
                <img class="oneline-heart" :src="heartIcon" alt="" aria-hidden="true" />
              </p>
            </section>

            <!-- 태그 -->
            <section class="card card-tags">
              <h2 class="card-title"><img :src="heartIcon" alt="" aria-hidden="true" />태그 속 마음 조각</h2>
              <div class="tag-cloud">
                <span
                  v-for="tag in mindTags"
                  :key="tag.type + tag.text"
                  class="mind-tag"
                  :class="tag.type === 'relief' ? 'is-relief' : 'is-stress'"
                >#{{ tag.text }}</span>
                <span v-if="mindTags.length === 0" class="mind-tag is-muted">아직 모이는 중</span>
              </div>
            </section>

            <!-- 감정 흐름 -->
            <section class="card card-flow">
              <h2 class="card-title"><img :src="noteIcon" alt="" aria-hidden="true" />감정 흐름 (멜로디)</h2>
              <p class="flow-sub">감정 기록이 더 섬세할수록 내 멜로디가 그려져요.</p>
              <div class="flow-legend">
                <span class="lg tone-neg"><i></i>많이 힘들었어요</span>
                <span class="lg tone-neu"><i></i>조금 나아졌어요</span>
                <span class="lg tone-pos"><i></i>따뜻했어요</span>
              </div>
              <div v-if="emotionPoints.length" class="flow-stage">
                <svg class="flow-svg" :viewBox="`0 0 ${FLOW_W} ${FLOW_H}`" preserveAspectRatio="none" aria-hidden="true">
                  <defs>
                    <linearGradient id="flowStroke" x1="0" y1="0" x2="1" y2="0">
                      <stop offset="0%" stop-color="#8f7bd6" />
                      <stop offset="50%" stop-color="#e59ec3" />
                      <stop offset="100%" stop-color="#f4a35f" />
                    </linearGradient>
                  </defs>
                  <path :d="emotionPath" class="flow-line" />
                </svg>
                <div class="flow-dots">
                  <div
                    v-for="(p, i) in emotionPoints"
                    :key="p.day + i"
                    class="flow-dot"
                    :class="`tone-${p.tone}`"
                    :style="{ left: `${(p.x / FLOW_W) * 100}%`, top: `${(p.y / FLOW_H) * 100}%` }"
                  ><small>{{ p.day }}</small></div>
                </div>
              </div>
              <p v-else class="card-empty">감정 기록이 더 쌓이면 이곳에 멜로디가 그려져요.</p>
            </section>

            <!-- 마음을 힘들게 한 순간 -->
            <section class="card card-hard">
              <h2 class="card-title"><img :src="catIcon" alt="" aria-hidden="true" />마음을 힘들게 한 순간 <em>(불협화음)</em></h2>
              <ul class="hard-list">
                <li v-for="line in hardMoments" :key="line">{{ line }}</li>
                <li v-if="hardMoments.length === 0" class="hard-empty">뚜렷하게 마음을 흔든 순간은 아직 보이지 않아요.</li>
              </ul>
            </section>

            <!-- 나를 다독이는 한마디 -->
            <section class="card card-comfort">
              <h2 class="card-title"><img :src="heartIcon" alt="" aria-hidden="true" />나를 다독이는 한마디 <em>(위로 선물)</em></h2>
              <p class="comfort-quote">{{ comfortMessage }}</p>
              <img class="comfort-mascot" :src="flowRedpanda" alt="" aria-hidden="true" />
            </section>
          </div>

          <!-- 작은 제안 -->
          <section class="suggest-block">
            <h2 class="suggest-head">
              <img :src="sparkle" alt="" aria-hidden="true" />작은 제안
              <em>지금의 나에게 어울리는 작은 활동이에요. 가볍게 시도해 보세요.</em>
            </h2>
            <div v-if="suggestCards.length" class="suggest-grid" :style="{ gridTemplateColumns: `repeat(${suggestCards.length}, 1fr)` }">
              <article v-for="(card, index) in suggestCards" :key="card.title + index" class="suggest-card">
                <div class="sc-head">
                  <img class="sc-mascot" :src="mascotFor(index)" alt="" aria-hidden="true" />
                  <strong>{{ card.title || '오늘의 작은 제안' }}</strong>
                </div>
                <p class="sc-reason">{{ card.reason }}</p>
                <div v-if="card.how" class="sc-start">
                  <span class="sc-start-label">어떻게 시작해볼까요?</span>
                  <p><img class="sc-heart" :src="heartIcon" alt="" aria-hidden="true" />{{ card.how }}</p>
                </div>
              </article>
            </div>
            <p v-else class="card-empty">추천 활동이 준비되면 이곳에 담겨요.</p>
          </section>
        </template>
=======
        <footer class="report-actions">
          <p>☆ 작은 기록이 모여, 당신의 내일을 더 단단하게 만듭니다. <span>♥</span></p>
          <button type="button" class="secondary-button">이미지 저장</button>
          <button type="button" class="primary-button" disabled aria-disabled="true">공유</button>
        </footer>
>>>>>>> origin/dev
      </section>
    </section>

    <!-- 추천 행동 피드백 -->
    <section v-if="currentReport && !currentReport.is_safety_response && todayAction" class="feedback-panel" aria-labelledby="action-feedback-title">
      <h2 id="action-feedback-title"><img :src="sparkle" alt="" aria-hidden="true" />추천 행동은 어땠나요?</h2>
      <p class="feedback-desc"><strong>{{ todayAction.title }}</strong>을(를) 해본 뒤, 감정 완화에 도움이 된 정도를 남겨주세요.</p>
      <div class="feedback-score-row">
        <button
          v-for="option in feedbackOptions"
          :key="option.value"
          type="button"
          class="feedback-score"
          :class="{ active: actionFeedbackValue === option.value }"
          @click="actionFeedbackValue = option.value"
        >
          <strong>{{ option.value }}</strong>
          <span>{{ option.label }}</span>
        </button>
      </div>
      <div class="feedback-footer">
        <span v-if="actionFeedbackMessage" class="feedback-message">{{ actionFeedbackMessage }}</span>
        <button type="button" class="primary-button" :disabled="isFeedbackSaving || !actionFeedbackValue" @click="saveActionFeedback">
          {{ isFeedbackSaving ? '저장 중…' : '평가 저장' }}
        </button>
      </div>
    </section>
  </main>
</template>

<script setup>
import { computed, ref, watch, onBeforeUnmount, onMounted } from 'vue'
import { reportApi } from '../../api/report.js'
import reportBg from '../../assets/report-bg.png'
<<<<<<< HEAD
import bubbleHeart from '../../assets/report/bubble-heart.png'
import feather from '../../assets/report/feather.png'
import heartIcon from '../../assets/report/heart.png'
import noteIcon from '../../assets/report/note.png'
import sparkle from '../../assets/report/sparkle.png'
import flowBird from '../../assets/report/flow-bird.png'
import flowOtter from '../../assets/report/flow-otter.png'
import flowRedpanda from '../../assets/report/flow-redpanda.png'
import flowCat from '../../assets/report/flow-cat.png'
import catIcon from '../../assets/report/flow-cat.png'

const mascots = [flowRedpanda, flowOtter, flowBird, flowCat]
const mascotFor = (index) => mascots[index % mascots.length]
=======
import { attachMindReportImageSaver } from './reportImageSaver.js'
>>>>>>> origin/dev

const reports = ref([])

const isLoading = ref(true)
const isRefreshing = ref(false)
const fetchError = ref('')
let detachReportImageSaver = null

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
const getReportMonth = (report) => (report && report.range ? report.range.slice(0, 7) : '')
const formatMonthLabel = (month) => {
  const [year, value] = month.split('.')
  return `${year}년 ${Number(value)}월`
}
const periodDateLabel = (report) => (report && report.range ? report.range.split(' ~ ')[0].replace(' 생성', '') : '')
const weekdayKo = ['일', '월', '화', '수', '목', '금', '토']

const hasReports = computed(() => reports.value.length > 0)
const reportsByNewest = computed(() => [...reports.value].sort((a, b) => getReportStartDate(b) - getReportStartDate(a)))
const latestMonth = computed(() => getReportMonth(reportsByNewest.value[0]))
const isMonthFilterOpen = ref(false)
const selectedMonth = ref(latestMonth.value)
const selectedReportId = ref(reportsByNewest.value[0]?.id)

const monthOptions = computed(() => {
  const months = [...new Set(reportsByNewest.value.map(getReportMonth))]
  return months.map((month) => ({ value: month, label: formatMonthLabel(month) }))
})
<<<<<<< HEAD
const filteredReports = computed(() => reportsByNewest.value.filter((r) => getReportMonth(r) === selectedMonth.value))
const currentReport = computed(() => filteredReports.value.find((r) => r.id === selectedReportId.value) ?? filteredReports.value[0])
const todayAction = computed(() => todayCheckin.value?.selected_action ?? null)
const headerDate = computed(() => {
  const r = currentReport.value?.range || ''
  if (r.includes('~')) return r
  const d = getReportStartDate(currentReport.value)
  if (d instanceof Date && !Number.isNaN(d.getTime())) {
    return `${r.replace(' 생성', '').trim()} ${weekdayKo[d.getDay()]}요일`
=======

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
>>>>>>> origin/dev
  }
  return r
})

const mindTags = computed(() => {
  const report = currentReport.value
  if (!report) return []
  const clean = (list) => list.map((t) => String(t).trim()).filter((t) => t && t !== '기록 수집 중...')
  return [
    ...clean(report.stressCauses).map((text) => ({ text, type: 'stress' })),
    ...clean(report.reliefCauses).map((text) => ({ text, type: 'relief' })),
  ]
})

const parsedAnalysis = computed(() => {
  const analysis = currentReport.value?.analysis ?? []
  const recs = currentReport.value?.recommendations ?? []
  const reflections = []
  const cards = []
  const hasMarker = analysis.some((line) => String(line).trim().startsWith('✅'))
  if (hasMarker) {
    let cur = null
    for (const raw of analysis) {
      const line = String(raw).trim()
      if (line.startsWith('✅')) {
        cur = { title: line.replace(/^✅\s*/, ''), reason: '', how: '' }
        cards.push(cur)
      } else if (line.includes('왜 추천하나요?')) {
        if (cur) cur.reason = line.split('왜 추천하나요?')[1].replace(/^[\s:?-]*/, '').trim()
      } else if (line.includes('어떻게 시작할까요?')) {
        if (cur) cur.how = line.split('어떻게 시작할까요?')[1].replace(/^[\s:?-]*/, '').trim()
      } else if (!cur && line) {
        reflections.push(line)
      }
    }
  } else {
    const recSet = new Set(recs.map((r) => String(r).trim()))
    for (const raw of analysis) {
      const line = String(raw || '').trim()
      if (!line || recSet.has(line)) continue
      reflections.push(line)
    }
    for (const r of recs) cards.push({ title: '', reason: String(r).trim(), how: '' })
  }
  return { reflections, cards }
})

const hardMoments = computed(() => {
  const report = currentReport.value
  if (!report) return []
  const causes = report.stressCauses.map((t) => String(t).trim()).filter((t) => t && t !== '기록 수집 중...')
  if (causes.length) return causes.slice(0, 4)
  return parsedAnalysis.value.reflections.slice(0, 3)
})

const suggestCards = computed(() => parsedAnalysis.value.cards.slice(0, 4))

const comfortPool = [
  '지금 이 순간도, 나는\n나의 속도로 잘 가고 있어요.',
  '애쓴 마음을 가장 먼저 알아주는 건,\n바로 나 자신이에요.',
  '느려도 괜찮아요.\n멈추지 않았다는 게 중요해요.',
  '오늘의 나에게,\n작은 쉼표 하나를 선물해요.',
  '충분히 잘하고 있어요.\n조금 더 다정해도 좋아요, 나에게.',
]
const comfortMessage = computed(() => {
  const id = currentReport.value?.id ?? ''
  let hash = 0
  for (let i = 0; i < id.length; i += 1) hash = (hash + id.charCodeAt(i)) % comfortPool.length
  return comfortPool[hash]
})

/* 감정 흐름 라인차트 */
const FLOW_W = 640
const FLOW_H = 150
const moodLevel = (icon) => {
  if (['😊', '😄', '🙂', '😌', '🥲'].includes(icon)) return 0.82
  if (['😢', '😣', '😔', '😞', '😥'].includes(icon)) return 0.2
  if (['😮‍💨', '😳', '😰', '😨'].includes(icon)) return 0.36
  return 0.5
}
const moodTone = (icon) => {
  const level = moodLevel(icon)
  if (level >= 0.7) return 'pos'
  if (level <= 0.4) return 'neg'
  return 'neu'
}
const buildPath = (points) => {
  if (points.length === 0) return ''
  if (points.length === 1) return `M ${points[0].x} ${points[0].y}`
  let d = `M ${points[0].x} ${points[0].y}`
  for (let i = 0; i < points.length - 1; i += 1) {
    const p0 = points[i]
    const p1 = points[i + 1]
    const mx = (p0.x + p1.x) / 2
    d += ` C ${mx} ${p0.y}, ${mx} ${p1.y}, ${p1.x} ${p1.y}`
  }
  return d
}
const emotionPoints = computed(() => {
  const list = currentReport.value?.emotions ?? []
  if (!list.length) return []
  const n = list.length
  const padX = 40
  const usable = FLOW_W - padX * 2
  const top = 26
  const bottom = 120
  return list.map((d, i) => {
    const level = moodLevel(d.icon)
    const x = n === 1 ? FLOW_W / 2 : padX + (usable * i) / (n - 1)
    const y = bottom - level * (bottom - top)
    return { x, y, icon: d.icon, day: d.day, tone: moodTone(d.icon) }
  })
})
const emotionPath = computed(() => buildPath(emotionPoints.value))

watch(selectedMonth, () => { selectedReportId.value = filteredReports.value[0]?.id })
watch(latestMonth, (newMonth) => { if (newMonth) selectedMonth.value = newMonth })

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
<<<<<<< HEAD
const loadTodayCheckin = async () => {
  try {
    const data = await reportApi.getTodayCheckin()
    todayCheckin.value = data?.checkin ?? null
    actionFeedbackValue.value = data?.action_feedback?.helpfulness ?? null
  } catch (error) {
    console.warn('Failed to fetch today check-in:', error)
  }
}
onMounted(() => { loadReports(); loadTodayCheckin() })

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
=======

onMounted(() => {
  detachReportImageSaver = attachMindReportImageSaver()
  loadReports()
})

onBeforeUnmount(() => {
  detachReportImageSaver?.()
})

const emotionToneClass = (day) => {
  if (day.emotion_state === 'positive') return 'emotion-day--positive'
  if (day.emotion_state === 'negative') return 'emotion-day--negative'

  // 기존에 저장된 리포트에는 emotion_state가 없으므로 아이콘으로 호환한다.
  if (['😄', '😊', '🙂', '😌', '🥲'].includes(day.icon)) return 'emotion-day--positive'
  if (['😢', '😣', '😔', '😮‍💨', '😳'].includes(day.icon)) return 'emotion-day--negative'
  return 'emotion-day--neutral'
>>>>>>> origin/dev
}
</script>

<style scoped>
button { font: inherit; cursor: pointer; }

.diary-page {
  min-height: calc(100vh - 54px);
  padding: 30px 26px 84px;
  overflow: hidden auto;
  background-image:
    linear-gradient(
      180deg,
      rgba(13, 5, 32, 0.18) 0%,
      rgba(20, 8, 48, 0.3) 45%,
      rgba(13, 5, 32, 0.46) 100%
    ),
    var(--report-bg);
  background-position: center;
  background-size: cover;
  background-attachment: fixed;
  font-family: var(--font-ui);
}

.diary-toolbar { display: flex; justify-content: flex-end; width: min(1400px, 100%); margin: 0 auto 12px; }
.refresh-button {
  display: inline-flex; align-items: center; gap: 7px; min-height: 38px; padding: 8px 15px;
  border: 1px solid rgba(255, 255, 255, 0.28); border-radius: 999px;
  background: rgba(38, 22, 66, 0.6); color: #fff8ff; box-shadow: 0 8px 24px rgba(8, 3, 20, 0.2);
}
.refresh-button:disabled { cursor: wait; opacity: 0.58; }
.refresh-icon.spinning { animation: refresh-spin 0.8s linear infinite; }
@keyframes refresh-spin { to { transform: rotate(360deg); } }
.refresh-button:hover:not(:disabled) { border-color: rgba(244, 175, 170, 0.8); transform: translateY(-1px); }

/* ── 셸 ── */
.diary-shell {
  display: grid;
  grid-template-columns: 288px minmax(0, 1fr);
  gap: 20px;
  width: min(1400px, 100%);
  margin: 0 auto;
  align-items: stretch;
}

/* ── 사이드바 ── */
.side {
  display: flex; flex-direction: column;
  padding: 22px 18px 20px;
  border: 1px solid rgba(150, 110, 190, 0.4);
  border-radius: 26px;
  background: linear-gradient(180deg, #2c1a50 0%, #38215f 60%, #2a1850 100%);
  box-shadow: 0 22px 54px rgba(8, 3, 24, 0.5), inset 0 0 0 1px rgba(210, 180, 255, 0.08);
  color: #f6eefc;
}
.side-head { display: flex; align-items: center; gap: 9px; margin-bottom: 16px; }
.side-quill { width: 24px; height: 24px; object-fit: contain; }
.side-brand { flex: 1; font-family: var(--font-soft); font-size: 19px; font-weight: 800; letter-spacing: -0.3px; }
.filter-toggle {
  padding: 5px 12px; border: 1px solid rgba(255, 255, 255, 0.3); border-radius: 999px;
  background: transparent; color: #e9dcf4; font-size: 12px;
}
.filter-toggle:hover, .filter-toggle.active { border-color: #f2aaa8; color: #ffd6d3; }

.side-body { flex: 1; min-height: 150px; overflow-y: auto; }
.month-filter { display: flex; flex-wrap: wrap; gap: 6px; margin-bottom: 12px; }
.month-chip {
  padding: 6px 10px; border: 1px solid rgba(255, 255, 255, 0.2); border-radius: 999px;
  background: rgba(255, 255, 255, 0.06); color: #e6daf0; font-size: 12px;
}
.month-chip.active { border-color: rgba(242, 170, 168, 0.8); background: rgba(242, 170, 168, 0.16); color: #fff; }
.side-empty { color: #c9b7dc; font-size: 13px; line-height: 1.6; }

.report-list { list-style: none; margin: 0; padding: 0; display: grid; gap: 10px; }
.report-item {
  position: relative; display: grid; gap: 3px; width: 100%;
  padding: 12px 40px 12px 14px;
  border: 1px solid rgba(180, 150, 220, 0.28); border-radius: 14px;
  background: rgba(255, 255, 255, 0.05); color: #f2e9f8; text-align: left;
  transition: transform 0.16s ease, border-color 0.16s ease, background 0.16s ease;
}
.report-item:hover { transform: translateY(-1px); border-color: rgba(210, 180, 255, 0.5); }
.report-item.active {
  border-color: rgba(244, 176, 180, 0.7);
  background: linear-gradient(135deg, rgba(244, 176, 180, 0.26), rgba(150, 120, 210, 0.22));
  box-shadow: 0 8px 20px rgba(120, 60, 120, 0.3);
}
.ri-date { font-size: 12px; color: #cdbde2; }
.ri-title { font-size: 14px; font-weight: 700; color: #fffaff; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.ri-lock { position: absolute; top: 12px; right: 13px; font-size: 12px; opacity: 0.6; }
.ri-heart { position: absolute; top: 9px; right: 10px; width: 20px; height: 20px; object-fit: contain; }

/* ── 보드 ── */
.board {
  position: relative; min-width: 0;
  padding: 26px 28px 26px;
  border: 1px solid rgba(230, 175, 175, 0.4);
  border-radius: 28px;
  background: linear-gradient(158deg, #fae4d6 0%, #f7d2ce 50%, #f2c6d0 100%);
  box-shadow: 0 26px 64px rgba(30, 10, 40, 0.4), inset 0 0 0 1px rgba(255, 245, 240, 0.55);
  color: #5a4460;
  font-family: var(--font-soft);
}

.board-state {
  display: grid; justify-items: center; align-content: center; gap: 10px;
  min-height: 480px; text-align: center;
}
.state-icon { width: 74px; height: 74px; object-fit: contain; }
.board-state h1 { margin: 4px 0 0; font-size: 24px; color: #6a4270; }
.board-state p { margin: 0; max-width: 480px; color: #7d6787; font-size: 15px; line-height: 1.7; }
.safety-line { color: #a24d6c !important; font-weight: 700; }
.safety-body { margin-top: 12px; max-height: 300px; overflow-y: auto; }
.safety-body p { margin: 0 0 10px; color: #5c4a62; font-size: 14px; line-height: 1.8; }

.board-header { display: grid; grid-template-columns: auto 1fr auto; align-items: center; gap: 14px; margin-bottom: 20px; }
.bh-icon { width: 54px; height: 54px; object-fit: contain; }
.bh-text h1 { margin: 0; font-family: var(--font-soft); font-size: clamp(24px, 2.4vw, 32px); font-weight: 800; color: #5a3570; letter-spacing: -0.4px; }
.title-spark { width: 20px; height: 20px; object-fit: contain; vertical-align: 6px; margin-left: 8px; opacity: 0.85; }
.bh-sub { margin: 5px 0 0; color: #9a7ba6; font-size: 14px; }
.bh-date {
  align-self: start; padding: 7px 14px; border-radius: 999px;
  background: rgba(255, 255, 255, 0.55); color: #8a5c86;
  font-family: var(--font-ui); font-size: 13px; font-weight: 700; white-space: nowrap;
}

/* ── 카드 그리드 ── */
.board-grid {
  display: grid;
  grid-template-columns: minmax(0, 1.05fr) minmax(0, 0.95fr);
  grid-template-areas:
    'oneline tags'
    'flow    hard'
    'flow    comfort';
  gap: 16px;
  margin-bottom: 18px;
}
.card-oneline { grid-area: oneline; }
.card-tags { grid-area: tags; }
.card-flow { grid-area: flow; }
.card-hard { grid-area: hard; }
.card-comfort { grid-area: comfort; }

<<<<<<< HEAD
.card {
=======
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

.emotion-day--negative {
  border-color: rgba(0, 0, 0, 0.78);
  background: linear-gradient(180deg, rgba(255, 73, 105, 0.78), rgba(122, 20, 45, 0.74));
  box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.14), 0 8px 16px rgba(255, 58, 90, 0.2);
}

.emotion-day--neutral {
  border-color: rgba(0, 0, 0, 0.78);
  background: linear-gradient(180deg, rgba(170, 177, 190, 0.34), rgba(77, 82, 96, 0.42));
  box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.1);
}

.emotion-day--positive {
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
  background: linear-gradient(180deg, #fff9ed 0%, #f4e6cf 100%);
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
>>>>>>> origin/dev
  padding: 16px 18px;
  border: 1px solid rgba(255, 250, 248, 0.7);
  border-radius: 20px;
  background: rgba(255, 250, 247, 0.5);
  box-shadow: 0 8px 22px rgba(150, 90, 120, 0.1), inset 0 1px 0 rgba(255, 255, 255, 0.6);
}
.card-hard { background: rgba(233, 224, 245, 0.62); }
.card-comfort { background: rgba(247, 214, 220, 0.6); position: relative; overflow: hidden; }
.card-oneline { background: rgba(255, 251, 246, 0.6); }
.card-oneline .oneline {
  padding: 12px 14px; border: 1.5px dashed rgba(190, 140, 160, 0.5); border-radius: 14px;
  background: rgba(255, 252, 249, 0.5);
}
.card-title {
  display: flex; align-items: center; gap: 8px; margin: 0 0 12px;
  font-family: var(--font-soft); font-size: 17px; font-weight: 800; color: #6a4270;
}
.card-title img { width: 24px; height: 24px; object-fit: contain; }
.card-title em { font-style: normal; font-size: 12.5px; font-weight: 600; color: #a382ab; }
.card-empty { margin: 0; color: #9a7fa0; font-size: 13.5px; line-height: 1.6; }

/* 한 줄 기록 */
.oneline { margin: 0; color: #5c4660; font-size: 16px; line-height: 1.7; }
.oneline-heart { width: 22px; height: 22px; vertical-align: middle; margin-left: 4px; }

/* 태그 */
.tag-cloud { display: flex; flex-wrap: wrap; gap: 8px; }
.mind-tag { padding: 8px 14px; border-radius: 999px; font-family: var(--font-ui); font-size: 13.5px; font-weight: 600; }
.mind-tag.is-stress { background: rgba(232, 160, 185, 0.4); color: #9c4d6a; }
.mind-tag.is-relief { background: rgba(170, 160, 225, 0.42); color: #574f9c; }
.mind-tag.is-muted { background: rgba(200, 185, 205, 0.5); color: #7d6787; }

/* 감정 흐름 */
.flow-sub { margin: -4px 0 10px; color: #8a728f; font-size: 13px; }
.flow-legend { display: flex; flex-wrap: wrap; gap: 16px; margin-bottom: 10px; }
.lg { display: inline-flex; align-items: center; gap: 6px; font-family: var(--font-ui); font-size: 12.5px; color: #6f5f79; }
.lg i { width: 11px; height: 11px; border-radius: 50%; }
.lg.tone-neg i { background: #8f7bd6; }
.lg.tone-neu i { background: #d29ecf; }
.lg.tone-pos i { background: #f4a35f; }
.flow-stage { position: relative; width: 100%; height: 150px; }
.flow-svg { position: absolute; inset: 0; width: 100%; height: 100%; }
.flow-line { fill: none; stroke: url(#flowStroke); stroke-width: 4; stroke-linecap: round; }
.flow-dots { position: absolute; inset: 0; }
.flow-dot { position: absolute; transform: translate(-50%, -50%); width: 15px; height: 15px; border-radius: 50%; background: #fff; box-shadow: 0 3px 8px rgba(120, 70, 120, 0.28); }
.flow-dot.tone-pos { background: #f4a35f; }
.flow-dot.tone-neu { background: #d29ecf; }
.flow-dot.tone-neg { background: #8f7bd6; }
.flow-dot small { position: absolute; left: 50%; top: 20px; transform: translateX(-50%); font-family: var(--font-ui); font-size: 11px; color: #7c6a86; white-space: nowrap; }

/* 힘든 순간 */
.hard-list { margin: 0; padding: 0; list-style: none; display: grid; gap: 8px; }
.hard-list li { position: relative; padding-left: 18px; color: #5f4a68; font-size: 14.5px; line-height: 1.55; }
.hard-list li::before { content: '♪'; position: absolute; left: 0; color: #9a7bc0; }
.hard-empty::before { content: '·' !important; }

/* 다독임 */
.comfort-quote { margin: 0; padding-right: 76px; color: #8a4c84; font-size: 16px; line-height: 1.7; font-weight: 600; white-space: pre-line; }
.comfort-mascot { position: absolute; right: 12px; bottom: 10px; width: 62px; height: 62px; object-fit: contain; }

/* ── 작은 제안 ── */
.suggest-block {
  padding: 18px 18px 16px;
  border: 1px solid rgba(255, 250, 248, 0.7);
  border-radius: 20px;
  background: rgba(255, 250, 247, 0.42);
  box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.6);
}
.suggest-head {
  display: flex; align-items: center; gap: 8px; flex-wrap: wrap; margin: 0 0 14px;
  font-family: var(--font-soft); font-size: 17px; font-weight: 800; color: #6a4270;
}
.suggest-head img { width: 24px; height: 24px; object-fit: contain; }
.suggest-head em { font-style: normal; font-size: 12.5px; font-weight: 500; color: #9a86a6; }
.suggest-grid { display: grid; gap: 14px; }
.suggest-card {
  display: flex; flex-direction: column;
  padding: 14px 15px;
  border: 1px solid rgba(255, 250, 248, 0.8);
  border-radius: 16px;
  background: linear-gradient(180deg, rgba(255, 252, 250, 0.82), rgba(250, 240, 246, 0.72));
  box-shadow: 0 6px 16px rgba(150, 90, 120, 0.1);
}
.sc-head { display: flex; align-items: center; gap: 10px; margin-bottom: 8px; }
.sc-mascot { width: 40px; height: 40px; object-fit: contain; flex: 0 0 auto; }
.sc-head strong { color: #6a4270; font-size: 14.5px; font-weight: 800; line-height: 1.3; }
.sc-reason { margin: 0; color: #6f5f79; font-size: 13px; line-height: 1.6; }
.sc-start { margin-top: 12px; padding-top: 12px; border-top: 1px dashed rgba(160, 120, 170, 0.35); }
.sc-start-label { display: block; margin-bottom: 6px; color: #a06bb0; font-family: var(--font-ui); font-size: 12.5px; font-weight: 700; }
.sc-start p { margin: 0; display: flex; align-items: flex-start; gap: 6px; color: #5a4665; font-size: 13px; font-weight: 600; line-height: 1.55; }
.sc-heart { width: 16px; height: 16px; object-fit: contain; margin-top: 2px; flex: 0 0 auto; }

/* ── 피드백 패널 ── */
.feedback-panel {
  width: min(1400px, 100%); margin: 16px auto 0; padding: 20px 22px;
  border: 1px solid rgba(255, 255, 255, 0.16); border-radius: 20px;
  background: linear-gradient(135deg, rgba(52, 30, 78, 0.82), rgba(70, 40, 96, 0.8));
  box-shadow: 0 18px 44px rgba(6, 3, 18, 0.35); color: #fbf5ff; font-family: var(--font-ui);
}
.feedback-panel h2 { display: flex; align-items: center; gap: 8px; margin: 0 0 6px; font-family: var(--font-soft); font-size: 18px; }
.feedback-panel h2 img { width: 22px; height: 22px; object-fit: contain; }
.feedback-desc { margin: 0 0 12px; color: rgba(255, 245, 250, 0.78); font-size: 13.5px; line-height: 1.6; }
.feedback-desc strong { color: #ffc7dc; }
.feedback-score-row { display: grid; grid-template-columns: repeat(5, minmax(0, 1fr)); gap: 8px; }
.feedback-score {
  display: grid; justify-items: center; gap: 5px; min-height: 60px; padding: 9px 6px;
  border: 1px solid rgba(255, 255, 255, 0.2); border-radius: 12px;
  background: rgba(255, 255, 255, 0.06); color: rgba(255, 240, 248, 0.8); transition: 0.16s ease;
}
.feedback-score strong { font-size: 17px; color: #fff2f8; }
.feedback-score span { font-size: 10px; text-align: center; white-space: nowrap; }
.feedback-score:hover, .feedback-score.active {
  border-color: rgba(231, 62, 101, 0.7);
  background: linear-gradient(135deg, rgba(231, 62, 101, 0.7), rgba(231, 126, 110, 0.6));
  color: #fff; transform: translateY(-1px);
}
.feedback-footer { display: flex; align-items: center; justify-content: space-between; gap: 12px; margin-top: 12px; }
.feedback-message { color: #bff8ef; font-size: 12px; font-weight: 700; }
.primary-button {
  min-height: 40px; padding: 9px 18px; border: 1px solid #e73e65; border-radius: 999px;
  background: linear-gradient(135deg, #e73e65, #ee5d5f); color: #fffaff; font-family: var(--font-ui);
}
.primary-button:hover:not(:disabled) { transform: translateY(-1px); }
.primary-button:disabled { cursor: not-allowed; opacity: 0.55; }

/* ── 반응형 ── */
@media (max-width: 1040px) {
  .diary-shell { grid-template-columns: 1fr; }
  .side { flex-direction: column; }
  .side-body { max-height: 260px; }
  .board-grid { grid-template-columns: 1fr; grid-template-areas: 'oneline' 'tags' 'flow' 'hard' 'comfort'; }
  .suggest-grid { grid-template-columns: repeat(2, 1fr) !important; }
}
<<<<<<< HEAD
@media (max-width: 620px) {
  .diary-page { padding: 66px 12px 40px; background-attachment: scroll; }
  .board { padding: 20px 16px; border-radius: 22px; }
  .board-header { grid-template-columns: auto 1fr; }
  .bh-date { grid-column: 2; justify-self: start; }
  .suggest-grid { grid-template-columns: 1fr !important; }
  .feedback-score span { font-size: 9px; }
=======

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

>>>>>>> origin/dev
}
</style>

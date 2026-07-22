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
      <section class="board report-card" :class="{ 'is-loading': isLoading }" :aria-busy="isLoading">
        <!-- 상태 -->
        <div v-if="!isLoading && (fetchError || !currentReport)" class="board-state">
          <img :src="bubbleHeart" class="state-icon" alt="" aria-hidden="true" />
          <template v-if="fetchError"><h1>마음 리포트를 불러오지 못했어요.</h1><p>{{ fetchError }}</p></template>
          <template v-else><h1>아직 기록이 조금 부족해요</h1><p>대화를 나눈 뒤 새로고침하면 최신 주간·월간 마음 리포트를 확인할 수 있어요.</p></template>
        </div>

        <!-- 안전 -->
        <div v-else-if="!isLoading && currentReport?.is_safety_response" class="board-state">
          <img :src="bubbleHeart" class="state-icon" alt="" aria-hidden="true" />
          <h1>{{ currentReport.title }}</h1>
          <p class="safety-line">지금은 안전을 먼저 확인할 시간이에요. 도움을 받을 수 있는 방법을 안내합니다.</p>
          <div class="safety-body"><p v-for="line in currentReport.analysis" :key="line">{{ line }}</p></div>
        </div>

        <!-- 본문 -->
        <template v-else-if="!isLoading && currentReport">
          <header class="board-header">
            <img class="bh-icon" :src="bubbleHeart" alt="" aria-hidden="true" />
            <div class="bh-text">
              <h1>{{ currentReport.title }}<img class="title-spark" :src="sparkle" alt="" aria-hidden="true" /></h1>
              <p class="bh-sub">잘 해냈어요, 오늘도. 당신의 하루를 반짝이는 선물로 기록해요.</p>
            </div>
            <span class="bh-date">{{ headerDate }}</span>
          </header>


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
                  :class="[`is-${tag.type}`, `is-${tag.emphasis}`]"
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

        <footer v-if="!isLoading" class="report-actions">
          <p>☆ 작은 기록이 모여, 당신의 내일을 더 단단하게 만듭니다. <span>♥</span></p>
          <button type="button" class="secondary-button" :disabled="!currentReport">이미지 저장</button>
        </footer>

      </section>
    </section>

  </main>
</template>

<script setup>
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { reportApi } from '../../api/report.js'
import reportBg from '../../assets/report-bg.png'

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

import { attachMindReportImageSaver } from './reportImageSaver.js'

const mascots = [flowRedpanda, flowOtter, flowBird, flowCat]
const mascotFor = (index) => mascots[index % mascots.length]

const reports = ref([])
const isLoading = ref(true)
const isRefreshing = ref(false)
const fetchError = ref('')
const isMonthFilterOpen = ref(false)
const selectedMonth = ref('')
const selectedReportId = ref(null)

let detachReportImageSaver = null

const normalizeReport = (report) => ({
  ...report,
  stressCauses: Array.isArray(report?.stressCauses) ? report.stressCauses : [],
  reliefCauses: Array.isArray(report?.reliefCauses) ? report.reliefCauses : [],
  causeLabels: Array.isArray(report?.causeLabels) ? report.causeLabels : [],
  emotions: Array.isArray(report?.emotions) ? report.emotions : [],
  analysis: Array.isArray(report?.analysis) ? report.analysis : [],
  recommendations: Array.isArray(report?.recommendations) ? report.recommendations : [],
  is_fallback: Boolean(report?.is_fallback),
  is_safety_response: Boolean(report?.is_safety_response),
})

const getReportStartDate = (report) => {
  if (!report?.range) return new Date(0)

  const dateText = report.range
    .split(' ~ ')[0]
    .replace(' 생성', '')
    .trim()
    .replaceAll('.', '-')

  const date = new Date(dateText)
  return Number.isNaN(date.getTime()) ? new Date(0) : date
}

const getReportMonth = (report) => {
  if (!report?.range) return ''
  return report.range.replace(' 생성', '').trim().slice(0, 7)
}

const formatMonthLabel = (month) => {
  if (!month) return ''
  const [year, value] = month.split('.')
  return `${year}년 ${Number(value)}월`
}

const periodDateLabel = (report) => (
  report?.range
    ? report.range.split(' ~ ')[0].replace(' 생성', '').trim()
    : ''
)

const weekdayKo = ['일', '월', '화', '수', '목', '금', '토']

const hasReports = computed(() => reports.value.length > 0)

const reportsByNewest = computed(() => (
  [...reports.value].sort(
    (a, b) => getReportStartDate(b).getTime() - getReportStartDate(a).getTime(),
  )
))

const latestMonth = computed(() => getReportMonth(reportsByNewest.value[0]))

const monthOptions = computed(() => {
  const months = [...new Set(reportsByNewest.value.map(getReportMonth).filter(Boolean))]
  return months.map((month) => ({
    value: month,
    label: formatMonthLabel(month),
  }))
})

const filteredReports = computed(() => {
  if (!selectedMonth.value) return reportsByNewest.value
  return reportsByNewest.value.filter(
    (report) => getReportMonth(report) === selectedMonth.value,
  )
})

const currentReport = computed(() => (
  filteredReports.value.find(
    (report) => report.id === selectedReportId.value,
  ) ?? filteredReports.value[0] ?? null
))

const headerDate = computed(() => {
  const report = currentReport.value
  if (!report?.range) return ''

  const range = report.range.replace(' 생성', '').trim()
  if (range.includes('~')) return range

  const date = getReportStartDate(report)
  if (Number.isNaN(date.getTime())) return range

  return `${range} ${weekdayKo[date.getDay()]}요일`
})

watch(selectedMonth, () => {
  selectedReportId.value = filteredReports.value[0]?.id ?? null
})

watch(latestMonth, (newMonth) => {
  if (newMonth && !selectedMonth.value) {
    selectedMonth.value = newMonth
  }
})

const mindTags = computed(() => {
  const report = currentReport.value
  if (!report) return []

  const detailedLabels = report.causeLabels
    .map((label) => {
      const text = String(label?.keyword ?? '').trim()
      const type = ['stress', 'relief'].includes(label?.causeType)
        ? label.causeType
        : null
      const emphasis = label?.emphasis === 'secondary' ? 'secondary' : 'primary'
      const hasDisplayWeight = label?.displayWeight !== null
        && label?.displayWeight !== undefined
        && label?.displayWeight !== ''
      const parsedWeight = hasDisplayWeight ? Number(label.displayWeight) : Number.NaN

      return {
        text,
        type,
        emphasis,
        displayWeight: Number.isFinite(parsedWeight)
          ? Math.min(1, Math.max(0, parsedWeight))
          : emphasis === 'secondary' ? 0.7 : 1,
      }
    })
    .filter((tag) => tag.type && tag.text && tag.text !== '기록 수집 중...')
    .sort((a, b) => b.displayWeight - a.displayWeight)

  if (detailedLabels.length) return detailedLabels

  const clean = (list) => list
    .map((text) => String(text).trim())
    .filter((text) => text && text !== '기록 수집 중...')

  return [
    ...clean(report.stressCauses).map((text) => ({ text, type: 'stress', emphasis: 'primary' })),
    ...clean(report.reliefCauses).map((text) => ({ text, type: 'relief', emphasis: 'primary' })),
  ]
})

const parsedAnalysis = computed(() => {
  const analysis = currentReport.value?.analysis ?? []
  const recommendations = currentReport.value?.recommendations ?? []
  const reflections = []
  const cards = []

  const hasMarker = analysis.some(
    (line) => String(line).trim().startsWith('✅'),
  )

  if (hasMarker) {
    let currentCard = null

    for (const raw of analysis) {
      const line = String(raw).trim()

      if (line.startsWith('✅')) {
        currentCard = {
          title: line.replace(/^✅\s*/, ''),
          reason: '',
          how: '',
        }
        cards.push(currentCard)
      } else if (line.includes('왜 추천하나요?')) {
        if (currentCard) {
          currentCard.reason = line
            .split('왜 추천하나요?')[1]
            .replace(/^[\s:?-]*/, '')
            .trim()
        }
      } else if (line.includes('어떻게 시작할까요?')) {
        if (currentCard) {
          currentCard.how = line
            .split('어떻게 시작할까요?')[1]
            .replace(/^[\s:?-]*/, '')
            .trim()
        }
      } else if (!currentCard && line) {
        reflections.push(line)
      }
    }
  } else {
    const recommendationSet = new Set(
      recommendations.map((item) => String(item).trim()),
    )

    for (const raw of analysis) {
      const line = String(raw ?? '').trim()
      if (!line || recommendationSet.has(line)) continue
      reflections.push(line)
    }

    for (const recommendation of recommendations) {
      cards.push({
        title: '',
        reason: String(recommendation).trim(),
        how: '',
      })
    }
  }

  return { reflections, cards }
})

const hardMoments = computed(() => {
  const report = currentReport.value
  if (!report) return []

  const causes = report.stressCauses
    .map((text) => String(text).trim())
    .filter((text) => text && text !== '기록 수집 중...')

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
  const id = String(currentReport.value?.id ?? '')
  let hash = 0

  for (let index = 0; index < id.length; index += 1) {
    hash = (hash + id.charCodeAt(index)) % comfortPool.length
  }

  return comfortPool[hash]
})

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

  let path = `M ${points[0].x} ${points[0].y}`

  for (let index = 0; index < points.length - 1; index += 1) {
    const current = points[index]
    const next = points[index + 1]
    const middleX = (current.x + next.x) / 2

    path += ` C ${middleX} ${current.y}, ${middleX} ${next.y}, ${next.x} ${next.y}`
  }

  return path
}

const emotionPoints = computed(() => {
  const list = currentReport.value?.emotions ?? []
  if (!list.length) return []

  const count = list.length
  const paddingX = 40
  const usableWidth = FLOW_W - paddingX * 2
  const top = 26
  const bottom = 120

  return list.map((day, index) => {
    const level = moodLevel(day.icon)
    const x = count === 1
      ? FLOW_W / 2
      : paddingX + (usableWidth * index) / (count - 1)
    const y = bottom - level * (bottom - top)

    return {
      x,
      y,
      icon: day.icon,
      day: day.day,
      tone: moodTone(day.icon),
    }
  })
})

const emotionPath = computed(() => buildPath(emotionPoints.value))

const applyReports = (data) => {
  reports.value = Array.isArray(data?.reports)
    ? data.reports.map(normalizeReport)
    : []

  const firstReport = reportsByNewest.value[0]

  if (firstReport) {
    selectedMonth.value = getReportMonth(firstReport)
    selectedReportId.value = firstReport.id
  } else {
    selectedMonth.value = ''
    selectedReportId.value = null
  }
}

const loadReports = async () => {
  try {
    fetchError.value = ''
    const data = await reportApi.getReports()
    applyReports(data)
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
    const data = await reportApi.refreshReports()
    applyReports(data)
  } catch (error) {
    fetchError.value = error?.message ?? '마음 리포트를 새로고침하지 못했습니다.'
    console.error('Failed to refresh reports:', error)
  } finally {
    isRefreshing.value = false
  }
}

onMounted(() => {
  detachReportImageSaver = attachMindReportImageSaver()
  loadReports()
})

onBeforeUnmount(() => {
  detachReportImageSaver?.()
})
</script>

<style scoped>
button {
  font: inherit;
  cursor: pointer;
}

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

.diary-toolbar {
  display: flex;
  justify-content: flex-end;
  width: min(1400px, 100%);
  margin: 0 auto 12px;
}

.refresh-button {
  display: inline-flex;
  align-items: center;
  gap: 7px;
  min-height: 38px;
  padding: 8px 15px;
  border: 1px solid rgba(255, 255, 255, 0.28);
  border-radius: 999px;
  background: rgba(38, 22, 66, 0.6);
  color: #fff8ff;
  box-shadow: 0 8px 24px rgba(8, 3, 20, 0.2);
  transition: transform 0.16s ease, border-color 0.16s ease;
}

.refresh-button:disabled {
  cursor: wait;
  opacity: 0.58;
}

.refresh-button:hover:not(:disabled) {
  border-color: rgba(244, 175, 170, 0.8);
  transform: translateY(-1px);
}

.refresh-icon.spinning {
  animation: refresh-spin 0.8s linear infinite;
}

@keyframes refresh-spin {
  to {
    transform: rotate(360deg);
  }
}

.diary-shell {
  display: grid;
  grid-template-columns: 288px minmax(0, 1fr);
  gap: 20px;
  width: min(1400px, 100%);
  margin: 0 auto;
  align-items: stretch;
}

.side {
  display: flex;
  flex-direction: column;
  padding: 22px 18px 20px;
  border: 1px solid rgba(150, 110, 190, 0.4);
  border-radius: 26px;
  background: linear-gradient(180deg, #2c1a50 0%, #38215f 60%, #2a1850 100%);
  box-shadow:
    0 22px 54px rgba(8, 3, 24, 0.5),
    inset 0 0 0 1px rgba(210, 180, 255, 0.08);
  color: #f6eefc;
}

.side-head {
  display: flex;
  align-items: center;
  gap: 9px;
  margin-bottom: 16px;
}

.side-quill {
  width: 24px;
  height: 24px;
  object-fit: contain;
}

.side-brand {
  flex: 1;
  font-family: var(--font-soft);
  font-size: 19px;
  font-weight: 800;
  letter-spacing: -0.3px;
}

.filter-toggle {
  padding: 5px 12px;
  border: 1px solid rgba(255, 255, 255, 0.3);
  border-radius: 999px;
  background: transparent;
  color: #e9dcf4;
  font-size: 12px;
}

.filter-toggle:hover,
.filter-toggle.active {
  border-color: #f2aaa8;
  color: #ffd6d3;
}

.side-body {
  flex: 1;
  min-height: 150px;
  overflow-y: auto;
}

.month-filter {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  margin-bottom: 12px;
}

.month-chip {
  padding: 6px 10px;
  border: 1px solid rgba(255, 255, 255, 0.2);
  border-radius: 999px;
  background: rgba(255, 255, 255, 0.06);
  color: #e6daf0;
  font-size: 12px;
}

.month-chip:hover,
.month-chip.active {
  border-color: rgba(242, 170, 168, 0.8);
  background: rgba(242, 170, 168, 0.16);
  color: #fff;
}

.side-empty {
  color: #c9b7dc;
  font-size: 13px;
  line-height: 1.6;
}

.report-list {
  display: grid;
  gap: 10px;
  margin: 0;
  padding: 0;
  list-style: none;
}

.report-item {
  position: relative;
  display: grid;
  gap: 3px;
  width: 100%;
  padding: 12px 40px 12px 14px;
  border: 1px solid rgba(180, 150, 220, 0.28);
  border-radius: 14px;
  background: rgba(255, 255, 255, 0.05);
  color: #f2e9f8;
  text-align: left;
  transition:
    transform 0.16s ease,
    border-color 0.16s ease,
    background 0.16s ease;
}

.report-item:hover {
  transform: translateY(-1px);
  border-color: rgba(210, 180, 255, 0.5);
}

.report-item.active {
  border-color: rgba(244, 176, 180, 0.7);
  background: linear-gradient(
    135deg,
    rgba(244, 176, 180, 0.26),
    rgba(150, 120, 210, 0.22)
  );
  box-shadow: 0 8px 20px rgba(120, 60, 120, 0.3);
}

.ri-date {
  color: #cdbde2;
  font-size: 12px;
}

.ri-title {
  overflow: hidden;
  color: #fffaff;
  font-size: 14px;
  font-weight: 700;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.ri-lock {
  position: absolute;
  top: 12px;
  right: 13px;
  font-size: 12px;
  opacity: 0.6;
}

.ri-heart {
  position: absolute;
  top: 9px;
  right: 10px;
  width: 20px;
  height: 20px;
  object-fit: contain;
}

.board {
  position: relative;
  min-width: 0;
  padding: 26px 28px;
  border: 1px solid rgba(230, 175, 175, 0.4);
  border-radius: 28px;
  background: linear-gradient(158deg, #fae4d6 0%, #f7d2ce 50%, #f2c6d0 100%);
  box-shadow:
    0 26px 64px rgba(30, 10, 40, 0.4),
    inset 0 0 0 1px rgba(255, 245, 240, 0.55);
  color: #5a4460;
  font-family: var(--font-soft);
}

.board.is-loading {
  min-height: 532px;
}

.board-state {
  display: grid;
  justify-items: center;
  align-content: center;
  gap: 10px;
  min-height: 480px;
  text-align: center;
}

.state-icon {
  width: 74px;
  height: 74px;
  object-fit: contain;
}

.board-state h1 {
  margin: 4px 0 0;
  color: #6a4270;
  font-size: 24px;
}

.board-state p {
  max-width: 480px;
  margin: 0;
  color: #7d6787;
  font-size: 15px;
  line-height: 1.7;
}

.safety-line {
  color: #a24d6c !important;
  font-weight: 700;
}

.safety-body {
  max-height: 300px;
  margin-top: 12px;
  overflow-y: auto;
}

.safety-body p {
  margin: 0 0 10px;
  color: #5c4a62;
  font-size: 14px;
  line-height: 1.8;
}

.board-header {
  display: grid;
  grid-template-columns: auto 1fr auto;
  align-items: center;
  gap: 14px;
  margin-bottom: 20px;
}

.bh-icon {
  width: 54px;
  height: 54px;
  object-fit: contain;
}

.bh-text h1 {
  margin: 0;
  color: #5a3570;
  font-family: var(--font-soft);
  font-size: clamp(24px, 2.4vw, 32px);
  font-weight: 800;
  letter-spacing: -0.4px;
}

.title-spark {
  width: 20px;
  height: 20px;
  margin-left: 8px;
  object-fit: contain;
  vertical-align: 6px;
  opacity: 0.85;
}

.bh-sub {
  margin: 5px 0 0;
  color: #9a7ba6;
  font-size: 14px;
}

.bh-date {
  align-self: start;
  padding: 7px 14px;
  border-radius: 999px;
  background: rgba(255, 255, 255, 0.55);
  color: #8a5c86;
  font-family: var(--font-ui);
  font-size: 13px;
  font-weight: 700;
  white-space: nowrap;
}

.board-grid {
  display: grid;
  grid-template-columns: minmax(0, 1.05fr) minmax(0, 0.95fr);
  grid-template-areas:
    'oneline tags'
    'flow hard'
    'flow comfort';
  gap: 16px;
  margin-bottom: 18px;
}

.card {
  min-width: 0;
  padding: 16px 18px;
  border: 1px solid rgba(255, 250, 248, 0.72);
  border-radius: 20px;
  background: rgba(255, 250, 247, 0.46);
  box-shadow:
    0 8px 22px rgba(150, 90, 120, 0.1),
    inset 0 1px 0 rgba(255, 255, 255, 0.64);
}

.card-oneline {
  grid-area: oneline;
  background: rgba(255, 251, 246, 0.6);
}

.card-tags {
  grid-area: tags;
}

.card-flow {
  grid-area: flow;
}

.card-hard {
  grid-area: hard;
  background: rgba(233, 224, 245, 0.62);
}

.card-comfort {
  position: relative;
  grid-area: comfort;
  overflow: hidden;
  background: rgba(247, 214, 220, 0.6);
}

.card-title {
  display: flex;
  align-items: center;
  gap: 8px;
  margin: 0 0 12px;
  color: #6a4270;
  font-family: var(--font-soft);
  font-size: 17px;
  font-weight: 800;
}

.card-title img {
  width: 24px;
  height: 24px;
  object-fit: contain;
}

.card-title em {
  color: #a382ab;
  font-size: 12.5px;
  font-style: normal;
  font-weight: 600;
}

.card-empty {
  margin: 0;
  color: #9a7fa0;
  font-size: 13.5px;
  line-height: 1.6;
}

.card-oneline .oneline {
  padding: 12px 14px;
  border: 1.5px dashed rgba(190, 140, 160, 0.5);
  border-radius: 14px;
  background: rgba(255, 252, 249, 0.5);
}

.oneline {
  margin: 0;
  color: #5c4660;
  font-size: 16px;
  line-height: 1.7;
}

.oneline-heart {
  width: 22px;
  height: 22px;
  margin-left: 4px;
  vertical-align: middle;
}

.tag-cloud {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.mind-tag {
  padding: 8px 14px;
  border: 1px solid transparent;
  border-radius: 999px;
  font-family: var(--font-ui);
  font-size: 13.5px;
  font-weight: 600;
  line-height: 1.3;
}

.mind-tag.is-stress {
  background: rgba(232, 160, 185, 0.4);
  color: #9c4d6a;
}

.mind-tag.is-relief {
  background: rgba(170, 160, 225, 0.42);
  color: #574f9c;
}

.mind-tag.is-primary {
  box-shadow: 0 4px 12px rgba(95, 70, 120, 0.12);
}

.mind-tag.is-stress.is-secondary {
  border-color: rgba(156, 77, 106, 0.28);
  background: rgba(255, 250, 252, 0.54);
  color: #7c5665;
  box-shadow: none;
}

.mind-tag.is-relief.is-secondary {
  border-color: rgba(87, 79, 156, 0.28);
  background: rgba(250, 249, 255, 0.56);
  color: #625d88;
  box-shadow: none;
}

.mind-tag.is-muted {
  background: rgba(200, 185, 205, 0.5);
  color: #7d6787;
}

.flow-sub {
  margin: -4px 0 10px;
  color: #8a728f;
  font-size: 13px;
}

.flow-legend {
  display: flex;
  flex-wrap: wrap;
  gap: 16px;
  margin-bottom: 10px;
}

.lg {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  color: #6f5f79;
  font-family: var(--font-ui);
  font-size: 12.5px;
}

.lg i {
  width: 11px;
  height: 11px;
  border-radius: 50%;
}

.lg.tone-neg i {
  background: #8f7bd6;
}

.lg.tone-neu i {
  background: #d29ecf;
}

.lg.tone-pos i {
  background: #f4a35f;
}

.flow-stage {
  position: relative;
  width: 100%;
  height: 150px;
}

.flow-svg {
  position: absolute;
  inset: 0;
  width: 100%;
  height: 100%;
}

.flow-line {
  fill: none;
  stroke: url(#flowStroke);
  stroke-width: 4;
  stroke-linecap: round;
}

.flow-dots {
  position: absolute;
  inset: 0;
}

.flow-dot {
  position: absolute;
  width: 15px;
  height: 15px;
  border-radius: 50%;
  background: #fff;
  box-shadow: 0 3px 8px rgba(120, 70, 120, 0.28);
  transform: translate(-50%, -50%);
}

.flow-dot.tone-pos {
  background: #f4a35f;
}

.flow-dot.tone-neu {
  background: #d29ecf;
}

.flow-dot.tone-neg {
  background: #8f7bd6;
}

.flow-dot small {
  position: absolute;
  top: 20px;
  left: 50%;
  color: #7c6a86;
  font-family: var(--font-ui);
  font-size: 11px;
  white-space: nowrap;
  transform: translateX(-50%);
}

.hard-list {
  display: grid;
  gap: 8px;
  margin: 0;
  padding: 0;
  list-style: none;
}

.hard-list li {
  position: relative;
  padding-left: 18px;
  color: #5f4a68;
  font-size: 14.5px;
  line-height: 1.55;
}

.hard-list li::before {
  content: '♪';
  position: absolute;
  left: 0;
  color: #9a7bc0;
}

.hard-empty::before {
  content: '·' !important;
}

.comfort-quote {
  margin: 0;
  padding-right: 76px;
  color: #8a4c84;
  font-size: 16px;
  font-weight: 600;
  line-height: 1.7;
  white-space: pre-line;
}

.comfort-mascot {
  position: absolute;
  right: 12px;
  bottom: 10px;
  width: 62px;
  height: 62px;
  object-fit: contain;
}

.suggest-block {
  padding: 18px 18px 16px;
  border: 1px solid rgba(255, 250, 248, 0.7);
  border-radius: 20px;
  background: rgba(255, 250, 247, 0.42);
  box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.6);
}

.suggest-head {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 8px;
  margin: 0 0 14px;
  color: #6a4270;
  font-family: var(--font-soft);
  font-size: 17px;
  font-weight: 800;
}

.suggest-head img {
  width: 24px;
  height: 24px;
  object-fit: contain;
}

.suggest-head em {
  color: #9a86a6;
  font-size: 12.5px;
  font-style: normal;
  font-weight: 500;
}

.suggest-grid {
  display: grid;
  gap: 14px;
}

.suggest-card {
  display: flex;
  flex-direction: column;
  padding: 14px 15px;
  border: 1px solid rgba(255, 250, 248, 0.8);
  border-radius: 16px;
  background: linear-gradient(
    180deg,
    rgba(255, 252, 250, 0.82),
    rgba(250, 240, 246, 0.72)
  );
  box-shadow: 0 6px 16px rgba(150, 90, 120, 0.1);
}

.sc-head {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 8px;
}

.sc-mascot {
  flex: 0 0 auto;
  width: 40px;
  height: 40px;
  object-fit: contain;
}

.sc-head strong {
  color: #6a4270;
  font-size: 14.5px;
  font-weight: 800;
  line-height: 1.3;
}

.sc-reason {
  margin: 0;
  color: #6f5f79;
  font-size: 13px;
  line-height: 1.6;
}

.sc-start {
  margin-top: 12px;
  padding-top: 12px;
  border-top: 1px dashed rgba(160, 120, 170, 0.35);
}

.sc-start-label {
  display: block;
  margin-bottom: 6px;
  color: #a06bb0;
  font-family: var(--font-ui);
  font-size: 12.5px;
  font-weight: 700;
}

.sc-start p {
  display: flex;
  align-items: flex-start;
  gap: 6px;
  margin: 0;
  color: #5a4665;
  font-size: 13px;
  font-weight: 600;
  line-height: 1.55;
}

.sc-heart {
  flex: 0 0 auto;
  width: 16px;
  height: 16px;
  margin-top: 2px;
  object-fit: contain;
}

.report-actions {
  display: flex;
  align-items: center;
  justify-content: flex-end;
  flex-wrap: wrap;
  gap: 10px;
  margin-top: 18px;
  padding-top: 16px;
  border-top: 1px dashed rgba(125, 80, 130, 0.28);
}

.report-actions p {
  flex: 1 1 360px;
  margin: 0;
  color: #7b6482;
  font-size: 13px;
}

.report-actions p span {
  color: #d46f91;
}

.secondary-button {
  min-height: 40px;
  padding: 9px 18px;
  border-radius: 999px;
  font-family: var(--font-ui);
  transition: transform 0.16s ease, opacity 0.16s ease;
}

.secondary-button {
  border: 1px solid rgba(113, 72, 124, 0.34);
  background: rgba(255, 255, 255, 0.48);
  color: #6a4270;
}

.secondary-button:hover:not(:disabled) {
  transform: translateY(-1px);
}

.secondary-button:disabled {
  cursor: not-allowed;
  opacity: 0.55;
}

@media (max-width: 1040px) {
  .diary-shell {
    grid-template-columns: 1fr;
  }

  .side-body {
    max-height: 260px;
  }

  .board-grid {
    grid-template-columns: 1fr;
    grid-template-areas:
      'oneline'
      'tags'
      'flow'
      'hard'
      'comfort';
  }

  .suggest-grid {
    grid-template-columns: repeat(2, 1fr) !important;
  }
}

@media (max-width: 620px) {
  .diary-page {
    padding: 66px 12px 40px;
    background-attachment: scroll;
  }

  .board {
    padding: 20px 16px;
    border-radius: 22px;
  }

  .board-header {
    grid-template-columns: auto 1fr;
  }

  .bh-date {
    grid-column: 2;
    justify-self: start;
  }

  .suggest-grid {
    grid-template-columns: 1fr !important;
  }

  .report-actions {
    align-items: stretch;
    flex-direction: column;
  }

  .report-actions p {
    flex-basis: auto;
  }

  .secondary-button {
    width: 100%;
  }
}
</style>

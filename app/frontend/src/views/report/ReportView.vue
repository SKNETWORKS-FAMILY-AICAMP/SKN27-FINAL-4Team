<template>
  <main class="diary-page" :style="{ '--report-bg': `url(${reportBg})` }">
    <div class="diary-toolbar">
      <div class="refresh-copy">
        <p class="refresh-context" :class="{ 'has-feedback': refreshFeedback }">
        </p>
        <details class="report-criteria">
          <summary class="criteria-trigger">
            리포트를 볼 수 있는 기준
            <span class="criteria-help" aria-hidden="true">?</span>
          </summary>
          <div class="criteria-popover">
            <p>내가 챗봇에게 보낸 메시지 수를 기준으로 해요.</p>
            <ul>
              <li><strong>주간 리포트</strong><span>일주일에 5번 이상</span></li>
              <li><strong>월간 리포트</strong><span>한 달에 20번 이상</span></li>
            </ul>
          </div>
        </details>
      </div>
      <button
        type="button"
        class="refresh-button"
        :disabled="isLoading || isRefreshing"
        title="다음 정기 갱신을 기다리지 않고 최신 대화를 지금 반영합니다"
        @click="refreshReports"
      >
        <span class="refresh-icon" :class="{ spinning: isRefreshing }" aria-hidden="true">↻</span>
        {{ isRefreshing ? '반영 중' : '지금 확인' }}
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
          <p v-if="!isLoading && !hasReports" class="side-empty">아직 준비된 정기 리포트가 없어요.</p>
          <ul class="report-list">
            <li v-for="period in filteredReports" :key="period.id">
              <button
                type="button"
                class="report-item"
                :class="{ active: selectedReportId === period.id }"
                @click="selectedReportId = period.id"
              >
                <span class="ri-date"><b>{{ reportPeriodLabel(period) }}</b> · {{ periodDateLabel(period) }}</span>
                <strong class="ri-title">{{ period.title }}</strong>
                <img v-if="selectedReportId === period.id" class="ri-heart" :src="heartIcon" alt="" aria-hidden="true" />
                <span v-else class="ri-lock" aria-hidden="true">🔒</span>
              </button>
            </li>
          </ul>
        </div>
      </aside>

      <!-- ────── 보드 ────── -->
      <section ref="reportCardRef" class="board report-card" :class="{ 'is-loading': isLoading }" :aria-busy="isLoading">
        <!-- 상태 -->
        <div v-if="!isLoading && (fetchError || !currentReport)" class="board-state">
          <img :src="bubbleHeart" class="state-icon" alt="" aria-hidden="true" />
          <template v-if="fetchError"><h1>마음 리포트를 불러오지 못했어요.</h1><p>{{ fetchError }}</p></template>
          <template v-else><h1>첫 정기 리포트를 준비하고 있어요</h1><p>주간·월간 리포트는 정해진 시점에 자동으로 준비돼요. 최신 대화를 먼저 반영하고 싶다면 ‘지금 확인’을 이용해 주세요.</p></template>
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
              <p class="bh-sub">이번 기간에 이어진 마음의 흐름을 차분히 돌아봐요.</p>
            </div>
            <span class="bh-date">{{ reportPeriodLabel(currentReport) }} · {{ headerDate }}</span>
          </header>


          <div class="board-grid">
            <!-- 이번 기간의 한 줄 -->
            <section class="card card-oneline">
              <h2 class="card-title"><img :src="feather" alt="" aria-hidden="true" />이번 기간의 한 줄</h2>
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
              <p class="flow-sub">날짜마다 달라진 마음의 높낮이를 하나의 멜로디로 이었어요. 위쪽은 가벼웠던 날, 아래쪽은 버거웠던 날이에요.</p>
              <div v-if="emotionPoints.length" class="flow-stage">
                <div class="flow-scale" aria-hidden="true">
                  <span :style="flowScaleLabelStyle(FLOW_LIGHT_LABEL_Y)">가벼웠던 날</span>
                  <span :style="flowScaleLabelStyle(FLOW_STEADY_LABEL_Y)">잔잔했던 날</span>
                  <span :style="flowScaleLabelStyle(FLOW_HEAVY_LABEL_Y)">버거웠던 날</span>
                </div>
                <svg class="flow-svg" :viewBox="`0 0 ${FLOW_W} ${FLOW_H}`" preserveAspectRatio="none" aria-hidden="true">
                  <defs>
                    <linearGradient
                      v-for="segment in emotionSegments"
                      :id="segment.gradientId"
                      :key="segment.gradientId"
                      :x1="segment.x1"
                      :y1="segment.y1"
                      :x2="segment.x2"
                      :y2="segment.y2"
                      gradientUnits="userSpaceOnUse"
                    >
                      <stop offset="0%" :stop-color="segment.fromColor" />
                      <stop offset="100%" :stop-color="segment.toColor" />
                    </linearGradient>
                  </defs>
                  <rect
                    :x="FLOW_PLOT_LEFT"
                    :y="FLOW_PLOT_TOP"
                    :width="FLOW_W - FLOW_PLOT_LEFT - FLOW_PLOT_RIGHT"
                    :height="FLOW_LIGHT_BOUNDARY_Y - FLOW_PLOT_TOP"
                    class="flow-zone is-light-zone"
                  />
                  <rect
                    :x="FLOW_PLOT_LEFT"
                    :y="FLOW_LIGHT_BOUNDARY_Y"
                    :width="FLOW_W - FLOW_PLOT_LEFT - FLOW_PLOT_RIGHT"
                    :height="FLOW_HEAVY_BOUNDARY_Y - FLOW_LIGHT_BOUNDARY_Y"
                    class="flow-zone is-steady-zone"
                  />
                  <rect
                    :x="FLOW_PLOT_LEFT"
                    :y="FLOW_HEAVY_BOUNDARY_Y"
                    :width="FLOW_W - FLOW_PLOT_LEFT - FLOW_PLOT_RIGHT"
                    :height="FLOW_PLOT_BOTTOM - FLOW_HEAVY_BOUNDARY_Y"
                    class="flow-zone is-heavy-zone"
                  />
                  <line
                    :x1="FLOW_PLOT_LEFT"
                    :x2="FLOW_W - FLOW_PLOT_RIGHT"
                    :y1="FLOW_LIGHT_BOUNDARY_Y"
                    :y2="FLOW_LIGHT_BOUNDARY_Y"
                    class="flow-guide"
                  />
                  <line
                    :x1="FLOW_PLOT_LEFT"
                    :x2="FLOW_W - FLOW_PLOT_RIGHT"
                    :y1="FLOW_HEAVY_BOUNDARY_Y"
                    :y2="FLOW_HEAVY_BOUNDARY_Y"
                    class="flow-guide"
                  />
                  <line
                    :x1="FLOW_PLOT_LEFT"
                    :x2="FLOW_W - FLOW_PLOT_RIGHT"
                    :y1="FLOW_PLOT_BOTTOM"
                    :y2="FLOW_PLOT_BOTTOM"
                    class="flow-x-axis-line"
                  />
                  <path
                    v-for="segment in emotionSegments"
                    :key="segment.pathKey"
                    :d="segment.path"
                    :stroke="`url(#${segment.gradientId})`"
                    class="flow-line"
                  />
                </svg>
                <div class="flow-dots">
                  <div
                    v-for="(p, i) in emotionPoints"
                    :key="p.day + i"
                    class="flow-dot"
                    :style="{
                      left: `${(p.x / FLOW_W) * 100}%`,
                      top: `${(p.y / FLOW_H) * 100}%`,
                      backgroundColor: p.color,
                    }"
                    :aria-label="`${p.day}, ${p.band}`"
                  ></div>
                </div>
                <div class="flow-date-axis" aria-hidden="true">
                  <span
                    v-for="(p, i) in emotionPoints"
                    :key="`flow-date-${p.day}-${i}`"
                    :style="{
                      left: `${(p.x / FLOW_W) * 100}%`,
                      top: `${(FLOW_DATE_LABEL_Y / FLOW_H) * 100}%`,
                    }"
                  >{{ p.day }}</span>
                </div>
              </div>
              <p v-else-if="hasUnscoredEmotions" class="card-empty">이 기록은 다음 정기 갱신에 새로운 멜로디로 반영돼요. 먼저 보고 싶다면 ‘지금 확인’을 이용해 주세요.</p>
              <p v-else class="card-empty">감정 기록이 더 쌓이면 이곳에 멜로디가 그려져요.</p>
            </section>

            <!-- 마음이 놓였던 장면 -->
            <section class="card card-relief">
              <h2 class="card-title"><img :src="heartIcon" alt="" aria-hidden="true" />마음이 놓였던 장면 <em>(편안한 화음)</em></h2>
              <p v-if="reliefHarmony" class="harmony-passage">
                <span v-if="reliefHarmonyDate" class="harmony-date">{{ reliefHarmonyDate }} ·</span>{{ reliefHarmony }}
              </p>
              <p v-else class="moment-empty">마음이 놓였던 장면은 기록이 조금 더 쌓이면 들려드릴게요.</p>
            </section>

            <!-- 마음이 무거워졌던 장면 -->
            <section class="card card-hard">
              <h2 class="card-title"><img :src="catIcon" alt="" aria-hidden="true" />마음이 무거워졌던 장면 <em>(불협화음)</em></h2>
              <p v-if="hardHarmony" class="harmony-passage">
                <span v-if="hardHarmonyDate" class="harmony-date">{{ hardHarmonyDate }} ·</span>{{ hardHarmony }}
              </p>
              <p v-else class="moment-empty">마음이 무거워졌던 장면은 아직 뚜렷하게 보이지 않아요.</p>
            </section>
          </div>

          <!-- 작은 제안 -->
          <section class="suggest-block">
            <h2 class="suggest-head">
              <img :src="sparkle" alt="" aria-hidden="true" />작은 제안
              <em>{{ suggestionWindowDescription }}</em>
            </h2>
            <div v-if="suggestCards.length" class="suggest-grid" :style="{ gridTemplateColumns: `repeat(${suggestCards.length}, 1fr)` }">
              <article v-for="(card, index) in suggestCards" :key="card.title + index" class="suggest-card">
                <div class="sc-head">
                  <img class="sc-mascot" :src="mascotFor(index)" alt="" aria-hidden="true" />
                  <strong>{{ card.title || '작은 실천' }}</strong>
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
          <button
            type="button"
            class="secondary-button pdf-button"
            :disabled="!currentReport || isPdfSaving"
            :aria-busy="isPdfSaving"
            title="현재 마음 리포트를 예시 이미지와 같은 구성의 PDF로 저장합니다"
            @click="saveCurrentReportAsPdf"
          >{{ isPdfSaving ? 'PDF 준비 중...' : 'PDF 저장' }}</button>
        </footer>

      </section>
    </section>

  </main>
</template>

<script setup>
import { computed, onMounted, ref, watch } from 'vue'
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

import { saveMindReportAsPdf } from './reportPdfSaver.js'

const mascots = [flowRedpanda, flowOtter, flowBird, flowCat]
const mascotFor = (index) => mascots[index % mascots.length]

const reports = ref([])
const isLoading = ref(true)
const isRefreshing = ref(false)
const fetchError = ref('')
const refreshFeedback = ref('')
const isMonthFilterOpen = ref(false)
const selectedMonth = ref('')
const selectedReportId = ref(null)
const reportCardRef = ref(null)
const isPdfSaving = ref(false)

const normalizeReport = (report) => ({
  ...report,
  stressCauses: Array.isArray(report?.stressCauses) ? report.stressCauses : [],
  reliefCauses: Array.isArray(report?.reliefCauses) ? report.reliefCauses : [],
  causeLabels: Array.isArray(report?.causeLabels) ? report.causeLabels : [],
  hardMoments: Array.isArray(report?.hardMoments) ? report.hardMoments : [],
  reliefMoments: Array.isArray(report?.reliefMoments) ? report.reliefMoments : [],
  stressReport: String(report?.stressReport ?? '').trim(),
  reliefReport: String(report?.reliefReport ?? '').trim(),
  emotions: Array.isArray(report?.emotions) ? report.emotions : [],
  emotionScale: report?.emotionScale && typeof report.emotionScale === 'object'
    ? report.emotionScale
    : null,
  analysis: Array.isArray(report?.analysis) ? report.analysis : [],
  recommendations: Array.isArray(report?.recommendations) ? report.recommendations : [],
  suggestionCards: Array.isArray(report?.suggestionCards) ? report.suggestionCards : [],
  generatedAt: String(report?.generatedAt ?? report?.createdAt ?? '').trim(),
  comfortMessage: String(report?.comfortMessage ?? report?.summary ?? '').trim(),
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

const reportPeriodLabel = (report) => (
  String(report?.type ?? '').includes('월간') ? '월간 리포트' : '주간 리포트'
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

    const valueAfterLabel = (line, labels) => {
      for (const label of labels) {
        const index = line.indexOf(label)
        if (index >= 0) {
          return line
            .slice(index + label.length)
            .replace(/^[\s:?-]*/, '')
            .trim()
        }
      }
      return null
    }

    for (const raw of analysis) {
      const line = String(raw).trim()

      if (line.startsWith('✅')) {
        currentCard = {
          title: line.replace(/^✅\s*/, ''),
          reason: '',
          how: '',
          sourceCandidate: '',
          relatedCause: '',
          timing: '',
        }
        cards.push(currentCard)
      } else if (!currentCard && line) {
        reflections.push(line)
      } else if (currentCard) {
        const reason = valueAfterLabel(
          line,
          ['왜 추천하나요?', '웹 추천 이유'],
        )
        const how = valueAfterLabel(
          line,
          ['어떻게 시작할까요?', '가볍게 시작하기'],
        )
        const relatedCause = valueAfterLabel(line, ['연결된 마음의 원인'])
        const timing = valueAfterLabel(line, ['제안 시점'])
        const sourceCandidate = valueAfterLabel(line, ['감정 흐름 후보'])

        if (reason !== null) currentCard.reason = reason
        if (how !== null) currentCard.how = how
        if (relatedCause !== null) currentCard.relatedCause = relatedCause
        if (timing !== null) currentCard.timing = timing
        if (sourceCandidate !== null) currentCard.sourceCandidate = sourceCandidate
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

const hardHarmony = computed(() => {
  const report = currentReport.value
  if (!report) return ''
  if (report.is_fallback) return '기록이 조금 더 모이면 마음을 힘들게 한 흐름도 알려드릴게요.'
  return report.stressReport
    || String(report.hardMoments?.[0]?.text ?? '').trim()
})

const reliefHarmony = computed(() => {
  const report = currentReport.value
  if (!report) return ''
  if (report.is_fallback) return '기록이 조금 더 모이면 마음을 편안하게 해준 흐름도 알려드릴게요.'
  return report.reliefReport
    || String(report.reliefMoments?.[0]?.text ?? '').trim()
})

const compactEvidenceDate = (moments, reportText) => {
  const dates = [...new Set(
    (moments ?? [])
      .flatMap((moment) => moment?.evidenceDates ?? [])
      .map((value) => String(value ?? '').trim())
      .filter(Boolean),
  )].sort()

  const formatted = dates
    .map((value) => {
      const match = value.match(/^(\d{4})[-./](\d{1,2})[-./](\d{1,2})/)
      if (!match) return null
      return {
        raw: value,
        iso: `${match[1]}-${String(match[2]).padStart(2, '0')}-${String(match[3]).padStart(2, '0')}`,
        label: `${Number(match[2])}월 ${Number(match[3])}일`,
        dotted: `${match[1]}.${String(match[2]).padStart(2, '0')}.${String(match[3]).padStart(2, '0')}`,
      }
    })
    .filter(Boolean)

  const text = String(reportText ?? '')
  if (formatted.some((date) => text.includes(date.label) || text.includes(date.raw) || text.includes(date.iso) || text.includes(date.dotted))) {
    return ''
  }

  const labels = formatted.map((date) => date.label)
  if (labels.length <= 2) return labels.join(' · ')
  return `${labels.slice(0, 2).join(' · ')} 외 ${labels.length - 2}일`
}

const hardHarmonyDate = computed(() => compactEvidenceDate(
  currentReport.value?.hardMoments,
  hardHarmony.value,
))

const reliefHarmonyDate = computed(() => compactEvidenceDate(
  currentReport.value?.reliefMoments,
  reliefHarmony.value,
))

const structuredSuggestCards = computed(() => (
  (currentReport.value?.suggestionCards ?? [])
    .map((card) => ({
      title: String(card?.title ?? '').trim(),
      reason: String(card?.reason ?? '').trim(),
      how: String(card?.how ?? '').trim(),
      sourceCandidate: String(card?.sourceCandidate ?? card?.source_candidate ?? '').trim(),
      relatedCause: String(card?.relatedCause ?? card?.related_cause ?? '').trim(),
      timing: String(card?.timing ?? '').trim(),
    }))
    .filter((card) => card.title && card.reason)
    .slice(0, 3)
))

const suggestCards = computed(() => (
  structuredSuggestCards.value.length
    ? structuredSuggestCards.value
    : parsedAnalysis.value.cards.slice(0, 3)
))

const suggestionWindowDescription = computed(() => {
  const report = currentReport.value
  const isMonthly = String(report?.type ?? '').includes('월간')
  const parsed = report?.generatedAt ? new Date(report.generatedAt) : null
  const hasGeneratedDate = parsed && !Number.isNaN(parsed.getTime())
  const dateLabel = hasGeneratedDate
    ? `${parsed.getMonth() + 1}월 ${parsed.getDate()}일부터 `
    : '이 리포트가 만들어진 뒤 '

  return isMonthly
    ? `${dateLabel}4주 동안 천천히 이어가도록 준비한 활동이에요.`
    : `${dateLabel}일주일 동안 가볍게 시도하도록 준비한 활동이에요.`
})

const FLOW_W = 640
const FLOW_H = 200
const FLOW_SCORE_MIN = 30
const FLOW_SCORE_MAX = 70
const FLOW_PLOT_LEFT = 148
const FLOW_PLOT_RIGHT = 28
const FLOW_PLOT_TOP = 22
const FLOW_PLOT_BOTTOM = 166
const FLOW_DATE_LABEL_Y = 177
const DEFAULT_EMOTION_SCALE = Object.freeze({ heavyMax: 45, lightMin: 55 })
const FLOW_BAND_COLORS = Object.freeze({
  heavy: '#a7a3e5',
  steady: '#e7b1cb',
  light: '#f5be87',
})

const emotionScore = (emotion) => {
  const rawScore = emotion?.emotion_score
  if (rawScore === null || rawScore === undefined || rawScore === '') return null

  const score = Number(rawScore)
  return Number.isFinite(score) ? score : null
}

const moodLevel = (score) => {
  const normalized = (score - FLOW_SCORE_MIN) / (FLOW_SCORE_MAX - FLOW_SCORE_MIN)
  return Math.max(0, Math.min(1, normalized))
}

const scoreY = (score) => (
  FLOW_PLOT_BOTTOM - moodLevel(score) * (FLOW_PLOT_BOTTOM - FLOW_PLOT_TOP)
)

const emotionScale = computed(() => {
  const heavyMax = Number(currentReport.value?.emotionScale?.heavyMax)
  const lightMin = Number(currentReport.value?.emotionScale?.lightMin)
  if (
    Number.isFinite(heavyMax)
    && Number.isFinite(lightMin)
    && heavyMax < lightMin
  ) {
    return { heavyMax, lightMin }
  }
  return DEFAULT_EMOTION_SCALE
})

const FLOW_LIGHT_BOUNDARY_Y = computed(() => scoreY(emotionScale.value.lightMin))
const FLOW_HEAVY_BOUNDARY_Y = computed(() => scoreY(emotionScale.value.heavyMax))
const FLOW_LIGHT_LABEL_Y = computed(() => (
  (FLOW_PLOT_TOP + FLOW_LIGHT_BOUNDARY_Y.value) / 2
))
const FLOW_STEADY_LABEL_Y = computed(() => (
  (FLOW_LIGHT_BOUNDARY_Y.value + FLOW_HEAVY_BOUNDARY_Y.value) / 2
))
const FLOW_HEAVY_LABEL_Y = computed(() => (
  (FLOW_HEAVY_BOUNDARY_Y.value + FLOW_PLOT_BOTTOM) / 2
))

const flowScaleLabelStyle = (y) => ({
  top: `${(y / FLOW_H) * 100}%`,
})

const moodBand = (score) => {
  if (score > emotionScale.value.lightMin) return 'light'
  if (score < emotionScale.value.heavyMax) return 'heavy'
  return 'steady'
}

const moodBandLabel = (score) => {
  const band = moodBand(score)
  if (band === 'light') return '한결 가벼운 날'
  if (band === 'heavy') return '조금 버거운 날'
  return '대체로 잔잔한 날'
}

const moodColor = (score) => FLOW_BAND_COLORS[moodBand(score)]

const emotionPoints = computed(() => {
  const list = (currentReport.value?.emotions ?? [])
    .map((day) => ({ day, score: emotionScore(day) }))
    .filter(({ score }) => score !== null)
  if (!list.length) return []

  const count = list.length
  const usableWidth = FLOW_W - FLOW_PLOT_LEFT - FLOW_PLOT_RIGHT

  return list.map(({ day, score }, index) => {
    const level = moodLevel(score)
    const x = count === 1
      ? FLOW_PLOT_LEFT + usableWidth / 2
      : FLOW_PLOT_LEFT + (usableWidth * index) / (count - 1)
    const y = FLOW_PLOT_BOTTOM - level * (FLOW_PLOT_BOTTOM - FLOW_PLOT_TOP)

    return {
      x,
      y,
      day: day.day,
      color: moodColor(score),
      band: moodBandLabel(score),
    }
  })
})

const hasUnscoredEmotions = computed(() => (
  (currentReport.value?.emotions?.length ?? 0) > 0
  && emotionPoints.value.length === 0
))

const emotionSegments = computed(() => emotionPoints.value.slice(0, -1).map(
  (current, index) => {
    const next = emotionPoints.value[index + 1]
    const middleX = (current.x + next.x) / 2
    return {
      gradientId: `flow-segment-gradient-${index}`,
      pathKey: `flow-segment-path-${current.day}-${next.day}-${index}`,
      x1: current.x,
      y1: current.y,
      x2: next.x,
      y2: next.y,
      fromColor: current.color,
      toColor: next.color,
      path: `M ${current.x} ${current.y} C ${middleX} ${current.y}, ${middleX} ${next.y}, ${next.x} ${next.y}`,
    }
  },
))

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
    refreshFeedback.value = ''
    const data = await reportApi.refreshReports()
    applyReports(data)
    fetchError.value = ''
    refreshFeedback.value = data?.message || '최신 대화를 반영한 리포트를 확인했어요.'
  } catch (error) {
    refreshFeedback.value = error?.message ?? '최신 대화를 지금 반영하지 못했어요. 기존 정기 리포트는 그대로 볼 수 있어요.'
    console.error('Failed to refresh reports:', error)
  } finally {
    isRefreshing.value = false
  }
}

const saveCurrentReportAsPdf = async () => {
  if (!currentReport.value || isPdfSaving.value) return

  try {
    isPdfSaving.value = true
    await saveMindReportAsPdf({
      element: reportCardRef.value,
      filename: [
        '마음리포트',
        currentReport.value.type,
        currentReport.value.range,
      ].filter(Boolean).join('_'),
    })
  } catch (error) {
    const message = error instanceof Error
      ? error.message
      : '마음 리포트 PDF 파일을 만들지 못했습니다.'
    window.alert(message)
  } finally {
    isPdfSaving.value = false
  }
}

onMounted(() => {
  loadReports()
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
  align-items: center;
  justify-content: space-between;
  gap: 20px;
  width: min(1400px, 100%);
  margin: 0 auto 12px;
}

.refresh-copy {
  display: grid;
  gap: 6px;
  min-width: 0;
}

.refresh-context {
  margin: 0;
  color: rgba(255, 248, 255, 0.82);
  font-size: 12.5px;
  line-height: 1.5;
}

.refresh-context.has-feedback {
  color: #fff8df;
}

.report-criteria {
  position: relative;
  width: fit-content;
  margin: 0;
  color: rgba(255, 248, 255, 0.92);
  font-size: 13px;
  line-height: 1.5;
}

.criteria-trigger {
  display: inline-flex;
  align-items: center;
  gap: 7px;
  min-height: 24px;
  padding: 2px 9px;
  border: 1px solid rgba(255, 221, 188, 0.5);
  border-radius: 999px;
  background: rgba(255, 245, 221, 0.13);
  color: #fff3cf;
  cursor: pointer;
  font-size: 11.5px;
  font-weight: 800;
  letter-spacing: 0.01em;
  list-style: none;
}

.criteria-trigger::-webkit-details-marker {
  display: none;
}

.criteria-trigger:hover {
  border-color: rgba(255, 236, 208, 0.85);
  background: rgba(255, 245, 221, 0.2);
}

.criteria-trigger:focus-visible {
  outline: 2px solid #fff3cf;
  outline-offset: 3px;
}

.criteria-help {
  display: inline-grid;
  width: 17px;
  height: 17px;
  place-items: center;
  border: 1px solid currentColor;
  border-radius: 50%;
  font-size: 10px;
  line-height: 1;
}

.criteria-popover {
  position: absolute;
  top: calc(100% + 9px);
  left: 0;
  z-index: 30;
  width: min(360px, calc(100vw - 40px));
  padding: 15px 16px;
  border: 1px solid rgba(255, 226, 199, 0.72);
  border-radius: 14px;
  background: rgba(45, 25, 67, 0.97);
  color: #fffaf4;
  box-shadow: 0 16px 38px rgba(10, 4, 23, 0.38);
}

.criteria-popover::before {
  position: absolute;
  top: -6px;
  left: 24px;
  width: 10px;
  height: 10px;
  border-top: 1px solid rgba(255, 226, 199, 0.72);
  border-left: 1px solid rgba(255, 226, 199, 0.72);
  background: rgba(45, 25, 67, 0.97);
  content: "";
  transform: rotate(45deg);
}

.criteria-popover p {
  margin: 0 0 10px;
  color: rgba(255, 250, 244, 0.82);
  font-size: 12.5px;
}

.criteria-popover ul {
  display: grid;
  gap: 7px;
  margin: 0;
  padding: 0;
  list-style: none;
}

.criteria-popover li {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 18px;
}

.criteria-popover li span {
  color: #fff3cf;
  white-space: nowrap;
}

.report-criteria strong {
  color: #fffaf4;
  font-weight: 800;
}

.refresh-button {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  flex: 0 0 auto;
  gap: 9px;
  min-width: 132px;
  min-height: 48px;
  padding: 10px 21px;
  border: 2px solid rgba(255, 225, 205, 0.88);
  border-radius: 999px;
  background: linear-gradient(135deg, rgba(140, 89, 152, 0.96), rgba(105, 62, 130, 0.96));
  color: #fffdf7;
  font-size: 14px;
  font-weight: 800;
  letter-spacing: 0.01em;
  box-shadow:
    0 0 0 3px rgba(255, 212, 190, 0.13),
    0 10px 28px rgba(8, 3, 20, 0.35);
  transition:
    transform 0.16s ease,
    border-color 0.16s ease,
    box-shadow 0.16s ease,
    filter 0.16s ease;
}

.refresh-button:disabled {
  cursor: wait;
  opacity: 0.62;
}

.refresh-button:hover:not(:disabled) {
  border-color: #fff3d7;
  box-shadow:
    0 0 0 4px rgba(255, 212, 190, 0.22),
    0 13px 30px rgba(8, 3, 20, 0.42);
  filter: brightness(1.08);
  transform: translateY(-2px);
}

.refresh-button:active:not(:disabled) {
  transform: translateY(0);
}

.refresh-button:focus-visible {
  outline: 3px solid #fff3cf;
  outline-offset: 3px;
}

.refresh-icon {
  font-size: 20px;
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

.ri-date b {
  color: #f1dce9;
  font-weight: 700;
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
    'flow relief'
    'flow hard';
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
  background: rgba(247, 214, 220, 0.6);
}

.card-relief {
  grid-area: relief;
  background: rgba(233, 224, 245, 0.62);
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

.flow-stage {
  position: relative;
  width: 100%;
  height: 200px;
}

.flow-scale {
  position: absolute;
  inset: 0 auto 0 0;
  z-index: 1;
  width: 20%;
  color: #796783;
  font-family: var(--font-ui);
  font-size: clamp(9.5px, 1.15vw, 11.5px);
  line-height: 1.45;
}

.flow-scale span {
  position: absolute;
  left: 0;
  white-space: nowrap;
  transform: translateY(-50%);
}

.flow-svg {
  position: absolute;
  inset: 0;
  width: 100%;
  height: 100%;
}

.flow-line {
  fill: none;
  stroke-width: 4;
  stroke-linecap: round;
}

.flow-zone {
  stroke: none;
}

.flow-zone.is-light-zone {
  fill: rgba(249, 211, 174, 0.2);
}

.flow-zone.is-steady-zone {
  fill: rgba(238, 196, 216, 0.18);
}

.flow-zone.is-heavy-zone {
  fill: rgba(195, 191, 235, 0.18);
}

.flow-guide {
  stroke: rgba(126, 101, 147, 0.2);
  stroke-width: 1;
  stroke-dasharray: 5 7;
}

.flow-x-axis-line {
  stroke: rgba(112, 91, 130, 0.28);
  stroke-width: 1;
}

.flow-dots {
  position: absolute;
  inset: 0;
}

.flow-dot {
  position: absolute;
  width: 15px;
  height: 15px;
  box-sizing: border-box;
  border: 2px solid rgba(255, 255, 255, 0.92);
  border-radius: 50%;
  background: #fff;
  box-shadow: 0 3px 8px rgba(120, 70, 120, 0.28);
  transform: translate(-50%, -50%);
}

.flow-date-axis {
  position: absolute;
  inset: 0;
  pointer-events: none;
}

.flow-date-axis span {
  position: absolute;
  color: #7c6a86;
  font-family: var(--font-ui);
  font-size: 11px;
  white-space: nowrap;
  transform: translateX(-50%);
}

.harmony-passage {
  position: relative;
  margin: 0;
  padding: 4px 4px 4px 27px;
  color: #5f4a68;
  font-size: 14.5px;
  line-height: 1.82;
  text-wrap: pretty;
}

.harmony-passage::before {
  content: '∿';
  position: absolute;
  top: 4px;
  left: 0;
  color: rgba(132, 96, 151, 0.68);
  font-family: var(--font-soft);
  font-size: 22px;
  line-height: 1;
}

.harmony-date {
  display: inline-block;
  margin-right: 8px;
  color: #76547f;
  font-family: var(--font-ui);
  font-size: 11.5px;
  font-weight: 700;
  white-space: nowrap;
}

.card-hard .harmony-date {
  color: #965a75;
}

.card-hard .harmony-passage {
  color: #80516f;
}

.card-hard .harmony-passage::before {
  color: rgba(190, 101, 137, 0.7);
}

.moment-empty {
  margin: 0;
  padding: 8px 2px;
  color: #927b98;
  font-size: 13.5px;
  line-height: 1.65;
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

.pdf-button {
  border-color: rgba(126, 91, 170, 0.38);
  background: linear-gradient(135deg, rgba(239, 225, 251, 0.9), rgba(255, 235, 226, 0.9));
  color: #65446f;
  font-weight: 800;
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
      'relief'
      'hard';
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

  .diary-toolbar {
    align-items: stretch;
    flex-direction: column;
    gap: 12px;
  }

  .refresh-button {
    width: 100%;
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

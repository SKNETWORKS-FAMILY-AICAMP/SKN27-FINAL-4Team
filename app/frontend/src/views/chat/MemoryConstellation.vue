<template>
  <div class="mc-wrap" :title="caption" role="img" :aria-label="caption + ' — 기억 별자리'">
    <svg viewBox="0 0 100 100" preserveAspectRatio="xMidYMid meet">
      <!-- 배경 잔별 — 별자리 주변을 '하늘 한 조각'처럼 채우는 이름 없는 별들 -->
      <circle v-for="(a, i) in ambient" :key="'a' + i"
              :cx="a[0]" :cy="a[1]" :r="a[2]" fill="#cbc3e6"
              class="mc-amb" :style="{ animationDelay: (i % 7) * 0.5 + 's' }" />
      <!-- 연결선 (은은한 점선) -->
      <line v-for="(l, i) in cons.lines" :key="'l' + i"
            :x1="cons.stars[l[0]][0]" :y1="cons.stars[l[0]][1]"
            :x2="cons.stars[l[1]][0]" :y2="cons.stars[l[1]][1]"
            class="mc-line" />
      <!-- 별 + 기억 라벨 -->
      <g v-for="s in starNodes" :key="s.idx"
         :class="['mc-star', { 'has-mem': !!s.mem, glow: s.mem && s.mem.glow }]"
         :style="{ animationDelay: s.delay }"
         @click="s.mem && $emit('pick', s.mem)">
        <circle :cx="s.x" :cy="s.y" :r="s.mem ? 2.1 : 1.1"
                :fill="s.mem ? s.mem.color : '#cbc3e6'" />
        <circle v-if="s.mem" :cx="s.x" :cy="s.y" r="4.2"
                :fill="s.mem.color" opacity="0.18" />
        <text v-if="s.mem" :x="labelX(s.x)" :y="s.y + 8.5" class="mc-label"
              text-anchor="middle">{{ s.mem.label }}</text>
      </g>
    </svg>
    <div class="mc-caption">{{ caption }}</div>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { getSeasonConstellation } from './config/constellations'

// 기억을 실제 별자리 모양에 얹는 장식 컴포넌트 (2026-07-24, 멘토 피드백).
// 데이터는 ChatView의 memoryPanelData 그대로 — 새 API 없음.
// 별 클릭 → pick 이벤트 (ChatView가 입력창에 말 걸 문구를 채움).
const props = defineProps({
  panelData: { type: Object, required: true },   // { upcoming, people, prefs, recent }
  glowName: { type: String, default: null },     // 방금 저장된 기억 반짝임 연동
})
defineEmits(['pick'])

const cons = getSeasonConstellation()

// 배경 잔별 — 매번 같은 자리(고정 시드 대신 상수 배열)라 화면이 안 어수선함.
// 별자리 본체와 최소 거리를 둬서 모양을 해치지 않는 위치들만 골라둠.
const AMBIENT_POOL = [
  [4, 8, 1.0], [14, 4, .7], [28, 6, .9], [44, 3, .6], [58, 7, .9], [72, 4, .7],
  [88, 8, 1.0], [96, 18, .7], [3, 26, .7], [95, 40, .9], [5, 52, .9], [97, 56, .6],
  [4, 78, .8], [12, 92, .9], [30, 96, .7], [50, 94, 1.0], [68, 95, .7], [86, 92, .9],
  [96, 80, .8], [40, 88, .6],
]
// 별자리 별과 너무 가까운 잔별은 제외 (라벨·모양 보호)
const ambient = AMBIENT_POOL.filter(([ax, ay]) =>
  cons.stars.every(([sx, sy]) => (ax - sx) ** 2 + (ay - sy) ** 2 > 90))

// 라벨을 얹을 기억 목록 — 종류별 상한으로 다양성 확보, 전체는 별자리 꼭짓점 수와 6개 중 작은 쪽.
// 색·아이콘 규칙은 기존 칩/팝오버와 동일 (노랑=일정, 하늘=사람, 분홍=취향, 연보라=최근).
const memories = computed(() => {
  const d = props.panelData
  const out = []
  for (const u of (d.upcoming || []).slice(0, 2)) {
    out.push({ key: 'u' + u.name, color: '#FCD34D',
               label: u.name + (u.dday === 0 ? ' 오늘' : ' D-' + u.dday),
               ask: `${u.name} 얼마 안 남았지? 같이 얘기해줘`, name: u.name })
  }
  for (const p of (d.people || []).slice(0, 2)) {
    out.push({ key: 'p' + p.name, color: '#7dd3fc', label: p.name,
               ask: `${p.name} 얘기 기억하고 있어?`, name: p.name })
  }
  for (const t of (d.prefs || []).slice(0, 2)) {
    out.push({ key: 't' + t.topic, color: '#f9a8d4', label: t.topic,
               ask: `나 요즘 ${t.topic} 좋아하는 거 알지?`, name: t.topic })
  }
  for (const n of (d.recent || []).slice(0, 1)) {
    out.push({ key: 'r' + n, color: '#cbc3e6', label: n,
               ask: `저번에 ${n} 얘기했던 거 기억나?`, name: n })
  }
  const cap = Math.min(6, cons.labelOrder.length)
  return out.slice(0, cap).map(m => ({ ...m, glow: m.name === props.glowName }))
})

// labelOrder(겹침 방지 순서)대로 기억을 별에 배정, 남는 별은 잔별
const starNodes = computed(() => {
  const byIdx = new Map()
  memories.value.forEach((m, i) => byIdx.set(cons.labelOrder[i], m))
  return cons.stars.map(([x, y], idx) => ({
    idx, x, y, mem: byIdx.get(idx) || null,
    delay: ((idx * 0.7) % 3.4).toFixed(1) + 's',
  }))
})

const caption = computed(() =>
  `${new Date().getMonth() + 1}월의 별자리 · ${cons.ko}`)

// 라벨이 좌우로 잘리지 않게 x를 안쪽으로 조금 끌어옴
function labelX(x) { return Math.min(82, Math.max(18, x)) }
</script>

<style scoped>
.mc-wrap { pointer-events: none; user-select: none; }
.mc-wrap svg { width: 100%; height: auto; overflow: visible; display: block; }
.mc-line { stroke: #a99fd0; stroke-opacity: .32; stroke-width: .45;
           stroke-dasharray: 1.6 2.6; }
.mc-star { animation: mc-tw 3.4s ease-in-out infinite; }
.mc-star.has-mem { pointer-events: auto; cursor: pointer; }
.mc-star.has-mem:hover circle { filter: brightness(1.25); }
.mc-star.glow circle { animation: mc-glow 1.1s ease-in-out 3; }
.mc-label { font-size: 5.6px; fill: #d9d2f0; paint-order: stroke;
            stroke: rgba(20, 12, 40, .85); stroke-width: 1.6px; }
.mc-caption { text-align: center; font-size: 11px; color: #a99fd0;
              opacity: .8; margin-top: 2px; letter-spacing: .04em; }
.mc-amb { animation: mc-amb-tw 4.6s ease-in-out infinite; }
@keyframes mc-amb-tw { 0%, 100% { opacity: .35; } 50% { opacity: .8; } }
@keyframes mc-tw { 0%, 100% { opacity: .55; } 50% { opacity: 1; } }
@keyframes mc-glow { 0%, 100% { filter: brightness(1); } 50% { filter: brightness(1.9); } }
@media (prefers-reduced-motion: reduce) { .mc-star { animation: none; } }
</style>

<template>
  <div class="mc-wrap" :class="{ inactive: !active }"
       :title="active ? caption : caption + ' · ' + cons.period"
       role="img" :aria-label="caption + (active ? ' — 기억 별자리' : '')">
    <svg viewBox="0 0 100 100" preserveAspectRatio="xMidYMid meet">
      <!-- 배경 잔별 — 이번 달 별자리 주변만 '하늘 한 조각'처럼 채움 -->
      <circle v-for="(a, i) in ambient" :key="'a' + i"
              :cx="a[0]" :cy="a[1]" :r="a[2]" fill="#cbc3e6"
              class="mc-amb" :style="{ animationDelay: (i % 7) * 0.5 + 's' }" />
      <!-- 연결선 (은은한 점선) -->
      <line v-for="(l, i) in cons.lines" :key="'l' + i"
            :x1="cons.stars[l[0]][0]" :y1="cons.stars[l[0]][1]"
            :x2="cons.stars[l[1]][0]" :y2="cons.stars[l[1]][1]"
            class="mc-line" />
      <!-- 별 + 기억 라벨 (기억은 이번 달 별자리에만 얹힘) -->
      <g v-for="s in starNodes" :key="s.idx"
         :class="['mc-star', { 'has-mem': !!s.mem, glow: s.mem && s.mem.glow }]"
         :style="{ animationDelay: s.delay }"
         @click="s.mem && $emit('pick', s.mem)">
        <circle v-if="s.mem" :cx="s.x" :cy="s.y" r="7" fill="transparent" />
        <circle :cx="s.x" :cy="s.y" :r="s.mem ? 2.1 : (active ? 1.6 : 1.7)"
                :fill="s.mem ? s.mem.color : (active ? '#fff3d6' : starTint(s.idx))" />
        <circle v-if="!s.mem" :cx="s.x" :cy="s.y" r="3.4"
                :fill="active ? '#fcd34d' : starTint(s.idx)" opacity="0.16" />
        <circle v-if="s.mem" :cx="s.x" :cy="s.y" r="4.2"
                :fill="s.mem.color" opacity="0.18" />
        <text v-if="s.mem" :x="labelX(s.x)" :y="s.y + 8.5" class="mc-label"
              text-anchor="middle">{{ s.mem.label }}</text>
      </g>
    </svg>
    <div class="mc-caption">{{ caption }}<span v-if="!active" class="mc-period"> · {{ cons.period }}</span></div>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { CONSTELLATIONS, getSeasonConstellation } from './config/constellations'

// 기억을 실제 별자리 모양에 얹는 컴포넌트 (2026-07-24, 멘토 피드백).
// 12궁을 하늘에 전부 붙여 쓰는 구조: active(이번 달)만 기억 라벨+클릭+잔별,
// 나머지는 은은한 모양만. 데이터는 ChatView의 memoryPanelData 그대로 — 새 API 없음.
const props = defineProps({
  conKey: { type: String, default: null },       // 별자리 지정 (없으면 이번 달 것)
  active: { type: Boolean, default: true },      // 이번 달 여부 (점등·잔별·캡션 강조)
  memories: { type: Array, default: () => [] },  // 이 별자리에 얹을 기억들 (ChatView가 배분)
  glowName: { type: String, default: null },     // 방금 저장된 기억 반짝임 연동
})
defineEmits(['pick'])

const cons = props.conKey
  ? { key: props.conKey, ...CONSTELLATIONS[props.conKey] }
  : getSeasonConstellation()

// 이번 달이 아닌 별자리의 별 색 — 금·청·은·백이 한 별자리 안에서 섞여 빛남.
// 별자리 이름으로 시작점을 어긋나게 해서 옆 별자리끼리 패턴이 안 겹치게.
const STAR_TINTS = ['#fcd34d', '#7dd3fc', '#cbd5e1', '#f6f3ff']
const _seed = [...cons.key].reduce((a, ch) => a + ch.charCodeAt(0), 0)
function starTint(i) { return STAR_TINTS[(_seed + i) % STAR_TINTS.length] }

// 배경 잔별 (active 전용) — 고정 좌표라 화면이 안 어수선함.
const AMBIENT_POOL = [
  [4, 8, 1.0], [14, 4, .7], [28, 6, .9], [44, 3, .6], [58, 7, .9], [72, 4, .7],
  [88, 8, 1.0], [96, 18, .7], [3, 26, .7], [95, 40, .9], [5, 52, .9], [97, 56, .6],
  [4, 78, .8], [12, 92, .9], [30, 96, .7], [50, 94, 1.0], [68, 95, .7], [86, 92, .9],
  [96, 80, .8], [40, 88, .6],
]
const ambient = props.active
  ? AMBIENT_POOL.filter(([ax, ay]) =>
      cons.stars.every(([sx, sy]) => (ax - sx) ** 2 + (ay - sy) ** 2 > 90))
  : []

// 이 별자리에 얹을 기억 — 배분은 ChatView(skyAssign)가 함. 여기선 꼭짓점 수만큼만.
const memories = computed(() =>
  props.memories.slice(0, cons.labelOrder.length)
    .map(m => ({ ...m, glow: m.name === props.glowName })))

// labelOrder(겹침 방지 순서)대로 기억을 별에 배정, 남는 별은 잔별
const starNodes = computed(() => {
  const byIdx = new Map()
  memories.value.forEach((m, i) => byIdx.set(cons.labelOrder[i], m))
  return cons.stars.map(([x, y], idx) => ({
    idx, x, y, mem: byIdx.get(idx) || null,
    delay: ((idx * 0.7) % 3.4).toFixed(1) + 's',
  }))
})

const caption = computed(() => props.active
  ? `${new Date().getMonth() + 1}월의 별자리 · ${cons.ko}`
  : cons.ko)

// 라벨이 좌우로 잘리지 않게 x를 안쪽으로 조금 끌어옴
function labelX(x) { return Math.min(82, Math.max(18, x)) }
</script>

<style scoped>
.mc-wrap { pointer-events: none; user-select: none; }
.mc-wrap svg { width: 100%; height: auto; overflow: visible; display: block; }
.mc-line { stroke: #a99fd0; stroke-opacity: .32; stroke-width: .45;
           stroke-dasharray: 1.6 2.6; }

/* 이번 달 별자리 — 주인공 대접: 어두운 받침 + 금빛 무리 + 또렷한 선 */
.mc-wrap:not(.inactive) {
  background: radial-gradient(ellipse 62% 56% at 50% 45%,
              rgba(252, 211, 77, .12), rgba(16, 10, 34, .55) 52%,
              rgba(16, 10, 34, 0) 80%);
  border-radius: 16px;
  animation: mc-season 4.2s ease-in-out infinite;
}
.mc-wrap:not(.inactive) .mc-line { stroke: #d9cfa9; stroke-opacity: .6; stroke-width: .7; }
@keyframes mc-season { 0%, 100% { filter: brightness(1); } 50% { filter: brightness(1.22); } }
.mc-star { animation: mc-tw 3.4s ease-in-out infinite; }
.mc-star.has-mem { pointer-events: auto; cursor: pointer; }
.mc-star.has-mem:hover circle { filter: brightness(1.25); }
.mc-star.glow circle { animation: mc-glow 1.1s ease-in-out 3; }
.mc-label { font-size: 5.6px; fill: #d9d2f0; paint-order: stroke;
            stroke: rgba(20, 12, 40, .85); stroke-width: 1.6px;
            opacity: 0; transition: opacity .25s ease; }
.mc-star.has-mem:hover .mc-label { opacity: 1; }
.mc-star.glow .mc-label { opacity: 1; }   /* 방금 저장된 기억은 잠깐 이름 공개 */
.mc-caption { text-align: center; font-size: 11px; color: #a99fd0;
              opacity: .8; margin-top: 2px; letter-spacing: .04em; }
.mc-wrap:not(.inactive) .mc-caption { color: #fcd34d; opacity: 1; font-weight: 500;
              text-shadow: 0 0 8px rgba(252, 211, 77, .45); }
.mc-amb { animation: mc-amb-tw 4.6s ease-in-out infinite; }

/* 이번 달이 아닌 별자리 — 금·청·은·백 고유 색으로 깜빡이며 살아있음.
   배경(밝은 노을~어두운 밤) 어디서든 보이게: 별 크게 + 어두운 하늘안개 받침 */
.mc-wrap.inactive { opacity: .85; transition: opacity .3s ease; pointer-events: auto;
                    background: radial-gradient(ellipse 60% 55% at 50% 45%,
                                rgba(16, 10, 34, .5), rgba(16, 10, 34, 0) 75%);
                    border-radius: 16px; }
.mc-wrap.inactive:hover { opacity: 1; }
.mc-wrap.inactive .mc-line { stroke-opacity: .5; stroke-width: .7; }
.mc-wrap.inactive .mc-caption { opacity: .6; }
.mc-period { opacity: 0; transition: opacity .25s ease; color: #d9d2f0; }
.mc-wrap.inactive:hover .mc-period { opacity: 1; }

@keyframes mc-amb-tw { 0%, 100% { opacity: .35; } 50% { opacity: .8; } }
@keyframes mc-tw { 0%, 100% { opacity: .55; } 50% { opacity: 1; } }
@keyframes mc-glow { 0%, 100% { filter: brightness(1); } 50% { filter: brightness(1.9); } }
@media (prefers-reduced-motion: reduce) { .mc-star { animation: none; } }
</style>

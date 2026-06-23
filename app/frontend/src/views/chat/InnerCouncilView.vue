<template>
  <div class="council-page">

    <!-- 노을 배경 + 어두운 오버레이 + 중앙 스포트라이트 -->
    <div class="council-bg" :style="{ backgroundImage: `url(${chatBg})` }"></div>
    <div class="council-spot"></div>

    <!-- ① 헤더 (SCR-004 ①) -->
    <div class="council-header">
      💭 이너 카운슬 — 캐릭터들이 당신에 대해 이야기하는 중
    </div>

    <!-- ② 3캐릭터 회의 영역 (SCR-004 ②) -->
    <div class="stage">
      <div
        v-for="agent in agents"
        :key="agent.key"
        class="agent-card"
      >
        <div class="agent-face" :style="{ background: agent.bg, color: agent.color }">
          {{ agent.face }}
        </div>
        <div class="agent-name">{{ agent.name }}</div>
        <div class="agent-role">{{ agent.role }}</div>
        <div
          class="agent-talk"
          :style="{ background: agent.bg, color: agent.color }"
        >
          <template v-if="agentMessages[agent.key]">
            {{ agentMessages[agent.key] }}
          </template>
          <span v-else class="thinking">생각 중…</span>
        </div>
      </div>
    </div>

    <!-- ④ 합의 요약 카드 (SCR-004 ④) -->
    <div v-if="summaryText" class="summary-card">
      📋 합의 요약 — "{{ summaryText }}"
    </div>

    <!-- ③ 개입·지켜보기 입력 (SCR-004 ③) -->
    <div class="ctrl-bar">
      <input
        v-model="interventionText"
        class="intervention-input"
        placeholder='나도 한마디 개입하기… ("너무 잔소리하지 마")'
        :disabled="isRunning || isFinished"
        @keydown.enter.prevent="intervene"
      />
      <button
        class="btn-intervene"
        :disabled="!interventionText.trim() || isRunning || isFinished"
        @click="intervene"
      >개입</button>
      <button
        class="btn-watch"
        :disabled="isRunning || isFinished"
        @click="watchMode"
      >지켜보기</button>
    </div>

    <!-- ⑤ 백엔드 가드 안내 (SCR-004 ⑤) -->
    <div class="guard-note">
      백엔드 가드: 최대 3턴 · 합산 1,200토큰 상한,
      위기 감지 시 즉시 종료 (수동 발동만)
    </div>

    <!-- 종료 후 대화방으로 돌아가기 -->
    <div v-if="isFinished" class="finished-bar">
      <button class="back-btn" @click="goBack">← 대화방으로 돌아가기</button>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { chatApi } from '../../api/chat.js'
import chatBg from '../../assets/chat-bg.png'

const router = useRouter()
const route  = useRoute()

const sessionId = route.query.sessionId

// ── 캐릭터 정의 ──────────────────────────────────────────
const agents = [
  {
    key:   'haeon',
    name:  '해온',
    role:  '위로·내러티브',
    face:  '◠‿◠',
    color: '#5EEAD4',
    bg:    'rgba(94,234,212,0.16)',
  },
  {
    key:   'greung',
    name:  '그릉',
    role:  '직면·CBT',
    face:  '◣_◢',
    color: '#FCA5A5',
    bg:    'rgba(252,165,165,0.16)',
  },
  {
    key:   'dalkong',
    name:  '달콩',
    role:  '코치·ACT',
    face:  '◕‿◕',
    color: '#C4B5FD',
    bg:    'rgba(196,181,253,0.16)',
  },
]

const agentMessages   = ref({ haeon: '', greung: '', dalkong: '' })
const summaryText     = ref('')
const interventionText = ref('')
const isRunning       = ref(false)
const isFinished      = ref(false)
const turnCount       = ref(0)
const MAX_TURNS       = 3

// 진입 시 첫 번째 이너 카운슬 라운드 자동 실행
onMounted(() => runCouncil())

async function runCouncil(userInput = null) {
  if (turnCount.value >= MAX_TURNS) {
    isFinished.value = true
    return
  }

  isRunning.value = true
  agentMessages.value = { haeon: '', greung: '', dalkong: '' }
  summaryText.value = ''

  try {
    const result = await chatApi.runCouncil(sessionId, userInput, turnCount.value)
    agentMessages.value = result.agent_messages
    summaryText.value   = result.summary
    turnCount.value++

    if (turnCount.value >= MAX_TURNS) isFinished.value = true
  } catch (e) {
    summaryText.value = '잠시 연결이 끊겼어요. 다시 시도해 주세요.'
  } finally {
    isRunning.value = false
  }
}

function intervene() {
  const input = interventionText.value.trim()
  if (!input) return
  interventionText.value = ''
  runCouncil(input)
}

function watchMode() {
  runCouncil(null)
}

function goBack() {
  router.back()
}
</script>

<style scoped>
.council-page {
  display: flex;
  flex-direction: column;
  min-height: calc(100vh - 52px);
  position: relative;
  overflow: hidden;
}

/* 배경: 노을 + 어두운 오버레이 */
.council-bg {
  position: absolute;
  inset: 0;
  z-index: 0;
  background-size: cover;
  background-position: center 30%;
}
.council-bg::after {
  content: "";
  position: absolute;
  inset: 0;
  background: linear-gradient(180deg,
    rgba(11,4,28,0.74) 0%,
    rgba(16,7,40,0.82) 45%,
    rgba(9,4,24,0.92) 100%);
}
/* 중앙 스포트라이트 (3캐릭터에 시선 집중) */
.council-spot {
  position: absolute;
  inset: 0;
  z-index: 0;
  background: radial-gradient(ellipse 60% 42% at 50% 30%,
    rgba(196,181,253,0.18) 0%, rgba(196,181,253,0.06) 45%, transparent 70%);
  pointer-events: none;
}
.council-page > *:not(.council-bg):not(.council-spot) { position: relative; z-index: 1; }

/* 헤더 */
.council-header {
  background: rgba(83,74,183,0.22);
  color: #D8CCFF;
  font-weight: 700;
  font-size: 16px;
  text-align: center;
  padding: 16px;
  border-bottom: 1px solid rgba(192,132,252,0.2);
  backdrop-filter: blur(10px);
}

/* 3캐릭터 영역 */
.stage {
  display: flex;
  gap: 20px;
  padding: 34px 28px;
  justify-content: center;
  flex-wrap: wrap;
}

.agent-card {
  flex: 1;
  max-width: 260px;
  min-width: 200px;
  text-align: center;
}

.agent-face {
  width: 104px;
  height: 104px;
  border-radius: 26px;
  margin: 0 auto 12px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 44px;
  border: 1px solid rgba(255,255,255,0.12);
  box-shadow: 0 0 26px rgba(192,132,252,0.16);
}

.agent-name {
  font-weight: 700;
  font-size: 18px;
  color: #fff;
  margin-bottom: 3px;
}

.agent-role {
  font-size: 13px;
  color: rgba(255,255,255,0.45);
  margin-bottom: 12px;
}

.agent-talk {
  font-size: 14.5px;
  border-radius: 16px;
  padding: 13px 15px;
  line-height: 1.6;
  text-align: left;
  min-height: 80px;
  border: 1px solid rgba(255,255,255,0.1);
}

.thinking {
  color: inherit;
  opacity: 0.55;
}

/* 합의 요약 카드 */
.summary-card {
  margin: 8px 28px 20px;
  background: rgba(83,74,183,0.18);
  border: 1px dashed rgba(192,132,252,0.5);
  border-radius: 16px;
  padding: 16px 18px;
  font-size: 15px;
  color: #E9CAFF;
  line-height: 1.65;
  text-align: center;
  backdrop-filter: blur(8px);
}

/* 개입 입력 바 */
.ctrl-bar {
  display: flex;
  gap: 12px;
  align-items: center;
  margin-top: auto;
  border-top: 1px solid rgba(192,132,252,0.18);
  padding: 16px 28px;
  background: rgba(13,5,32,0.4);
  backdrop-filter: blur(20px);
}

.intervention-input {
  flex: 1;
  background: rgba(255,255,255,0.07);
  border: 1px solid rgba(255,255,255,0.15);
  border-radius: 14px;
  padding: 14px 17px;
  font-size: 15.5px;
  font-family: inherit;
  color: #fff;
}
.intervention-input::placeholder { color: rgba(255,255,255,0.32); }
.intervention-input:focus { outline: none; border-color: rgba(192,132,252,0.6); }
.intervention-input:disabled { opacity: 0.5; }

.btn-intervene {
  background: linear-gradient(135deg, #8B7DEC, #B6A7FF);
  color: #14093a;
  border-radius: 14px;
  padding: 14px 24px;
  font-size: 15.5px;
  font-weight: 700;
}
.btn-intervene:disabled { opacity: 0.35; cursor: not-allowed; }
.btn-intervene:not(:disabled):hover { opacity: 0.9; }

.btn-watch {
  background: rgba(255,255,255,0.08);
  border: 1px solid rgba(255,255,255,0.16);
  border-radius: 14px;
  padding: 14px 20px;
  font-size: 15px;
  color: rgba(255,255,255,0.75);
}
.btn-watch:disabled { opacity: 0.35; cursor: not-allowed; }
.btn-watch:not(:disabled):hover { background: rgba(255,255,255,0.15); }

/* 가드 안내 */
.guard-note {
  font-size: 12.5px;
  color: rgba(255,255,255,0.4);
  text-align: center;
  padding: 12px 16px;
  background: rgba(13,5,32,0.4);
  border-top: 1px solid rgba(192,132,252,0.12);
}

/* 종료 후 */
.finished-bar {
  display: flex;
  justify-content: center;
  padding: 16px;
  border-top: 1px solid rgba(192,132,252,0.12);
  background: rgba(13,5,32,0.4);
}
.back-btn {
  font-size: 15px;
  color: #5EEAD4;
  border: 1px solid rgba(94,234,212,0.5);
  border-radius: 12px;
  padding: 12px 24px;
  background: rgba(94,234,212,0.08);
}
.back-btn:hover { background: rgba(94,234,212,0.16); }
</style>

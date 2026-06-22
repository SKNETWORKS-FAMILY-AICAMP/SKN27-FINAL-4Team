<template>
  <div class="council-page">

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
import { chatApi } from '../api/chat.js'

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
    color: 'var(--teal)',
    bg:    'var(--tealbg)',
  },
  {
    key:   'greung',
    name:  '그릉',
    role:  '직면·CBT',
    face:  '◣_◢',
    color: 'var(--cor)',
    bg:    'var(--corbg)',
  },
  {
    key:   'dalkong',
    name:  '달콩',
    role:  '코치·ACT',
    face:  '◕‿◕',
    color: 'var(--pur)',
    bg:    'var(--purbg)',
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
  background: var(--canvas);
}

/* 헤더 */
.council-header {
  background: var(--purbg);
  color: var(--pur);
  font-weight: 700;
  font-size: 14px;
  text-align: center;
  padding: 12px;
  border-bottom: 1px solid var(--bd);
}

/* 3캐릭터 영역 */
.stage {
  display: flex;
  gap: 14px;
  padding: 20px 24px;
  justify-content: center;
  background: var(--soft);
  border-bottom: 1px solid var(--bd);
}

.agent-card {
  flex: 1;
  max-width: 200px;
  text-align: center;
}

.agent-face {
  width: 68px;
  height: 68px;
  border-radius: 18px;
  margin: 0 auto 8px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 30px;
}

.agent-name {
  font-weight: 700;
  font-size: 14px;
  margin-bottom: 2px;
}

.agent-role {
  font-size: 11px;
  color: var(--mut);
  margin-bottom: 8px;
}

.agent-talk {
  font-size: 12px;
  border-radius: 11px;
  padding: 8px 10px;
  line-height: 1.5;
  text-align: left;
  min-height: 60px;
}

.thinking {
  color: inherit;
  opacity: 0.55;
}

/* 합의 요약 카드 */
.summary-card {
  margin: 16px 20px;
  background: #fff;
  border: 1px dashed var(--pur);
  border-radius: 12px;
  padding: 12px 14px;
  font-size: 13px;
  color: var(--pur);
  line-height: 1.5;
}

/* 개입 입력 바 */
.ctrl-bar {
  display: flex;
  gap: 10px;
  align-items: center;
  border-top: 1px solid var(--bd);
  padding: 12px 20px;
  background: #fff;
}

.intervention-input {
  flex: 1;
  background: #f0efec;
  border: 1px solid var(--bd);
  border-radius: 10px;
  padding: 9px 12px;
  font-size: 12px;
  font-family: inherit;
  color: var(--mut);
}
.intervention-input:focus { outline: none; border-color: var(--pur); }
.intervention-input:disabled { opacity: 0.6; }

.btn-intervene {
  background: var(--pur);
  color: #fff;
  border-radius: 9px;
  padding: 9px 16px;
  font-size: 13px;
  font-weight: 600;
}
.btn-intervene:disabled { opacity: 0.4; cursor: not-allowed; }
.btn-intervene:not(:disabled):hover { background: #4540a0; }

.btn-watch {
  background: #fff;
  border: 1px solid var(--bd);
  border-radius: 9px;
  padding: 9px 14px;
  font-size: 13px;
  color: var(--mut);
}
.btn-watch:disabled { opacity: 0.4; cursor: not-allowed; }
.btn-watch:not(:disabled):hover { background: var(--gray); }

/* 가드 안내 */
.guard-note {
  font-size: 11px;
  color: var(--mut);
  text-align: center;
  padding: 8px 16px;
  background: var(--soft);
  border-top: 1px solid var(--bd);
}

/* 종료 후 */
.finished-bar {
  display: flex;
  justify-content: center;
  padding: 14px;
  border-top: 1px solid var(--bd);
}
.back-btn {
  font-size: 13px;
  color: var(--teal);
  border: 1px solid var(--teal);
  border-radius: 8px;
  padding: 9px 20px;
  background: #fff;
}
.back-btn:hover { background: var(--tealbg); }
</style>

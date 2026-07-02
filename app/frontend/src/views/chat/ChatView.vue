<template>
  <div class="chat-page" :class="{ 'is-secret': isSecret }">

    <!-- 🎉 기쁨 감정 축하 폭죽 효과 오버레이 -->
    <div v-if="showJoyCelebration" class="joy-celebration-overlay">
      <div v-for="n in 35" :key="n" class="confetti-particle" :style="confettiStyle(n)"></div>
    </div>

    <!-- 배경: 일반=노을 일러스트 / 시크릿=밤하늘+별똥별 -->
    <div
      class="chat-bg"
      :class="{ 'chat-bg--secret': isSecret }"
      :style="isSecret ? null : { backgroundImage: `url(${chatBg})` }"
    >
      <template v-if="isSecret">
        <div class="moon"></div>
        <div class="stars stars--far"></div>
        <div class="stars stars--mid"></div>
        <div class="stars stars--near"></div>
        <span class="shoot"></span>
        <span class="shoot"></span>
        <span class="shoot"></span>
        <span class="shoot"></span>
      </template>
    </div>

    <!-- 시크릿챗 경고 배너 (SCR-003-S ②) -->
    <div v-if="isSecret" class="secret-banner">
      <span>🔒 <strong>시크릿챗</strong> — 이 대화와 분석은 <strong>저장되지 않으며</strong>,
      종료 시 기록이 남지 않습니다.</span>
      <button class="secret-exit-btn" @click="showExitModal = true">✕ 시크릿챗 종료</button>
    </div>

    <!-- 시크릿챗 종료 확인 모달 (body로 텔레포트 → 화면 전체 덮고 중앙 정렬) -->
    <Teleport to="body">
      <Transition name="modal">
        <div v-if="showExitModal" class="modal-backdrop" @click.self="showExitModal = false">
          <div class="modal-box">
            <div class="modal-icon">🔒</div>
            <h3 class="modal-title">시크릿챗을 종료할까요?</h3>
            <p class="modal-desc">
              지금까지의 대화 내용이 <strong>모두 삭제</strong>됩니다.<br>
              저장되지 않으며 복구할 수 없습니다.
            </p>
            <div class="modal-actions">
              <button class="modal-btn modal-btn--cancel" @click="showExitModal = false">계속 대화할게요</button>
              <button class="modal-btn modal-btn--confirm" @click="confirmExitSecret">종료할게요</button>
            </div>
          </div>
        </div>
      </Transition>
    </Teleport>

    <div class="chat-layout">
      <!-- ===== 왼쪽 패널: 캐릭터 영역 ===== -->
      <aside class="left-panel">
        <div class="char-face" :style="{ background: CHARACTER_META[character].bg, color: CHARACTER_META[character].color }">
          {{ CHARACTER_META[character].faces[currentEmotion] }}
        </div>
        <div class="char-name">{{ CHARACTER_META[character].name }}</div>
        <div class="char-faces">표정 4분기 : 기쁨 · 슬픔 · 분노 · 일반</div>

        <div class="opener-bubble">
          {{ openerText }}
          <small>{{ isSecret ? 'opener · 비저장 안내' : 'opener · 운세/날씨' }}</small>
        </div>

        <template v-if="!isSecret">
          <div class="ctrl-btns">
            <button class="ctrl-btn" @click="toggleSecret">🔒 시크릿챗</button>
          </div>
        </template>

        <div v-else class="secret-note">
          🔒 비저장 모드 — 메모리 적립 정지<br>(종료 시 즉시 파기)
        </div>
      </aside>

      <!-- ===== 오른쪽: 대화 스레드 ===== -->
      <section class="chat-thread" ref="threadRef">
        <div
          v-for="msg in messages"
          :key="msg.id ?? msg._tempId"
          class="bubble-wrap"
          :class="msg.role"
        >
          <span v-if="msg.role === 'assistant' && msg.emotion_label" class="emotion-tag">
            {{ EMOTION_LABELS[msg.emotion_label] }}
          </span>

          <div class="bubble" :class="msg.role === 'user' ? 'bubble-user' : 'bubble-char'">
            {{ msg.content }}
          </div>

          <!-- 🔘 선택 버튼 카드 (콜드스타트 감정 선택지 / 시크릿 MBTI 저장 동의) -->
          <div v-if="msg.role === 'assistant' && msg._choices" class="mbti-options-bar">
            <button
              v-for="opt in msg._choices"
              :key="opt.value"
              class="mbti-opt-btn"
              :disabled="!!msg._chosen"
              @click="handleChoice(msg, opt)"
            >
              {{ opt.text }}
            </button>
          </div>

        </div>

        <div v-if="isTyping" class="typing-indicator">
          <span></span><span></span><span></span>
        </div>
      </section>
    </div>

    <!-- ===== 추천 질문 ===== -->
    <div class="suggest-bar">
      <span class="suggest-label">✦ 이런 말 어때요?</span>
      <span v-if="suggestLoading" class="suggest-loading">생각 중…</span>
      <button v-else v-for="q in suggestedQuestions" :key="q" class="q-chip" @click="fillInput(q)">
        {{ q }}
      </button>
    </div>

    <!-- ===== 입력바 ===== -->
    <div class="input-zone">
      <div class="input-bar">
        <textarea
          ref="inputRef"
          v-model="inputText"
          class="msg-input"
          :placeholder="isSecret ? '메시지 입력… (종료 시 전부 파기)' : '메시지 입력… (최대 300자)'"
          maxlength="300"
          rows="1"
          @keydown.enter.exact.prevent="sendMessage"
          @input="autoResize"
        />
        <span class="char-count">{{ inputText.length }}/300</span>
        <button class="send-btn" :disabled="!inputText.trim() || isTyping" @click="sendMessage">
          전송 ➤
        </button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, nextTick, onMounted, onUnmounted, watch } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { chatApi } from '../../api/chat.js'
import chatBg from '../../assets/chat-bg.png'
import { useSecret } from '../../composables/useSecret.js'
import { useTts } from '../../composables/useTts.js'

const router = useRouter()
const route  = useRoute()

const CHARACTER_META = {
  pori: {   // 레서판다 / 밝음·응원형
    name: '포리', color: '#5EEAD4', bg: 'rgba(94,234,212,0.18)',
    faces: {
      default:   '^‿^',
      joy:       '◕‿◕✨',
      sadness:   '；_；',
      anger:     '＞﹏＜',
      normal:    '^‿^',
    }
  },
  kkami: {  // 고양이 / 깊음·묵직형
    name: '까미', color: '#C4B5FD', bg: 'rgba(196,181,253,0.18)',
    faces: {
      default:   '•_•',
      joy:       '•‿•',
      sadness:   '•︵•',
      anger:     '•益•',
      normal:    '•_•',
    }
  },
  toto: {   // 수달 / 장난·환기형
    name: '토토', color: '#7DD3FC', bg: 'rgba(125,211,252,0.18)',
    faces: {
      default:   '◕‿↼',
      joy:       '(ᵔᴗᵔ)/',
      sadness:   '；ω；',
      anger:     '｀皿´',
      normal:    '◕‿↼',
    }
  },
  yeoul: {  // 뱁새 / 차분·포근형
    name: '여울', color: '#FBBF77', bg: 'rgba(251,191,119,0.18)',
    faces: {
      default:   '◠‿◠',
      joy:       '◠‿◠♡',
      sadness:   '◠︵◠',
      anger:     '◠ᗨ◠',
      normal:    '◠‿◠',
    }
  },
}
const EMOTION_LABELS = {
  joy:     '✦ 기쁨 모드',
  sadness: '✦ 슬픔 모드',
  anger:   '✦ 분노 모드',
  normal:  '✦ 일반 모드',
}

const character      = ref(
  CHARACTER_META[route.query.character] ? route.query.character : 'pori'
)
const { secret: isSecret, setSecret } = useSecret()
const { playTask, stop: ttsStop } = useTts()
const sessionId      = ref(null)
const coldStartDone  = ref(false)
const showExitModal  = ref(false)
const messages       = ref([])
const inputText      = ref('')
const isTyping       = ref(false)
const suggestLoading = ref(false)
const suggestedQuestions = ref([])
const suggestionRequestId = ref(0)
const mbtiQuestionLoading = ref(false)
const lastMbtiQuestionKey = ref('')
const currentEmotion = ref('default')
const threadRef = ref(null)
const inputRef  = ref(null)

const weatherInfo = ref(null)

const openerText = computed(() => {
  if (isSecret.value) {
    return '여긴 아무 기록도 안 남아. 편하게 다 털어놔도 돼.'
  }
  return weatherInfo.value?.opener || '오늘 어떤 하루였어?'
})

async function fetchWeatherOpener() {
  if (isSecret.value) return
  if (navigator.geolocation) {
    navigator.geolocation.getCurrentPosition(
      async (position) => {
        try {
          const { latitude, longitude } = position.coords
          const data = await chatApi.getWeatherOpener(latitude, longitude)
          weatherInfo.value = data
        } catch (err) {
          console.error("Failed to fetch weather opener with location:", err)
          fallbackWeatherOpener()
        }
      },
      async (err) => {
        console.warn("Geolocation access denied or failed:", err)
        fallbackWeatherOpener()
      }
    )
  } else {
    fallbackWeatherOpener()
  }
}

async function fallbackWeatherOpener() {
  try {
    const data = await chatApi.getWeatherOpener()
    weatherInfo.value = data
  } catch (err) {
    console.error("Failed to fetch fallback weather opener:", err)
  }
}

watch(isSecret, (newVal) => {
  if (!newVal) {
    fetchWeatherOpener()
  } else {
    weatherInfo.value = null
  }
})

const showJoyCelebration = ref(false)

function triggerJoyCelebration() {
  showJoyCelebration.value = true
  playFanfare()
  setTimeout(() => {
    showJoyCelebration.value = false
  }, 3000)
}

function playFanfare() {
  try {
    const ctx = new (window.AudioContext || window.webkitAudioContext)()
    const now = ctx.currentTime
    const notes = [261.63, 329.63, 392.00, 523.25] // C4, E4, G4, C5
    notes.forEach((freq, idx) => {
      const osc = ctx.createOscillator()
      const gain = ctx.createGain()
      osc.type = 'triangle'
      osc.frequency.setValueAtTime(freq, now + idx * 0.08)
      gain.gain.setValueAtTime(0.12, now + idx * 0.08)
      gain.gain.exponentialRampToValueAtTime(0.0001, now + idx * 0.08 + 0.5)
      osc.connect(gain)
      gain.connect(ctx.destination)
      osc.start(now + idx * 0.08)
      osc.stop(now + idx * 0.08 + 0.6)
    })
  } catch (e) {
    console.warn("Web Audio API not supported or blocked:", e)
  }
}

function confettiStyle(n) {
  const colors = ['#FCD34D', '#F472B6', '#38BDF8', '#34D399', '#A78BFA']
  const left = Math.random() * 100
  const delay = Math.random() * 0.8
  const duration = 1.5 + Math.random() * 1.5
  const size = 6 + Math.random() * 10
  const color = colors[n % colors.length]
  return {
    left: `${left}%`,
    backgroundColor: color,
    animationDelay: `${delay}s`,
    animationDuration: `${duration}s`,
    width: `${size}px`,
    height: `${size}px`,
    transform: `rotate(${Math.random() * 360}deg)`
  }
}

async function refreshSuggestions() {
  if (!sessionId.value || isSecret.value || suggestLoading.value) return
  const requestId = suggestionRequestId.value + 1
  suggestionRequestId.value = requestId
  suggestLoading.value = true
  try {
    const result = await chatApi.suggestQuestions(sessionId.value)
    if (requestId === suggestionRequestId.value) {
      suggestedQuestions.value = result.questions ?? []
    }
  } catch {
    if (requestId === suggestionRequestId.value) {
      suggestedQuestions.value = []
    }
  } finally {
    if (requestId === suggestionRequestId.value) {
      suggestLoading.value = false
    }
  }
}

const OPENER_MSG = {
  pori:   isSecret => isSecret
    ? '여긴 비밀이니까 마음 편히 다 풀어놔! 무슨 일 있어?'
    : '안녕! 오늘 작은 좋은 일이라도 있었어? 같이 이야기해봐!',
  kkami:  isSecret => isSecret
    ? '여긴 아무것도 안 남아. 천천히 말해도 돼'
    : '왔구나. 오늘 마음에 제일 걸린 게 뭐였어?',
  toto:   isSecret => isSecret
    ? '쉿, 여긴 우리 둘만의 비밀이거든? 뭐든 풀어놔도 돼'
    : '안녕! 오늘 일진은 좀 어땠어? 무거우면 같이 털어볼래?',
  yeoul:  isSecret => isSecret
    ? '여긴 아무 기록도 안 남아. 천천히, 편하게 말해도 괜찮아'
    : '안녕. 오늘 하루는 어땠어? 천천히 말해줘도 괜찮아',
}

// ── 유휴 타이머: 턴 종료 후 10초 무입력 → MBTI 질문 (최종_통합_흐름도 §5) ──
const IDLE_MS = 10000
let idleTimer = null
function clearIdleTimer() { if (idleTimer) { clearTimeout(idleTimer); idleTimer = null } }
function startIdleTimer() { clearIdleTimer(); idleTimer = setTimeout(askMbtiIfIdle, IDLE_MS) }

async function askMbtiIfIdle() {
  if (isTyping.value || mbtiQuestionLoading.value || !sessionId.value || !coldStartDone.value) return
  mbtiQuestionLoading.value = true
  try {
    const res = await chatApi.mbtiNextQuestion(sessionId.value)
    if (res.has_question) {
      const questionKey = res.question_code || res.question_text
      if (questionKey && questionKey === lastMbtiQuestionKey.value) return
      lastMbtiQuestionKey.value = questionKey
      pushAssistant(res.question_text, {
        tts_task_id: res.tts_task_id,
        _mbtiQuestionCode: res.question_code,
      })
      await scrollToBottom()
    }
  } catch {
    // Optional MBTI prompt failures should not affect chat.
  } finally {
    mbtiQuestionLoading.value = false
  }
}
watch(inputText, v => { if (v) clearIdleTimer() })   // 입력 시작하면 눈치껏 대기

// ── 어시스턴트 말풍선 push + TTS 자동 1회 재생 (재생 후 서버에서 파기) ──
function pushAssistant(text, extra = {}) {
  const m = { _tempId: Date.now(), role: 'assistant', content: text, ...extra }
  messages.value.push(m)
  if (m.tts_task_id) playTask(m.tts_task_id)
  return m
}

// ── 세션 초기화: 콜드스타트 게이팅 (감정 선택지 먼저) ──
async function initSession() {
  try {
    const sess = await chatApi.startSession(character.value, isSecret.value)
    sessionId.value = sess.session_id
    coldStartDone.value = !!sess.cold_start_done
    lastMbtiQuestionKey.value = ''
    suggestionRequestId.value = 0

    if (!coldStartDone.value) {
      messages.value.push({
        _tempId: Date.now(), role: 'assistant',
        content: sess.opening_question || '지금 기분이 어때요?',
        _choices: (sess.emotion_choices || []).map(c => ({ value: c.code, text: c.label })),
        _choiceType: 'cold_start',
      })
    } else {
      const openerContent = OPENER_MSG[character.value]?.(isSecret.value)
        ?? '안녕! 오늘 어떤 하루였어?'
      messages.value.push({ _tempId: Date.now(), role: 'assistant', content: openerContent })
      refreshSuggestions()
    }
  } catch {
    // 세션 생성 실패: 옛 세션 ID가 남지 않도록 초기화 + 안내
    sessionId.value = null
    messages.value.push({
      _tempId: Date.now(), role: 'assistant',
      content: '서버랑 연결이 잠깐 안 되고 있어요. 새로고침 한 번 해줄래요?',
    })
  }
}

onMounted(async () => {
  fetchWeatherOpener()
  await initSession()
})

onUnmounted(() => { clearIdleTimer(); ttsStop() })

// ── 선택 버튼 처리 (콜드스타트 감정 선택 / MBTI 저장 동의) ──
async function handleChoice(msgObj, opt) {
  if (msgObj._chosen) return
  msgObj._chosen = opt.value

  if (msgObj._choiceType === 'cold_start') {
    messages.value.push({ _tempId: Date.now(), role: 'user', content: opt.text })
    try {
      const res = await chatApi.coldStart(sessionId.value, opt.value)
      coldStartDone.value = true
      currentEmotion.value = opt.value
      pushAssistant(res.follow_up_message, { tts_task_id: res.tts_task_id })
      refreshSuggestions()
      startIdleTimer()
    } catch {
      msgObj._chosen = null
      messages.value.push({ _tempId: Date.now(), role: 'assistant', content: '앗, 잠깐 연결이 불안정했어요. 다시 골라줄래요?' })
    }
  } else if (msgObj._choiceType === 'mbti_consent') {
    try {
      const res = await chatApi.mbtiConsent(sessionId.value, opt.value === 'yes')
      pushAssistant(res.confirm_message, { tts_task_id: res.tts_task_id })
      startIdleTimer()
    } catch {
      msgObj._chosen = null
    }
  }
  await scrollToBottom()
}

async function sendMessage() {
  const content = inputText.value.trim()
  if (!content || isTyping.value) return
  if (!sessionId.value) {
    messages.value.push({ _tempId: Date.now(), role: 'assistant', content: '연결이 끊겨 있어요. 새로고침 해주세요!' })
    return
  }
  // 감정 선택 전에 바로 입력한 경우: '그냥 그래'로 자동 시작하고 대화 계속 진행
  if (!coldStartDone.value) {
    try {
      await chatApi.coldStart(sessionId.value, 'normal')
      coldStartDone.value = true
      // 남아있는 선택지 버튼 비활성화
      messages.value.forEach(m => { if (m._choiceType === 'cold_start' && !m._chosen) m._chosen = 'normal' })
    } catch {
      messages.value.push({ _tempId: Date.now(), role: 'assistant', content: '잠깐 연결이 불안정했어요. 위의 기분 버튼을 눌러 시작해줄래요?' })
      return
    }
  }
  clearIdleTimer()
  messages.value.push({ _tempId: Date.now(), role: 'user', content })
  inputText.value = ''
  isTyping.value = true
  await scrollToBottom()
  try {
    const res = await chatApi.sendChat(sessionId.value, content, character.value, isSecret.value)
    const m = pushAssistant(res.message.text, {
      id: res.message_id ?? undefined,
      emotion_label: res.emotion_label,
      tts_task_id: res.tts_task_id,
    })
    // 시크릿 모드에서 MBTI 답변 감지 → 저장 동의 버튼 (API_명세서 §5-2)
    if (res.ui?.show_mbti_save_consent) {
      m._choices = [
        { value: 'yes', text: '💾 저장해도 돼요' },
        { value: 'no',  text: '🙅 이번엔 저장하지 말아요' },
      ]
      m._choiceType = 'mbti_consent'
    }
    if (res.emotion_label) {
      currentEmotion.value = res.emotion_label
      if (res.emotion_label === 'joy') {
        triggerJoyCelebration()
      }
    }
    refreshSuggestions()
  } catch {
    messages.value.push({ _tempId: Date.now(), role: 'assistant', content: '잠시 연결이 끊겼어요. 다시 시도해 줄래요? 🙏' })
  } finally {
    isTyping.value = false
    startIdleTimer()
    await scrollToBottom()
  }
}

async function toggleSecret() {
  clearIdleTimer()
  setSecret(!isSecret.value)
  messages.value = []
  coldStartDone.value = false
  await initSession()
  router.replace({ query: { character: character.value, secret: isSecret.value ? 'on' : undefined } })
}

async function confirmExitSecret() {
  showExitModal.value = false
  clearIdleTimer()
  if (sessionId.value) {
    try {
      // 🔒 시크릿챗 종료 → RAM/세션 캐시 즉시 파기 (API_명세서 v6.0)
      await chatApi.endSession(sessionId.value)
    } catch (err) {
      console.error("Failed to end secret session:", err)
    }
  }
  setSecret(false)
  messages.value = []
  coldStartDone.value = false
  await initSession()
  router.replace({ query: { character: character.value } })
}

function fillInput(text) { inputText.value = text; inputRef.value?.focus() }
function autoResize(e) { e.target.style.height = 'auto'; e.target.style.height = e.target.scrollHeight + 'px' }
async function scrollToBottom() { await nextTick(); if (threadRef.value) threadRef.value.scrollTop = threadRef.value.scrollHeight }

</script>

<style scoped>
.chat-page {
  display: flex;
  flex-direction: column;
  height: calc(100vh - 54px);
  position: relative;
  overflow: hidden;
}

/* 배경 공통 */
.chat-bg {
  position: absolute;
  inset: 0;
  z-index: 0;
  background-size: cover;
  background-position: center 30%;
  background-repeat: no-repeat;
  overflow: hidden;
}
/* 일반(노을): 가독성용 어두운 오버레이 */
.chat-bg:not(.chat-bg--secret)::after {
  content: "";
  position: absolute;
  inset: 0;
  background: linear-gradient(180deg,
    rgba(13, 5, 32, 0.18) 0%,
    rgba(20, 8, 48, 0.30) 45%,
    rgba(13, 5, 32, 0.46) 100%);
}

/* ── 시크릿챗: 밤하늘 ── */
.chat-bg--secret {
  background: radial-gradient(circle at 70% -10%,
    #2a1560 0%, #170c3c 36%, #0b0622 70%, #060218 100%);
}

/* 달 (시선 포인트) */
.moon {
  position: absolute;
  top: 8%;
  right: 9%;
  width: 92px;
  height: 92px;
  border-radius: 50%;
  background: radial-gradient(circle at 36% 34%, #f4f8ff 0%, #d8e3f5 50%, #b6c6e6 100%);
  box-shadow: 0 0 60px 16px rgba(200,218,255,0.28),
              0 0 150px 62px rgba(150,180,255,0.16);
}

/* 별 레이어 (가까운/먼) — parallax drift */
.stars {
  position: absolute;
  inset: 0;
  background-repeat: repeat;
}
.stars--far {
  background-image:
    radial-gradient(1px 1px at 30px 40px, rgba(255,255,255,.65), transparent),
    radial-gradient(1px 1px at 120px 90px, rgba(255,255,255,.45), transparent),
    radial-gradient(1px 1px at 80px 160px, rgba(200,215,255,.55), transparent);
  background-size: 210px 210px;
  opacity: .7;
  animation: drift 150s linear infinite;
}
.stars--mid {
  background-image:
    radial-gradient(1.6px 1.6px at 50px 60px, rgba(255,255,255,.9), transparent),
    radial-gradient(1.4px 1.4px at 170px 130px, rgba(255,255,255,.7), transparent),
    radial-gradient(1.5px 1.5px at 100px 30px, rgba(205,222,255,.8), transparent);
  background-size: 270px 270px;
  animation: drift 95s linear infinite, twinkle 5s ease-in-out infinite alternate;
}
.stars--near {
  background-image:
    radial-gradient(2.3px 2.3px at 70px 80px, #fff, transparent),
    radial-gradient(2px 2px at 210px 170px, rgba(255,255,255,.9), transparent),
    radial-gradient(1.9px 1.9px at 150px 230px, rgba(214,228,255,.95), transparent);
  background-size: 350px 350px;
  animation: drift 62s linear infinite;
}
@keyframes drift {
  from { background-position: 0 0; }
  to   { background-position: -160px 1000px; }
}
@keyframes twinkle {
  0%   { opacity: 0.5; }
  100% { opacity: 1; }
}

/* 별똥별 (머리 + 꼬리) */
.shoot {
  position: absolute;
  width: 180px;
  height: 2px;
  background: linear-gradient(90deg, rgba(255,255,255,0) 0%, rgba(190,215,255,.5) 70%, rgba(255,255,255,.95) 100%);
  border-radius: 2px;
  filter: drop-shadow(0 0 6px rgba(190,215,255,0.85));
  opacity: 0;
  transform: rotate(20deg);
  animation: shoot 7s linear infinite;
}
.shoot::after {
  content: "";
  position: absolute;
  right: -2px;
  top: 50%;
  transform: translateY(-50%);
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: #fff;
  box-shadow: 0 0 12px 3px rgba(205,225,255,0.95);
}
.shoot:nth-of-type(1) { top: 10%; left: 4%;  animation-delay: 0s;   }
.shoot:nth-of-type(2) { top: 24%; left: 40%; animation-delay: 2.6s; }
.shoot:nth-of-type(3) { top: 6%;  left: 66%; animation-delay: 4.4s; }
.shoot:nth-of-type(4) { top: 38%; left: 18%; animation-delay: 5.8s; }
@keyframes shoot {
  0%   { opacity: 0; transform: translate(0, 0) rotate(20deg); }
  4%   { opacity: 1; }
  16%  { opacity: 1; }
  24%  { opacity: 0; transform: translate(500px, 182px) rotate(20deg); }
  100% { opacity: 0; }
}

/* 배경 위로 실제 UI를 올림 */
.chat-page > *:not(.chat-bg) { position: relative; z-index: 1; }

/* ── 시크릿챗 패널 톤: 차분한 푸른/은빛 ── */
.is-secret .left-panel,
.is-secret .suggest-bar,
.is-secret .input-zone { border-color: rgba(150,180,255,0.18); }
.is-secret .send-btn {
  background: linear-gradient(135deg, #8fb0ff, #b9cdff);
  color: #0a1230;
}
.is-secret .q-chip {
  border-color: rgba(150,180,255,0.4);
  color: #d4e2ff;
  background: rgba(120,150,255,0.12);
}
.is-secret .q-chip:hover { background: rgba(120,150,255,0.22); }
.is-secret .opener-bubble {
  background: rgba(20,30,72,0.42);
  border-color: rgba(150,180,255,0.24);
  color: #d4e2ff;
}
.is-secret .char-face { box-shadow: 0 0 30px rgba(150,180,255,0.18); }
.is-secret .msg-input:focus { border-color: rgba(150,180,255,0.6); }
.is-secret .emotion-tag { background: rgba(150,180,255,0.18); color: #bcd2ff; }

/* 시크릿챗 배너 */
.secret-banner {
  background: rgba(248, 113, 113, 0.15);
  border-bottom: 1px solid rgba(248,113,113,0.3);
  color: #FCA5A5;
  font-size: 13px;
  padding: 9px 16px;
  flex-shrink: 0;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}
.secret-banner strong { color: #fff; }
.secret-exit-btn {
  flex-shrink: 0;
  font-size: 12px;
  padding: 4px 12px;
  border-radius: 999px;
  border: 1px solid rgba(248,113,113,0.5);
  color: #FCA5A5;
  background: rgba(248,113,113,0.15);
  cursor: pointer;
  white-space: nowrap;
  transition: background 0.2s;
}
.secret-exit-btn:hover {
  background: rgba(248,113,113,0.3);
}

/* ── 시크릿챗 종료 모달 ── */
.modal-backdrop {
  position: fixed;
  inset: 0;
  z-index: 100;
  background: rgba(0, 0, 0, 0.6);
  backdrop-filter: blur(6px);
  display: flex;
  align-items: center;
  justify-content: center;
}
.modal-box {
  background: rgba(30, 15, 60, 0.92);
  border: 1px solid rgba(248, 113, 113, 0.35);
  border-radius: 20px;
  padding: 36px 32px;
  width: 340px;
  text-align: center;
  box-shadow: 0 8px 40px rgba(0,0,0,0.5);
}
.modal-icon {
  font-size: 40px;
  margin-bottom: 14px;
}
.modal-title {
  font-size: 17px;
  font-weight: 700;
  color: #fff;
  margin-bottom: 12px;
}
.modal-desc {
  font-size: 13px;
  color: rgba(255,255,255,0.6);
  line-height: 1.7;
  margin-bottom: 24px;
}
.modal-desc strong { color: #FCA5A5; }
.modal-actions {
  display: flex;
  gap: 10px;
}
.modal-btn {
  flex: 1;
  padding: 11px 0;
  border-radius: 10px;
  font-size: 14px;
  font-weight: 600;
  cursor: pointer;
  border: none;
  transition: opacity 0.2s;
}
.modal-btn:hover { opacity: 0.85; }
.modal-btn--cancel {
  background: rgba(255,255,255,0.1);
  color: rgba(255,255,255,0.8);
}
.modal-btn--confirm {
  background: rgba(248, 113, 113, 0.8);
  color: #fff;
}

/* 모달 트랜지션 */
.modal-enter-active, .modal-leave-active { transition: all 0.2s ease; }
.modal-enter-from, .modal-leave-to { opacity: 0; transform: scale(0.95); }

.chat-layout {
  display: flex;
  flex: 1;
  overflow: hidden;
}

/* ── 왼쪽 패널 (글래스모피즘) ── */
.left-panel {
  flex: 0 0 460px;
  border-right: 1px solid rgba(192,132,252,0.2);
  padding: 40px 34px;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 22px;
  overflow-y: auto;
  background: rgba(13,5,32,0.25);
  backdrop-filter: blur(16px);
}

.char-face {
  width: 240px;
  height: 240px;
  border-radius: 48px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 96px;
  border: 1px solid rgba(192,132,252,0.3);
  margin-top: 8px;
  box-shadow: 0 0 44px rgba(192,132,252,0.18);
}

.char-name {
  font-weight: 700;
  font-size: 28px;
  color: #fff;
}

.char-faces {
  font-size: 14.5px;
  color: rgba(255,255,255,0.45);
  text-align: center;
}

.opener-bubble {
  background: rgba(42,14,107,0.4);
  border: 1px solid rgba(192,132,252,0.22);
  border-radius: 18px;
  padding: 17px 19px;
  font-size: 16.5px;
  color: #E9CAFF;
  text-align: center;
  width: 100%;
  line-height: 1.6;
}
.opener-bubble small {
  display: block;
  color: rgba(255,255,255,0.38);
  font-size: 10.5px;
  margin-top: 4px;
}

.ctrl-btns { display: flex; gap: 12px; width: 100%; }
.ctrl-btn {
  flex: 1;
  font-size: 15.5px;
  border: 1px solid rgba(255,138,101,0.25);
  border-radius: 14px;
  padding: 15px 8px;
  background: rgba(255,138,101,0.1);
  color: #FFD9C0;
  transition: background 0.2s;
}
.ctrl-btn:hover { background: rgba(255,138,101,0.22); }

.secret-note {
  width: 100%;
  font-size: 11.5px;
  color: rgba(255,255,255,0.4);
  border: 1px dashed rgba(255,255,255,0.15);
  border-radius: 10px;
  padding: 9px 11px;
  text-align: center;
  line-height: 1.6;
}

/* ── 대화 스레드 ── */
.chat-thread {
  flex: 1;
  padding: 36px 56px;
  display: flex;
  flex-direction: column;
  gap: 22px;
  overflow-y: auto;
  background: rgba(13,5,32,0.15);
}

.bubble-wrap {
  display: flex;
  flex-direction: column;
  max-width: 82%;
}
.bubble-wrap.user      { align-self: flex-end;   align-items: flex-end; }
.bubble-wrap.assistant { align-self: flex-start;  align-items: flex-start; }

.emotion-tag {
  font-size: 12px;
  background: rgba(94,234,212,0.18);
  color: #5EEAD4;
  border-radius: 7px;
  padding: 3px 10px;
  margin-bottom: 6px;
  display: inline-block;
}

.bubble {
  border-radius: 20px;
  padding: 16px 22px;
  font-size: 17.5px;
  line-height: 1.65;
}
.bubble-user {
  background: linear-gradient(135deg, rgba(255,138,101,0.28), rgba(255,179,71,0.22));
  color: #FFD9C0;
  border: 1px solid rgba(255,138,101,0.35);
}
.bubble-char {
  background: rgba(255,255,255,0.09);
  border: 1px solid rgba(255,255,255,0.14);
  color: rgba(255,255,255,0.92);
}
.tea-card {
  background: rgba(255,255,255,0.08);
  border: 1px solid rgba(255,255,255,0.15);
  border-radius: 16px;
  padding: 12px 14px;
  font-size: 13px;
  color: #fff;
}
.tea-desc { font-size: 11px; color: rgba(255,255,255,0.5); margin: 4px 0; }

/* 타이핑 인디케이터 */
.typing-indicator {
  align-self: flex-start;
  display: flex;
  gap: 5px;
  align-items: center;
  background: rgba(255,255,255,0.09);
  border: 1px solid rgba(255,255,255,0.14);
  border-radius: 14px;
  padding: 10px 16px;
}
.typing-indicator span {
  display: block;
  width: 7px;
  height: 7px;
  border-radius: 50%;
  background: rgba(255,255,255,0.5);
  animation: bounce 1.2s infinite ease-in-out;
}
.typing-indicator span:nth-child(2) { animation-delay: 0.2s; }
.typing-indicator span:nth-child(3) { animation-delay: 0.4s; }
@keyframes bounce {
  0%, 80%, 100% { transform: translateY(0); opacity: 0.4; }
  40%           { transform: translateY(-6px); opacity: 1; }
}

/* ── 추천 질문 바 ── */
.suggest-bar {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
  padding: 16px 32px;
  border-top: 1px solid rgba(192,132,252,0.15);
  background: rgba(13,5,32,0.25);
  backdrop-filter: blur(10px);
  flex-shrink: 0;
}
.suggest-label {
  font-size: 14.5px;
  color: rgba(255,255,255,0.4);
  font-weight: 600;
  white-space: nowrap;
}
.q-chip {
  font-size: 15px;
  border: 1px solid rgba(192,132,252,0.35);
  border-radius: 999px;
  padding: 10px 19px;
  color: #E9CAFF;
  background: rgba(192,132,252,0.1);
  transition: background 0.2s;
}
.q-chip:hover { background: rgba(192,132,252,0.22); }

.suggest-loading {
  font-size: 13.5px;
  color: rgba(255,255,255,0.35);
  font-style: italic;
}

/* ── 입력바 ── */
.input-zone {
  border-top: 1px solid rgba(192,132,252,0.15);
  padding: 20px 32px 24px;
  background: rgba(13,5,32,0.4);
  backdrop-filter: blur(20px);
  flex-shrink: 0;
}
.input-bar { display: flex; align-items: flex-end; gap: 14px; }

.msg-input {
  flex: 1;
  background: rgba(255,255,255,0.07);
  border: 1px solid rgba(255,255,255,0.15);
  border-radius: 16px;
  padding: 15px 19px;
  font-size: 17px;
  font-family: inherit;
  color: #fff;
  resize: none;
  line-height: 1.5;
  max-height: 160px;
  overflow-y: auto;
}
.msg-input::placeholder { color: rgba(255,255,255,0.3); }
.msg-input:focus { outline: none; border-color: rgba(94,234,212,0.5); }

.char-count {
  font-size: 10.5px;
  color: rgba(255,255,255,0.3);
  flex-shrink: 0;
  white-space: nowrap;
}

.send-btn {
  background: linear-gradient(135deg, #FF8A65, #FFB347);
  color: #1a0a00;
  border-radius: 16px;
  padding: 15px 28px;
  font-size: 16.5px;
  font-weight: 700;
  flex-shrink: 0;
  transition: opacity 0.2s, transform 0.1s;
}
.send-btn:not(:disabled):hover { opacity: 0.88; transform: translateY(-1px); }
.send-btn:disabled { opacity: 0.3; cursor: not-allowed; }

/* 🔘 MBTI 선택형 버튼 스타일 */
.mbti-options-bar {
  display: flex;
  flex-direction: column;
  gap: 8px;
  width: 100%;
  margin-top: 10px;
}
.mbti-opt-btn {
  background: rgba(255, 255, 255, 0.08);
  border: 1px solid rgba(192, 132, 252, 0.4);
  color: #E9CAFF;
  border-radius: 12px;
  padding: 12px 16px;
  font-size: 15px;
  font-weight: 500;
  text-align: left;
  cursor: pointer;
  transition: all 0.2s;
}
.mbti-opt-btn:hover:not(:disabled) {
  background: rgba(192, 132, 252, 0.2);
  border-color: #C4B5FD;
}
.mbti-opt-btn:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

/* 🍵 수락/권유형 추천 카드 스타일 */
.recommend-consent-bar {
  margin-top: 12px;
  width: 100%;
  border-top: 1px dashed rgba(255, 255, 255, 0.1);
  padding-top: 10px;
}
.consent-question {
  display: flex;
  flex-direction: column;
  gap: 8px;
  font-size: 13.5px;
  color: rgba(255, 255, 255, 0.7);
}
.consent-btns {
  display: flex;
  gap: 10px;
}
.consent-btn {
  padding: 6px 14px;
  border-radius: 8px;
  font-size: 12.5px;
  font-weight: 600;
  cursor: pointer;
  border: 1px solid rgba(255, 255, 255, 0.15);
}
.consent-btn--yes {
  background: rgba(252, 211, 77, 0.18);
  color: #FCD34D;
  border-color: rgba(252, 211, 77, 0.4);
}
.consent-btn--no {
  background: rgba(255, 255, 255, 0.05);
  color: rgba(255, 255, 255, 0.5);
}

.recommend-cards-wrap {
  display: flex;
  flex-direction: column;
  gap: 12px;
  margin-top: 8px;
  animation: fadeIn 0.3s ease-out;
}
.recommend-tea-card, .recommend-bgm-card {
  background: rgba(255, 255, 255, 0.06);
  border: 1px solid rgba(255, 255, 255, 0.1);
  border-radius: 14px;
  padding: 14px 16px;
  color: rgba(255, 255, 255, 0.9);
}
.rec-title { font-size: 14.5px; margin-bottom: 6px; }
.rec-title strong { color: #FCD34D; }
.rec-reason { font-size: 12.5px; color: rgba(255, 255, 255, 0.6); margin-bottom: 6px; line-height: 1.5; }
.rec-effect { font-size: 11px; color: rgba(255, 255, 255, 0.4); font-style: italic; }

.recommend-bgm-card .rec-title strong { color: #38BDF8; }
.rec-artist { display: block; font-size: 12px; color: rgba(255, 255, 255, 0.5); margin-bottom: 8px; }
.bgm-play-link {
  display: inline-block;
  font-size: 12.5px;
  color: #38BDF8;
  text-decoration: none;
  font-weight: 600;
  border: 1px solid rgba(56, 189, 248, 0.4);
  padding: 6px 12px;
  border-radius: 8px;
  background: rgba(56, 189, 248, 0.1);
  transition: background 0.2s;
}
.bgm-play-link:hover {
  background: rgba(56, 189, 248, 0.22);
}

@keyframes fadeIn {
  from { opacity: 0; transform: translateY(4px); }
  to { opacity: 1; transform: translateY(0); }
}

/* 🎉 기쁨 감정 축하 (폭죽/Confetti) 효과 */
.joy-celebration-overlay {
  position: absolute;
  inset: 0;
  pointer-events: none;
  z-index: 10;
  overflow: hidden;
}
.confetti-particle {
  position: absolute;
  top: -20px;
  border-radius: 3px;
  opacity: 0.85;
  animation: fallDown linear forwards;
}
@keyframes fallDown {
  0% {
    transform: translateY(0) rotate(0deg);
    opacity: 1;
  }
  100% {
    transform: translateY(110vh) rotate(720deg);
    opacity: 0;
  }
}

</style>



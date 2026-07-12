<template>
  <div class="chat-page" :class="{ 'is-secret': isSecret }"
       @dragover.prevent="onDragOver" @dragleave="onDragLeave" @drop.prevent="onDropImage">

    <!-- 📷 이미지 드래그&드롭 오버레이 -->
    <div v-if="isDragging" class="drop-overlay">
      <div class="drop-overlay-inner">📷 여기에 사진을 놓으면 첨부돼요</div>
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
        <div class="char-face character-image-frame" :style="{ background: displayCharacter.bg, color: displayCharacter.color }">
          <img
            :src="displayCharacterImage"
            :alt="`${displayCharacter.name} ${displayExpressionLabel}`"
            :class="displayAnimationClass"
          />
        </div>
        <div class="char-name">{{ displayCharacter.name }}</div>
        <!-- 감정 라벨 텍스트("현재 표정 : 슬픔")는 표시하지 않음 — 친구 컨셉 (표정 이미지로만 반응) -->

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
          <!-- 감정 라벨(슬픔 모드 등)은 화면에 표시하지 않음 — 친구 컨셉 (분석은 뒤에서만) -->
          <div class="bubble" :class="msg.role === 'user' ? 'bubble-user' : 'bubble-char'">
            <img v-if="msg.image" :src="msg.image" class="bubble-img" alt="첨부 이미지" />
            <span v-if="msg.content" class="bubble-text">{{ (msg.displayed !== undefined ? msg.displayed : msg.content) || '…' }}</span>
          </div>

        </div>

        <div v-if="isTyping" class="typing-indicator">
          <span></span><span></span><span></span>
        </div>
      </section>
    </div>

    <!-- ===== 입력바 ===== -->
    <div class="input-zone">
      <!-- 첨부 사진 미리보기 (전송 전) -->
      <div v-if="attachedImage" class="img-preview">
        <img :src="attachedImage" alt="첨부 미리보기" />
        <button class="img-preview-remove" @click="clearImage" title="사진 제거">✕</button>
      </div>
      <div class="input-bar">
        <input ref="fileInputRef" type="file" accept="image/*" class="file-hidden" @change="onPickImage" />
        <button class="attach-btn" :disabled="isTyping" @click="fileInputRef?.click()" title="사진 첨부">📷</button>
        <button v-if="sttSupported" class="attach-btn stt-btn" :class="{ 'stt-recording': isRecording }"
                :disabled="isTyping" @click="toggleStt"
                :title="isRecording ? '음성 입력 중지' : '음성으로 입력'">🎤</button>
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
        <button class="send-btn" :disabled="(!inputText.trim() && !attachedImage) || isTyping" @click="sendMessage">
          전송 ➤
        </button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, nextTick, onMounted, onUnmounted } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { chatApi } from '../../api/chat.js'
import chatBg from '../../assets/chat-bg.png'
import { useSecret } from '../../composables/useSecret.js'
import { useTts } from '../../composables/useTts.js'
import { useStt } from '../../composables/useStt.js'

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
// (감정 라벨은 화면에 표시하지 않음 — 친구 컨셉. 분석은 백엔드에서만)

const DISPLAY_CHARACTER_META = {
  otter: {
    name: '수달',
    color: '#7DD3FC',
    bg: 'rgba(125,211,252,0.18)',
    backendCharacter: 'toto',
  },
  cat: {
    name: '까미',
    color: '#C4B5FD',
    bg: 'rgba(196,181,253,0.18)',
    backendCharacter: 'kkami',
  },
  redpanda: {
    name: '포리',
    color: '#5EEAD4',
    bg: 'rgba(94,234,212,0.18)',
    backendCharacter: 'pori',
  },
  bird: {
    name: '여울',
    color: '#FBBF77',
    bg: 'rgba(251,191,119,0.18)',
    backendCharacter: 'yeoul',
  },
}

const EXPRESSION_LABELS = {
  default: '평온',
  joy: '기쁨',
  anger: '화남',
  sadness: '슬픔',
  anxiety: '불안',
  hurt: '상처',
  panic: '당황',
}

// 백엔드 emotion_label (joy/sadness/anger/normal) → 표정 이미지 id
// (구버전 라벨 encourage/sad/angry 매핑이 남아 있어 표정이 안 바뀌던 버그 수정 — 2026-07-03)
const EMOTION_TO_EXPRESSION = {
  joy: 'joy',
  sadness: 'sadness',
  anger: 'anger',
  normal: null,    // 일상 대화면 사용자가 고른 기본 표정 유지
  default: null,   // 세션 시작 직후
}

const EXPRESSION_ANIMATION = {
  joy: 'anim-joy',
  anger: 'anim-anger',
  sadness: 'anim-sadness',
  anxiety: 'anim-anxiety',
  hurt: 'anim-hurt',
  panic: 'anim-panic',
}

function readStoredCharacter() {
  try {
    return JSON.parse(localStorage.getItem('binteumsaiCharacter') || '{}')
  } catch {
    return {}
  }
}

function normalizeCharacterId(id) {
  if (DISPLAY_CHARACTER_META[id]) return id
  // 백엔드 캐릭터 ID → 디스플레이 ID
  if (id === 'toto')  return 'otter'
  if (id === 'kkami') return 'cat'
  if (id === 'pori')  return 'redpanda'
  if (id === 'yeoul') return 'bird'
  // 이전 dev 버전 하위호환
  if (id === 'haeon') return 'otter'
  if (id === 'greung' || id === 'geureung') return 'cat'
  if (id === 'dalkong') return 'redpanda'
  return 'otter'
}

const storedCharacter = readStoredCharacter()
const displayCharacterId = ref(normalizeCharacterId(route.query.character || storedCharacter.characterId))
// 대화방 평상시 표정은 default(평온) 고정 — 온보딩에서 고른 표정은 미리보기용이고,
// 대화 중 표정은 감정분석 결과가 결정한다 (감정 없으면 평온으로 복귀)
const selectedExpression = ref('default')
const { secret: isSecret, setSecret } = useSecret()
const { playTask, stop: ttsStop } = useTts()
const { isSupported: sttSupported, isRecording, start: sttStart, stop: sttStop } = useStt()

// 🎤 음성 입력 (STT) — 말하면 입력창에 실시간으로 채워지고, 확인 후 전송 (2026-07-10)
let sttBaseText = ''
function toggleStt() {
  if (isRecording.value) { sttStop(); return }
  sttBaseText = inputText.value ? inputText.value.replace(/\s+$/, '') + ' ' : ''
  sttStart({
    onInterim: (t) => { inputText.value = (sttBaseText + t).slice(0, 300) },
    onFinal:   (t) => {
      inputText.value = (sttBaseText + t).slice(0, 300)
      sttBaseText = inputText.value.replace(/\s+$/, '') + ' '
    },
    onEnd: () => { nextTick(() => autoResize()) },
  })
}
const sessionId      = ref(null)
const coldStartDone  = ref(false)
const showExitModal  = ref(false)
const messages       = ref([])
const inputText      = ref('')
const isTyping       = ref(false)
const currentEmotion = ref('default')
const threadRef = ref(null)
const inputRef  = ref(null)
const fileInputRef  = ref(null)
const attachedImage = ref(null)   // 첨부 사진 data URL (전송 전, 저장 안 함)
const isDragging    = ref(false)  // 이미지 드래그&드롭 오버레이 표시

const displayCharacter = computed(() => DISPLAY_CHARACTER_META[displayCharacterId.value] || DISPLAY_CHARACTER_META.otter)
const backendCharacter = computed(() => displayCharacter.value.backendCharacter)
const character = backendCharacter  // initSession 하위호환
const displayExpressionId = computed(() => EMOTION_TO_EXPRESSION[currentEmotion.value] || selectedExpression.value)
const displayExpressionLabel = computed(() => EXPRESSION_LABELS[displayExpressionId.value] || '기쁨')
const displayCharacterImage = computed(() => `/characters/${displayCharacterId.value}/${displayExpressionId.value}.png`)
const displayAnimationClass = computed(() => EXPRESSION_ANIMATION[displayExpressionId.value] || 'anim-joy')

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

// ── (구) 유휴 타이머 MBTI 트리거 폐지 (2026-07-08) ──
// MBTI 질문은 이제 백엔드(chat_turn)가 대화 흐름에 맞춰 응답 끝에 얹는다.
// clearIdleTimer는 기존 호출부(onUnmounted·sendMessage 등) 호환용 no-op으로 유지.
const userTurnCount = ref(0)      // 대화 턴 통계용 (MBTI 게이트로는 미사용)
function clearIdleTimer() {}

// ── 어시스턴트 말풍선 push + TTS 자동 1회 재생 (재생 후 서버에서 파기) ──
// 음성이 있으면 재생 시작에 맞춰 텍스트를 음성 길이만큼 타이핑(동기 자막).
// 음성 실패·자동재생 차단·지연(7초) 시엔 텍스트 전체를 즉시 표시.
function animateReveal(m, durationSec, alignment, audioEl) {
  if (m.displayed === m.content) return
  if (m._revealTimer) clearInterval(m._revealTimer)

  // ── 정밀 모드: ElevenLabs 글자별 타임스탬프 + 오디오 현재 시각으로 1:1 동기 ──
  // TTS로 보낸 텍스트와 화면 텍스트가 같아야 성립 — 다르면 균등 타이핑 폴백.
  const canSync = alignment && Array.isArray(alignment.chars) && alignment.chars.length > 0
    && audioEl && alignment.chars.join('') === m.content
  if (canSync) {
    const starts = alignment.starts
    m._revealTimer = setInterval(() => {
      const t = audioEl.currentTime
      if (audioEl.ended || (audioEl.paused && t === 0)) {   // 종료·중단 → 전체 표시
        clearInterval(m._revealTimer); m._revealTimer = null
        m.displayed = m.content
        return
      }
      let idx = 0
      while (idx < starts.length && starts[idx] <= t + 0.12) idx++   // 120ms 선행(읽기 편하게)
      m.displayed = m.content.slice(0, idx)
      scrollToBottom()
      if (idx >= m.content.length) { clearInterval(m._revealTimer); m._revealTimer = null }
    }, 45)
    return
  }

  // ── 폴백: 음성 길이에 맞춘 균등 타이핑 ──
  const total = m.content.length
  const durMs = Math.max(800, (durationSec ? durationSec * 1000 : total * 55) * 0.93)
  const t0 = performance.now()
  m._revealTimer = setInterval(() => {
    const p = Math.min(1, (performance.now() - t0) / durMs)
    m.displayed = m.content.slice(0, Math.ceil(total * p))
    scrollToBottom()
    if (p >= 1) { clearInterval(m._revealTimer); m._revealTimer = null }
  }, 50)
}
function revealNow(m) {
  if (m._revealTimer) { clearInterval(m._revealTimer); m._revealTimer = null }
  m.displayed = m.content
}

function pushAssistant(text, extra = {}) {
  const m = { _tempId: Date.now(), role: 'assistant', content: text, ...extra }
  if (m.tts_task_id) {
    m.displayed = ''                    // 음성 시작까지 잠깐 '…' 표시
    messages.value.push(m)
    const target = messages.value[messages.value.length - 1]   // 반응형 프록시로 조작
    playTask(m.tts_task_id, {
      onStart: (d, alignment, audioEl) => animateReveal(target, d, alignment, audioEl),
      onFail: () => revealNow(target),
    })
    setTimeout(() => {                  // 안전장치: TTS 생성이 8초+ 걸릴 수 있어 폴링 타임아웃(~28초)보다 늦게
      if (target.displayed !== target.content && !target._revealTimer) revealNow(target)
    }, 30000)
    return target
  }
  messages.value.push(m)
  return m
}

// ── 세션 초기화: 콜드스타트 게이팅 (감정 선택지 먼저) ──
async function initSession() {
  try {
    // 친구 컨셉: 감정 안 묻고 날씨/시간/닉네임 기반 첫인사로 시작
    const coords = await getCoordsOrNull()
    const sess = await chatApi.startSession(character.value, isSecret.value, coords)
    sessionId.value = sess.session_id
    coldStartDone.value = true
    userTurnCount.value = 0

    // 서버가 만든 친구 첫인사를 바로 표시 (+ 음성 자동 재생)
    const opener = sess.opener || OPENER_MSG[character.value]?.(isSecret.value) || '안녕! 뭐 하고 있었어?'
    pushAssistant(opener, { tts_task_id: sess.tts_task_id })
    // MBTI 질문은 유휴 타이머 대신 대화 흐름에 맞춰 백엔드가 응답에 얹음 (startIdleTimer 제거)
  } catch {
    sessionId.value = null
    messages.value.push({
      _tempId: Date.now(), role: 'assistant',
      content: '서버랑 연결이 잠깐 안 되고 있어요. 새로고침 한 번 해줄래요?',
    })
  }
}

// 위치 권한이 있으면 좌표 반환(날씨 첫인사용), 없으면 null (거부해도 대화는 정상)
function getCoordsOrNull() {
  return new Promise(resolve => {
    if (!navigator.geolocation) return resolve(null)
    navigator.geolocation.getCurrentPosition(
      p => resolve({ lat: p.coords.latitude, lon: p.coords.longitude }),
      () => resolve(null),
      { timeout: 3000 },
    )
  })
}

// 세션 종료 통지 — 일반 모드도 종료 시 잔여 대화가 user_memory 요약에 반영되도록.
// 탭 닫기/이탈에도 전송이 보장되는 sendBeacon 사용 (응답 안 기다림).
function endSessionBeacon() {
  if (!sessionId.value) return
  const blob = new Blob(
    [JSON.stringify({ session_id: sessionId.value })],
    { type: 'application/json' },
  )
  navigator.sendBeacon('/api/session/end/', blob)
}

onMounted(async () => {
  window.addEventListener('pagehide', endSessionBeacon)
  window.addEventListener('paste', onPasteImage)
  await initSession()
})

onUnmounted(() => {
  clearIdleTimer()
  ttsStop()
  window.removeEventListener('pagehide', endSessionBeacon)
  window.removeEventListener('paste', onPasteImage)
  endSessionBeacon()   // 다른 페이지로 이동할 때도 세션 마무리
})

// (시크릿 모드 MBTI 저장 동의 버튼은 "시크릿 = 완전 무저장" 원칙으로 제거 — 2026-07-03)

// ── 사진 첨부: 선택/드롭/붙여넣기 → 최대 1024px 리사이즈 → JPEG data URL (용량·비용 절감) ──
function processImageFile(file) {
  if (!file || !file.type.startsWith('image/')) return
  const reader = new FileReader()
  reader.onload = () => {
    const img = new Image()
    img.onload = () => {
      const MAX = 1024
      let { width, height } = img
      if (width > MAX || height > MAX) {
        const r = Math.min(MAX / width, MAX / height)
        width = Math.round(width * r); height = Math.round(height * r)
      }
      const canvas = document.createElement('canvas')
      canvas.width = width; canvas.height = height
      canvas.getContext('2d').drawImage(img, 0, 0, width, height)
      attachedImage.value = canvas.toDataURL('image/jpeg', 0.8)
    }
    img.src = reader.result
  }
  reader.readAsDataURL(file)
}
function onPickImage(e) {
  const file = e.target.files?.[0]
  e.target.value = ''            // 같은 파일 다시 선택 가능하게 초기화
  processImageFile(file)
}
// 화면에 이미지 파일 드래그&드롭
function onDropImage(e) {
  isDragging.value = false
  processImageFile(e.dataTransfer?.files?.[0])
}
function onDragOver() { if (!isTyping.value) isDragging.value = true }
function onDragLeave(e) {
  if (!e.relatedTarget) isDragging.value = false   // 창 밖으로 완전히 나갔을 때만 해제(깜빡임 방지)
}
// 클립보드 이미지 붙여넣기(Ctrl+V)
function onPasteImage(e) {
  const item = [...(e.clipboardData?.items || [])].find(i => i.type.startsWith('image/'))
  if (item) processImageFile(item.getAsFile())
}
function clearImage() { attachedImage.value = null }

async function sendMessage() {
  const content = inputText.value.trim()
  const image = attachedImage.value
  if ((!content && !image) || isTyping.value) return
  if (!sessionId.value) {
    messages.value.push({ _tempId: Date.now(), role: 'assistant', content: '연결이 끊겨 있어요. 새로고침 해주세요!' })
    return
  }
  clearIdleTimer()
  userTurnCount.value += 1                 // 대화 턴 카운트 (게이미피케이션/통계용)
  messages.value.push({ _tempId: Date.now(), role: 'user', content, image })
  inputText.value = ''
  attachedImage.value = null
  isTyping.value = true
  await scrollToBottom()
  try {
    const res = await chatApi.sendChat(sessionId.value, content, character.value, isSecret.value, image)
    const m = pushAssistant(res.message.text, {
      id: res.message_id ?? undefined,
      emotion_label: res.emotion_label,
      tts_task_id: res.tts_task_id,
    })
    if (res.emotion_label) {
      currentEmotion.value = res.emotion_label
    }
  } catch {
    messages.value.push({ _tempId: Date.now(), role: 'assistant', content: '잠시 연결이 끊겼어요. 다시 시도해 줄래요? 🙏' })
  } finally {
    isTyping.value = false
    await scrollToBottom()
  }
}

async function toggleSecret() {
  clearIdleTimer()
  endSessionBeacon()   // 기존 세션 마무리 (일반→시크릿 전환 시 잔여 요약)
  setSecret(!isSecret.value)
  messages.value = []
  coldStartDone.value = false
  await initSession()
  router.replace({ query: { character: displayCharacterId.value, secret: isSecret.value ? 'on' : undefined } })
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
  router.replace({ query: { character: displayCharacterId.value } })
}

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
.is-secret .input-zone { border-color: rgba(150,180,255,0.18); }
.is-secret .send-btn {
  background: linear-gradient(135deg, #8fb0ff, #b9cdff);
  color: #0a1230;
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

.character-image-frame {
  overflow: visible;
}

.character-image-frame img {
  width: 104%;
  height: 104%;
  object-fit: contain;
  transform-origin: center bottom;
  filter: drop-shadow(0 18px 24px rgba(0,0,0,0.28));
}

.char-name {
  font-weight: 700;
  font-size: 28px;
  color: #fff;
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

/* 📷 사진 첨부 (MVP) */
.file-hidden { display: none; }

.attach-btn {
  background: rgba(255,255,255,0.07);
  border: 1px solid rgba(255,255,255,0.15);
  border-radius: 16px;
  padding: 13px 15px;
  font-size: 18px;
  line-height: 1;
  flex-shrink: 0;
  transition: background 0.2s;
}
.attach-btn:not(:disabled):hover { background: rgba(255,255,255,0.14); }
.attach-btn:disabled { opacity: 0.3; cursor: not-allowed; }

.img-preview { position: relative; display: inline-block; margin-bottom: 10px; }
.img-preview img {
  max-width: 140px;
  max-height: 140px;
  border-radius: 12px;
  border: 1px solid rgba(255,255,255,0.2);
  display: block;
}
.img-preview-remove {
  position: absolute;
  top: -8px;
  right: -8px;
  width: 24px;
  height: 24px;
  border-radius: 50%;
  background: rgba(0,0,0,0.75);
  color: #fff;
  font-size: 13px;
  line-height: 1;
  display: flex;
  align-items: center;
  justify-content: center;
}

/* 드래그&드롭 오버레이 */
.drop-overlay {
  position: fixed;
  inset: 0;
  z-index: 50;
  background: rgba(20, 10, 30, 0.55);
  display: flex;
  align-items: center;
  justify-content: center;
  pointer-events: none;   /* 드롭 이벤트가 루트로 전달되도록 */
}
.drop-overlay-inner {
  border: 2px dashed rgba(255,255,255,0.75);
  border-radius: 20px;
  padding: 40px 60px;
  font-size: 22px;
  font-weight: 700;
  color: #fff;
  background: rgba(0,0,0,0.35);
}

/* 말풍선 안 첨부 이미지 */
.bubble-img {
  display: block;
  max-width: 240px;
  max-height: 240px;
  border-radius: 12px;
  margin-bottom: 6px;
}
.bubble-text { white-space: pre-wrap; }

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



/* 🎤 음성 입력 (STT) */
.stt-btn.stt-recording {
  background: rgba(248, 113, 113, 0.25);
  border-color: rgba(248, 113, 113, 0.8);
  animation: sttPulse 1.2s ease-in-out infinite;
}
@keyframes sttPulse {
  0%, 100% { box-shadow: 0 0 0 0 rgba(248, 113, 113, 0.45); }
  50%      { box-shadow: 0 0 0 7px rgba(248, 113, 113, 0); }
}

</style>

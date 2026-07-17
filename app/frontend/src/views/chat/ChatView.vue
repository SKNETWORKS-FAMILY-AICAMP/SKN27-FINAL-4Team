<template>
  <div class="chat-page" :class="[sceneMoodClass, timeSceneClass, { 'is-secret': isSecret }]"
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

    <!-- 모든 기능은 기존 API 계약만 사용한다. 화면은 채팅창이 아니라 '마음방의 한 장면'이다. -->
    <main class="vn-shell">
      <section class="mind-room" :style="{ '--character-color': displayCharacter.color }">
        <div class="room-atmosphere" aria-hidden="true">
          <span v-for="n in 12" :key="n" class="light-mote" :style="moteStyle(n)"></span>
          <div class="window-glow"></div>
          <div class="curtain curtain--left"></div>
          <div class="curtain curtain--right"></div>
          <div class="floor-light"></div>
        </div>

        <header class="room-header">
          <div class="room-plaque">
            <span class="room-symbol">✦</span>
            <span><small>{{ timeSceneLabel }}</small><strong>{{ displayCharacter.name }}의 마음방</strong></span>
          </div>
          <div class="room-controls">
            <span class="presence-state" aria-live="polite"><i></i>{{ sceneStatusText }}</span>
            <button class="room-control" type="button" @click="openChatLog" title="대화 기록 열기">
              <span>☰</span><b>이야기 기록</b>
            </button>
            <button class="room-control" :class="{ muted: !ttsEnabled }" type="button" @click="toggleTtsPref"
                    :title="ttsEnabled ? '캐릭터 목소리 끄기' : '캐릭터 목소리 켜기'">
              <span>{{ ttsEnabled ? '◖))' : '◖×' }}</span><b>{{ ttsEnabled ? '목소리' : '음소거' }}</b>
            </button>
            <button v-if="!isSecret" class="room-control room-control--secret" type="button" @click="toggleSecret" title="시크릿챗 시작">
              <span>◇</span><b>문 닫기</b>
            </button>
            <button v-else class="room-control room-control--exit" type="button" @click="showExitModal = true" title="시크릿챗 종료">
              <span>◇</span><b>비밀방 나가기</b>
            </button>
          </div>
        </header>

        <div class="story-lights" aria-label="오늘 쌓인 이야기 조각">
          <span v-for="n in 5" :key="n" :class="{ lit: n <= storyLightCount }"></span>
        </div>

        <div class="character-presence" :class="{ speaking: isCharacterSpeaking, thinking: isTyping, listening: isRecording }">
          <div class="presence-ring"></div>
          <div class="character-image-frame vn-character">
            <Transition name="emotion-shift" mode="out-in">
              <img
                :key="displayCharacterImage"
                :src="displayCharacterImage"
                :alt="`${displayCharacter.name} ${displayExpressionLabel}`"
                :class="displayAnimationClass"
              />
            </Transition>
          </div>
          <div class="character-hud" aria-live="polite">
            <i aria-hidden="true"></i>
            <span>
              <b>{{ displayCharacter.name }}</b>
              <small>{{ displayExpressionLabel }}</small>
            </span>
          </div>
          <div class="character-ground"></div>
          <div class="character-state">
            <span v-if="isTyping" class="thought-dots"><i></i><i></i><i></i></span>
            <span v-else-if="isCharacterSpeaking" class="voice-wave"><i></i><i></i><i></i><i></i><i></i></span>
            <span v-else>{{ isRecording ? '네 이야기를 듣고 있어…' : '곁에 머무는 중' }}</span>
          </div>
        </div>

        <Transition name="whisper">
          <div v-if="latestUserMessage && (isTyping || isCharacterSpeaking)" class="user-whisper">
            <span>나</span>
            <p>{{ latestUserMessage.content || (latestUserMessage.image ? '사진을 건넸다.' : '') }}</p>
          </div>
        </Transition>

        <section class="vn-dialogue chat-console" aria-label="현재 대화">
          <div ref="threadRef" class="chat-thread" @click="skipCurrentDialogue">
            <div v-if="!messages.length && !isTyping" class="chat-empty">
              <span>✦</span>
              <p>{{ displayCharacter.name }}에게 오늘의 이야기를 건네보세요.</p>
            </div>

            <article v-for="msg in messages" :key="msg.id ?? msg._tempId"
                     class="chat-message" :class="msg.role">
              <span v-if="msg.role === 'assistant'" class="chat-message-avatar">
                <img :src="displayCharacterImage" alt="" aria-hidden="true" />
              </span>
              <div class="chat-message-stack">
                <small>{{ msg.role === 'user' ? '나' : displayCharacter.name }}</small>
                <div class="chat-bubble">
                  <img v-if="msg.image" :src="msg.image" alt="대화에 건넨 사진" />
                  <p>{{ (msg.displayed !== undefined ? msg.displayed : msg.content) || '…' }}</p>
                  <span v-if="msg === latestAssistantMessage && isCharacterSpeaking" class="type-caret"></span>
                </div>
              </div>
            </article>

            <article v-if="isTyping" class="chat-message assistant chat-message--typing">
              <span class="chat-message-avatar"><img :src="displayCharacterImage" alt="" aria-hidden="true" /></span>
              <div class="chat-message-stack">
                <small>{{ displayCharacter.name }}</small>
                <div class="chat-bubble"><span class="thought-dots"><i></i><i></i><i></i></span></div>
              </div>
            </article>
          </div>

          <div class="chat-console-footer">
            <button v-if="latestSuggestion" class="story-link" type="button"
                    @click="router.push(latestSuggestion.suggestPage === 'report' ? '/report' : '/mypage')">
              <span>추천 바로가기</span><strong>{{ latestSuggestion.suggestLabel }}</strong><i>→</i>
            </button>

            <div v-if="canChooseAction && !inputText && !attachedImage" class="choice-deck">
              <span class="choice-guide">추천 답장</span>
              <button v-for="action in sceneActions" :key="action.label" type="button" @click="chooseSceneAction(action)">
                <strong>{{ action.label }}</strong>
              </button>
            </div>

            <div v-if="attachedImage" class="vn-image-preview">
              <img :src="attachedImage" alt="건넬 사진 미리보기" />
              <div><strong>{{ displayCharacter.name }}에게 보여줄 사진</strong><span>말과 함께 건넬 수 있어요.</span></div>
              <button type="button" @click="clearImage" title="사진 치우기">✕</button>
            </div>

            <div class="vn-composer">
              <input ref="fileInputRef" type="file" accept="image/*" class="file-hidden" @change="onPickImage" />
              <button class="world-action" :disabled="isTyping" type="button" @click="fileInputRef?.click()" title="사진 보여주기">
                <span>▧</span><b>사진</b>
              </button>
              <button v-if="sttSupported" class="world-action" :class="{ active: isRecording }"
                      :disabled="isTyping" type="button" @click="toggleStt"
                      :title="isRecording ? '듣기 멈추기' : '목소리로 이야기하기'">
                <span>◉</span><b>{{ isRecording ? '듣는 중' : '말하기' }}</b>
              </button>
              <div class="composer-field">
                <textarea
                  ref="inputRef"
                  v-model="inputText"
                  class="msg-input"
                  :placeholder="isSecret ? '이 방에서 나눈 말은 밖에 남지 않아…' : `${displayCharacter.name}에게 메시지 보내기`"
                  maxlength="300"
                  rows="1"
                  @keydown.enter.exact.prevent="sendMessage"
                  @input="autoResize"
                />
                <span>{{ inputText.length }}/300</span>
              </div>
              <button class="send-btn vn-send" :disabled="(!inputText.trim() && !attachedImage) || isTyping" type="button" @click="sendMessage" title="메시지 보내기">
                <span>보내기</span><i>➤</i>
              </button>
            </div>
          </div>
        </section>
      </section>
    </main>

    <Transition name="log-drawer">
      <div v-if="showChatLog" class="story-log-backdrop" @click.self="showChatLog = false">
        <aside class="story-log" aria-label="오늘의 이야기 기록">
          <header>
            <div><small>TODAY'S STORY</small><h2>오늘의 이야기</h2></div>
            <button type="button" @click="showChatLog = false" title="기록 닫기">✕</button>
          </header>
          <div class="story-log-list" ref="logThreadRef">
            <div v-if="!messages.length" class="empty-log">아직 방 안에 이야기가 피어나지 않았어요.</div>
            <article v-for="msg in messages" :key="msg.id ?? msg._tempId" :class="msg.role">
              <span>{{ msg.role === 'user' ? '나' : displayCharacter.name }}</span>
              <div>
                <img v-if="msg.image" :src="msg.image" alt="대화에서 건넨 사진" />
                <p>{{ (msg.displayed !== undefined ? msg.displayed : msg.content) || '…' }}</p>
              </div>
            </article>
            <div v-if="isTyping" class="log-thinking">{{ displayCharacter.name }}가 다음 말을 고르는 중…</div>
          </div>
          <footer><span>✦</span> 이 기록은 오늘의 마음방에서 이어지고 있어요.</footer>
        </aside>
      </div>
    </Transition>
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

// 🔊 TTS 음소거 (2026-07-12) — 목소리 원치 않는 사용자 배려 + 음소거 시 서버가 생성 자체를 스킵(크레딧 0)
const ttsEnabled = ref(localStorage.getItem('binteum_tts') !== 'off')
function toggleTtsPref() {
  ttsEnabled.value = !ttsEnabled.value
  localStorage.setItem('binteum_tts', ttsEnabled.value ? 'on' : 'off')
  if (!ttsEnabled.value) ttsStop()          // 재생 중이던 음성도 즉시 중단
}

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
const logThreadRef = ref(null)
const inputRef  = ref(null)
const fileInputRef  = ref(null)
const attachedImage = ref(null)   // 첨부 사진 data URL (전송 전, 저장 안 함)
const isDragging    = ref(false)  // 이미지 드래그&드롭 오버레이 표시
const showChatLog   = ref(false)

const displayCharacter = computed(() => DISPLAY_CHARACTER_META[displayCharacterId.value] || DISPLAY_CHARACTER_META.otter)
const backendCharacter = computed(() => displayCharacter.value.backendCharacter)
const character = backendCharacter  // initSession 하위호환
const displayExpressionId = computed(() => EMOTION_TO_EXPRESSION[currentEmotion.value] || selectedExpression.value)
const displayExpressionLabel = computed(() => EXPRESSION_LABELS[displayExpressionId.value] || '기쁨')
const displayCharacterImage = computed(() => `/characters/${displayCharacterId.value}/${displayExpressionId.value}.png`)
const displayAnimationClass = computed(() => EXPRESSION_ANIMATION[displayExpressionId.value] || 'anim-joy')

// 백엔드가 이미 주는 감정·TTS 상태·맥락 제안을 장면 전체가 소비한다.
const latestAssistantMessage = computed(() => [...messages.value].reverse().find(m => m.role === 'assistant') || null)
const latestUserMessage = computed(() => [...messages.value].reverse().find(m => m.role === 'user') || null)
const latestAssistantText = computed(() => {
  const msg = latestAssistantMessage.value
  if (!msg) return ''
  return (msg.displayed !== undefined ? msg.displayed : msg.content) || ''
})
const isCharacterSpeaking = computed(() => {
  const msg = latestAssistantMessage.value
  return !!msg && msg.displayed !== undefined && msg.displayed !== msg.content && !isTyping.value
})
const latestSuggestion = computed(() => {
  const msg = [...messages.value].reverse().find(m => m.role === 'assistant' && m.suggestPage)
  if (!msg) return null
  return msg.displayed === undefined || msg.displayed === msg.content ? msg : null
})
const canChooseAction = computed(() => {
  const msg = latestAssistantMessage.value
  const revealDone = !!msg && (msg.displayed === undefined || msg.displayed === msg.content)
  return !!sessionId.value && revealDone && !isTyping.value && !isCharacterSpeaking.value
})
const sceneMoodClass = computed(() => `mood-${currentEmotion.value || 'normal'}`)
const storyLightCount = computed(() => Math.min(5, Math.max(1, userTurnCount.value + 1)))

const currentHour = new Date().getHours()
const timeScene = currentHour < 6
  ? { className: 'time-dawn', label: '별빛이 머무는 새벽' }
  : currentHour < 12
    ? { className: 'time-morning', label: '햇살이 드는 아침' }
    : currentHour < 18
      ? { className: 'time-day', label: '느긋한 오후' }
      : { className: 'time-night', label: '노을이 내려앉은 밤' }
const timeSceneClass = timeScene.className
const timeSceneLabel = timeScene.label

const sceneStatusText = computed(() => {
  if (!sessionId.value) return '방으로 들어가는 중'
  if (isRecording.value) return '네 목소리를 듣는 중'
  if (isTyping.value) return `${displayCharacter.value.name}가 생각하는 중`
  if (isCharacterSpeaking.value) return `${displayCharacter.value.name}가 이야기하는 중`
  return `${displayCharacter.value.name}와 함께 머무는 중`
})

const ACTIONS_BY_EMOTION = {
  default: [
    { label: '오늘 있었던 일부터 말한다', message: '오늘 있었던 일부터 천천히 이야기해볼게.' },
    { label: '지금 마음을 솔직하게 보여준다', message: '지금 내 마음이 어떤지 솔직하게 말해보고 싶어.' },
    { label: '말 대신 사진을 건넨다', type: 'photo' },
  ],
  normal: [
    { label: '오늘 가장 기억나는 순간을 꺼낸다', message: '오늘 있었던 일 중에 가장 기억나는 순간부터 말해볼게.' },
    { label: '친구의 하루를 먼저 묻는다', message: '내 이야기 전에, 너는 오늘 어떻게 지냈어?' },
    { label: '말 대신 사진을 건넨다', type: 'photo' },
  ],
  joy: [
    { label: '좋았던 순간을 더 들려준다', message: '그때 정말 좋았어. 조금 더 자세히 이야기해도 돼?' },
    { label: '이 기분을 함께 기억해 달라고 한다', message: '오늘의 이 기분, 우리 같이 기억해두자.' },
    { label: '함께 기뻐해 달라고 한다', message: '나랑 조금만 더 같이 기뻐해줘!' },
  ],
  sadness: [
    { label: '조금 더 솔직하게 털어놓는다', message: '사실은 괜찮은 척했어. 조금 더 솔직하게 말해볼게.' },
    { label: '잠깐 말없이 곁에 있어 달라고 한다', message: '지금은 해결책보다 그냥 잠깐 곁에 있어줬으면 좋겠어.' },
    { label: '천천히 다른 이야기로 넘어간다', message: '이 이야기는 잠깐 내려놓고, 조금 가벼운 얘기를 해볼까?' },
  ],
  anger: [
    { label: '무엇이 화났는지 정확히 말한다', message: '내가 정확히 어떤 부분에서 화가 났는지 말해볼게.' },
    { label: '내 편이 되어 달라고 한다', message: '지금만큼은 판단하지 말고 내 편이 되어줬으면 좋겠어.' },
    { label: '숨을 고르고 다시 이야기한다', message: '잠깐 숨을 고르고, 처음부터 차근차근 다시 말해볼게.' },
  ],
}

const sceneActions = computed(() => ACTIONS_BY_EMOTION[currentEmotion.value] || ACTIONS_BY_EMOTION.default)

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
  if (m.tts_task_id && ttsEnabled.value) {
    m.displayed = ''                    // 음성 시작까지 잠깐 '…' 표시
    messages.value.push(m)
    const target = messages.value[messages.value.length - 1]   // 반응형 프록시로 조작
    playTask(m.tts_task_id, {
      onStart: (d, alignment, audioEl) => animateReveal(target, d, alignment, audioEl),
      onFail: () => animateReveal(target, null, null, null),   // 실패해도 즉시 덤프 대신 타이핑 (2026-07-12)
    })
    setTimeout(() => {                  // 안전장치: TTS 생성이 8초+ 걸릴 수 있어 폴링 타임아웃(~28초)보다 늦게
      if (target.displayed !== target.content && !target._revealTimer) revealNow(target)
    }, 30000)
    return target
  }
  // 음소거·TTS 없음 — 글자만이라도 생동감 있게 (균등 타이핑, 55ms/자)
  m.displayed = ''
  messages.value.push(m)
  const target = messages.value[messages.value.length - 1]
  animateReveal(target, null, null, null)
  return target
}

// ── 세션 초기화: 콜드스타트 게이팅 (감정 선택지 먼저) ──
// (대화 이어보기는 검토 후 불채택 — 2026-07-12. 만날 때마다 새 시작 컨셉 유지.
//  과거는 화면이 아니라 챗봇의 기억(그래프)과 주간 리포트로만 남는다)

async function initSession() {
  try {
    // 친구 컨셉: 감정 안 묻고 날씨/시간/닉네임 기반 첫인사로 시작
    const coords = await getCoordsOrNull()
    const sess = await chatApi.startSession(character.value, isSecret.value, coords, ttsEnabled.value)
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

function moteStyle(index) {
  const x = (index * 37 + 11) % 96
  const y = (index * 53 + 17) % 78
  const delay = (index % 6) * -0.8
  const duration = 5 + (index % 5) * 1.1
  return {
    left: `${x}%`,
    top: `${y}%`,
    animationDelay: `${delay}s`,
    animationDuration: `${duration}s`,
  }
}

async function chooseSceneAction(action) {
  if (isTyping.value) return
  if (action.type === 'photo') {
    fileInputRef.value?.click()
    return
  }
  inputText.value = action.message
  await nextTick()
  await sendMessage()
}

function skipCurrentDialogue() {
  if (!latestAssistantMessage.value || !isCharacterSpeaking.value) return
  revealNow(latestAssistantMessage.value)
  ttsStop()
}

async function openChatLog() {
  showChatLog.value = true
  await nextTick()
  if (logThreadRef.value) logThreadRef.value.scrollTop = logThreadRef.value.scrollHeight
}

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
  if (inputRef.value) inputRef.value.style.height = 'auto'
  isTyping.value = true
  await scrollToBottom()
  try {
    const res = await chatApi.sendChat(sessionId.value, content, character.value, isSecret.value, image, ttsEnabled.value)
    const m = pushAssistant(res.message.text, {
      id: res.message_id ?? undefined,
      emotion_label: res.emotion_label,
      tts_task_id: res.tts_task_id,
      suggestPage: res.ui?.suggest_page || null,     // 대화 맥락 바로가기 칩 (2026-07-12)
      suggestLabel: res.ui?.suggest_label || null,
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


/* 🔊 TTS 음소거 토글 */
.tts-toggle.tts-off {
  opacity: 0.55;
  filter: grayscale(0.6);
}


/* 대화 맥락 바로가기 칩 */
.suggest-chip {
  margin: 6px 4px 0;
  padding: 7px 14px;
  border-radius: 16px;
  border: 1px solid rgba(251, 191, 119, 0.55);
  background: rgba(251, 191, 119, 0.14);
  color: #FBBF77;
  font-size: 0.85rem;
  cursor: pointer;
  transition: background 0.15s;
}
.suggest-chip:hover { background: rgba(251, 191, 119, 0.28); }

/* ── Immersive chat scene ───────────────────────────────────── */
.chat-page {
  --scene-ink: #fff8f2;
  --scene-muted: rgba(255, 244, 238, 0.58);
  --scene-line: rgba(255, 209, 193, 0.17);
  --scene-pink: #f05b77;
  --scene-coral: #f18570;
  --scene-gold: #f6c477;
  height: calc(100dvh - var(--bt-header-h, 88px));
  min-height: 620px;
  isolation: isolate;
  color: var(--scene-ink);
}

.chat-bg:not(.chat-bg--secret)::after {
  background:
    radial-gradient(circle at 18% 45%, rgba(147, 22, 114, 0.12), transparent 34%),
    linear-gradient(180deg, rgba(13, 5, 32, 0.22), rgba(20, 8, 48, 0.52) 55%, rgba(13, 5, 32, 0.76));
}

.chat-page::before {
  content: none;
  position: absolute;
  inset: 0;
  z-index: 1;
  pointer-events: none;
  opacity: 0.22;
  background-image:
    linear-gradient(rgba(255,255,255,.018) 1px, transparent 1px),
    linear-gradient(90deg, rgba(255,255,255,.018) 1px, transparent 1px);
  background-size: 44px 44px;
  mask-image: linear-gradient(to bottom, black, transparent 75%);
}

.chat-shell {
  width: min(1560px, calc(100% - 48px));
  height: 100%;
  min-height: 0;
  margin: 0 auto;
  padding: 14px 0 22px;
  display: grid;
  grid-template-rows: auto minmax(0, 1fr);
  gap: 12px;
}

.scene-header {
  min-height: 60px;
  padding: 0 4px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 24px;
}

.scene-title {
  display: grid;
  gap: 2px;
}

.scene-kicker,
.dialogue-eyebrow,
.companion-label {
  color: rgba(246, 196, 119, 0.78);
  font-size: 10px;
  font-weight: 900;
  letter-spacing: 0.18em;
}

.scene-heading-row {
  display: flex;
  align-items: baseline;
  gap: 12px;
}

.scene-heading-row h1 {
  font-family: var(--font-display);
  font-size: clamp(26px, 2.1vw, 36px);
  font-weight: 400;
  line-height: 1;
  letter-spacing: 0.01em;
  text-shadow: 0 5px 24px rgba(31, 8, 42, 0.48);
}

.scene-number {
  padding-left: 12px;
  border-left: 1px solid rgba(255, 236, 224, 0.24);
  color: rgba(255, 236, 224, 0.42);
  font-size: 10px;
  font-weight: 800;
  letter-spacing: 0.14em;
}

.scene-status {
  min-height: 38px;
  padding: 0 16px;
  display: inline-flex;
  align-items: center;
  gap: 9px;
  border: 1px solid rgba(255,255,255,0.11);
  border-radius: 999px;
  background: rgba(19, 7, 38, 0.38);
  color: rgba(255, 245, 239, 0.68);
  font-size: 12px;
  font-weight: 700;
  box-shadow: inset 0 1px 0 rgba(255,255,255,.06);
  backdrop-filter: blur(14px);
}

.status-dot,
.online-pip {
  width: 7px;
  height: 7px;
  border-radius: 50%;
  background: rgba(255,255,255,.26);
}

.status-dot.online,
.online-pip {
  background: #71e0b2;
  box-shadow: 0 0 0 4px rgba(113,224,178,.1), 0 0 12px rgba(113,224,178,.55);
}

.status-divider {
  width: 1px;
  height: 13px;
  background: rgba(255,255,255,.16);
}

.chat-stage {
  min-height: 0;
  display: grid;
  grid-template-columns: minmax(290px, 350px) minmax(0, 1fr);
  border: 1px solid rgba(255, 209, 193, 0.17);
  border-radius: 28px;
  overflow: hidden;
  background: rgba(18, 7, 35, 0.46);
  box-shadow:
    0 28px 80px rgba(8, 2, 20, 0.42),
    inset 0 1px 0 rgba(255,255,255,.08);
  backdrop-filter: blur(22px);
}

.companion-panel {
  position: relative;
  min-height: 0;
  padding: 22px 28px 24px;
  display: flex;
  flex-direction: column;
  align-items: stretch;
  overflow: hidden;
  border-right: 1px solid var(--scene-line);
  background:
    radial-gradient(circle at 50% 32%, rgba(238, 93, 95, 0.17), transparent 42%),
    linear-gradient(165deg, rgba(82, 30, 89, 0.54), rgba(25, 10, 48, 0.82));
}

.companion-panel::before {
  content: "";
  position: absolute;
  inset: 0;
  pointer-events: none;
  background:
    linear-gradient(90deg, transparent 49.7%, rgba(255,255,255,.035) 50%, transparent 50.3%),
    linear-gradient(transparent 49.7%, rgba(255,255,255,.025) 50%, transparent 50.3%);
}

.panel-corner {
  position: absolute;
  width: 34px;
  height: 34px;
  opacity: .48;
  pointer-events: none;
}

.panel-corner--tl {
  top: 14px;
  left: 14px;
  border-top: 1px solid var(--scene-gold);
  border-left: 1px solid var(--scene-gold);
}

.panel-corner--br {
  right: 14px;
  bottom: 14px;
  border-right: 1px solid var(--scene-gold);
  border-bottom: 1px solid var(--scene-gold);
}

.companion-status {
  position: relative;
  z-index: 2;
  align-self: flex-start;
  display: inline-flex;
  align-items: center;
  gap: 9px;
  color: rgba(255,255,255,.58);
  font-size: 11px;
  font-weight: 800;
  letter-spacing: .08em;
}

.character-stage {
  position: relative;
  z-index: 1;
  min-height: 210px;
  flex: 1 1 auto;
  display: grid;
  place-items: center;
}

.character-aura {
  position: absolute;
  width: min(76%, 250px);
  aspect-ratio: 1;
  border: 1px solid color-mix(in srgb, var(--character-color), transparent 62%);
  border-radius: 50%;
  opacity: .7;
  box-shadow:
    0 0 70px color-mix(in srgb, var(--character-color), transparent 82%),
    inset 0 0 60px color-mix(in srgb, var(--character-color), transparent 88%);
  animation: auraBreathe 4.8s ease-in-out infinite;
}

.character-aura::before,
.character-aura::after {
  content: "";
  position: absolute;
  inset: 11px;
  border: 1px dashed color-mix(in srgb, var(--character-color), transparent 70%);
  border-radius: 50%;
  animation: orbit 30s linear infinite;
}

.character-aura::after {
  inset: -10px;
  border-style: solid;
  border-color: transparent color-mix(in srgb, var(--character-color), transparent 42%);
  animation-direction: reverse;
  animation-duration: 18s;
}

.char-face {
  position: relative;
  z-index: 2;
  width: min(88%, 275px);
  height: auto;
  aspect-ratio: 1;
  margin: 0;
  border: 0;
  border-radius: 0;
  background: transparent !important;
  box-shadow: none;
}

.character-image-frame img {
  width: 108%;
  height: 108%;
  filter: drop-shadow(0 24px 26px rgba(5, 2, 14, .44));
}

.stage-shadow {
  position: absolute;
  z-index: 0;
  bottom: 10%;
  width: 64%;
  height: 22px;
  border-radius: 50%;
  background: rgba(6,2,15,.42);
  filter: blur(9px);
}

.companion-info {
  position: relative;
  z-index: 2;
  padding-top: 13px;
  border-top: 1px solid rgba(255,255,255,.1);
}

.companion-name-row {
  margin-top: 4px;
  display: flex;
  align-items: center;
  gap: 10px;
}

.companion-name-row h2 {
  font-family: var(--font-display);
  font-size: 28px;
  font-weight: 400;
}

.affinity-badge {
  padding: 3px 8px;
  border: 1px solid rgba(246,196,119,.32);
  border-radius: 999px;
  background: rgba(246,196,119,.1);
  color: #f6cf91;
  font-size: 10px;
  font-weight: 800;
}

.companion-info p {
  margin-top: 4px;
  color: var(--scene-muted);
  font-family: var(--font-soft);
  font-size: 13px;
  line-height: 1.5;
}

.bond-meter {
  position: relative;
  z-index: 2;
  margin-top: 16px;
}

.bond-label {
  margin-bottom: 7px;
  display: flex;
  justify-content: space-between;
  color: rgba(255,255,255,.5);
  font-size: 10px;
  font-weight: 800;
}

.bond-label strong { color: #f5c98d; }

.bond-track {
  height: 5px;
  overflow: hidden;
  border-radius: 999px;
  background: rgba(255,255,255,.1);
}

.bond-track i {
  display: block;
  height: 100%;
  border-radius: inherit;
  background: linear-gradient(90deg, var(--scene-pink), var(--scene-gold));
  box-shadow: 0 0 12px rgba(246,196,119,.42);
  transition: width .5s ease;
}

.secret-mode-btn,
.secret-note {
  position: relative;
  z-index: 2;
  width: 100%;
  margin-top: 16px;
  padding: 11px 13px;
  display: flex;
  align-items: center;
  gap: 10px;
  border: 1px solid rgba(255,255,255,.12);
  border-radius: 14px;
  background: rgba(255,255,255,.055);
  color: rgba(255,255,255,.78);
  text-align: left;
  transition: border-color .2s, background .2s, transform .2s;
}

.secret-mode-btn:hover {
  transform: translateY(-1px);
  border-color: rgba(246,196,119,.34);
  background: rgba(246,196,119,.09);
}

.secret-mode-btn > span:nth-child(2) {
  min-width: 0;
  display: grid;
  gap: 1px;
}

.secret-mode-btn strong { font-size: 12px; }
.secret-mode-btn small { color: rgba(255,255,255,.42); font-size: 10px; }
.button-icon { color: #f5c98d; font-size: 17px; }
.button-arrow { margin-left: auto; color: rgba(255,255,255,.35); font-size: 22px; }

.secret-note {
  color: #c6d7ff;
  font-size: 12px;
  text-align: left;
  line-height: 1.5;
}

.secret-note > span { font-size: 17px; }

.dialogue-panel {
  min-width: 0;
  min-height: 0;
  display: grid;
  grid-template-rows: auto minmax(0, 1fr) auto auto;
  background:
    linear-gradient(180deg, rgba(20,8,39,.38), rgba(13,5,30,.7)),
    radial-gradient(circle at 70% 0%, rgba(231,62,101,.08), transparent 45%);
}

.dialogue-topbar {
  min-height: 58px;
  padding: 10px 24px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  border-bottom: 1px solid var(--scene-line);
  background: rgba(13,5,32,.24);
}

.dialogue-topbar > div {
  display: grid;
  gap: 2px;
}

.dialogue-topbar strong {
  color: rgba(255,248,244,.88);
  font-size: 13px;
}

.privacy-state {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  color: rgba(255,255,255,.48);
  font-size: 10px;
  font-weight: 800;
}

.privacy-state > span { color: #75dbb4; }
.privacy-state.secret { color: #c6d7ff; }
.privacy-state.secret > span { color: #9eb8ff; }

.chat-thread {
  min-height: 0;
  padding: 20px clamp(24px, 4vw, 58px) 24px;
  gap: 17px;
  background: transparent;
  scroll-behavior: smooth;
}

.chapter-divider {
  display: flex;
  align-items: center;
  gap: 12px;
  color: rgba(255,255,255,.28);
  font-size: 10px;
  font-weight: 800;
  letter-spacing: .08em;
}

.chapter-divider::before,
.chapter-divider::after {
  content: "";
  height: 1px;
  flex: 1;
  background: linear-gradient(90deg, transparent, rgba(255,255,255,.11));
}

.chapter-divider::after { transform: rotate(180deg); }

.bubble-wrap { max-width: min(78%, 760px); }

.message-speaker,
.message-owner {
  margin: 0 4px 6px;
  color: rgba(255,255,255,.4);
  font-size: 10px;
  font-weight: 800;
  letter-spacing: .05em;
}

.message-owner { margin: 5px 4px 0; }
.speaker-mark { margin-right: 6px; color: #f5c98d; }

.bubble {
  position: relative;
  padding: 14px 18px;
  border-radius: 18px;
  font-family: var(--font-soft);
  font-size: clamp(14px, 1.06vw, 16px);
  line-height: 1.7;
  box-shadow: 0 12px 30px rgba(5,2,15,.12);
}

.bubble-char {
  border: 1px solid rgba(255,236,225,.14);
  border-top-left-radius: 5px;
  background:
    linear-gradient(145deg, rgba(255,255,255,.11), rgba(255,255,255,.06)),
    rgba(50,24,73,.28);
  color: rgba(255,250,246,.93);
}

.bubble-char::before {
  content: "";
  position: absolute;
  top: -1px;
  left: 0;
  width: 36px;
  height: 1px;
  background: linear-gradient(90deg, #f6c477, transparent);
}

.bubble-user {
  border: 1px solid rgba(255, 165, 143, .28);
  border-bottom-right-radius: 5px;
  background: linear-gradient(135deg, rgba(231,62,101,.72), rgba(238,93,95,.66) 56%, rgba(231,126,110,.58));
  color: #fffaf6;
  box-shadow: 0 14px 34px rgba(147,22,114,.18);
}

.typing-wrap {
  display: flex;
  align-items: center;
  gap: 8px;
}

.typing-avatar {
  width: 27px;
  height: 27px;
  display: grid;
  place-items: center;
  border: 1px solid rgba(246,196,119,.2);
  border-radius: 50%;
  background: rgba(246,196,119,.08);
  color: #f5c98d;
  font-size: 10px;
}

.typing-indicator {
  padding: 9px 14px;
  border-color: rgba(255,255,255,.11);
  background: rgba(255,255,255,.06);
}

.prompt-deck {
  padding: 11px 24px;
  display: flex;
  align-items: center;
  gap: 14px;
  border-top: 1px solid rgba(255,255,255,.07);
  background: rgba(13,5,32,.18);
}

.prompt-deck > span {
  flex: 0 0 auto;
  color: rgba(255,255,255,.36);
  font-size: 10px;
  font-weight: 800;
}

.prompt-list {
  min-width: 0;
  display: flex;
  gap: 7px;
  overflow-x: auto;
  scrollbar-width: none;
}

.prompt-list::-webkit-scrollbar { display: none; }

.prompt-list button {
  flex: 0 0 auto;
  padding: 7px 12px;
  border: 1px solid rgba(255,211,194,.14);
  border-radius: 999px;
  background: rgba(255,255,255,.045);
  color: rgba(255,244,238,.62);
  font-size: 11px;
  font-weight: 700;
  transition: background .2s, border-color .2s, color .2s;
}

.prompt-list button:hover {
  border-color: rgba(246,196,119,.38);
  background: rgba(246,196,119,.09);
  color: #fff4e7;
}

.input-zone {
  padding: 12px 18px 16px;
  border-top: 1px solid var(--scene-line);
  background: rgba(10,4,25,.52);
  backdrop-filter: blur(18px);
}

.tool-row {
  min-height: 28px;
  margin-bottom: 8px;
  display: flex;
  align-items: center;
  gap: 6px;
}

.tool-btn {
  min-height: 27px;
  padding: 0 9px;
  display: inline-flex;
  align-items: center;
  gap: 5px;
  border: 1px solid rgba(255,255,255,.09);
  border-radius: 8px;
  background: rgba(255,255,255,.04);
  color: rgba(255,255,255,.5);
  font-size: 10px;
  font-weight: 800;
  transition: background .2s, color .2s, border-color .2s;
}

.tool-btn > span { color: rgba(246,196,119,.72); }

.tool-btn:hover:not(:disabled) {
  border-color: rgba(246,196,119,.28);
  background: rgba(246,196,119,.08);
  color: rgba(255,255,255,.82);
}

.input-guide {
  margin-left: auto;
  color: rgba(255,255,255,.25);
  font-size: 9px;
  font-weight: 700;
}

.input-bar {
  min-height: 56px;
  padding: 6px 7px 6px 18px;
  display: flex;
  align-items: center;
  gap: 10px;
  border: 1px solid rgba(255,218,204,.18);
  border-radius: 17px;
  background:
    linear-gradient(145deg, rgba(255,255,255,.075), rgba(255,255,255,.035)),
    rgba(45,17,65,.42);
  box-shadow: inset 0 1px 0 rgba(255,255,255,.07), 0 12px 30px rgba(5,2,15,.18);
  transition: border-color .2s, box-shadow .2s;
}

.input-bar:focus-within {
  border-color: rgba(246,196,119,.42);
  box-shadow: inset 0 1px 0 rgba(255,255,255,.08), 0 0 0 3px rgba(246,196,119,.06);
}

.msg-input {
  min-height: 24px;
  max-height: 110px;
  padding: 3px 0;
  border: 0;
  border-radius: 0;
  background: transparent;
  color: #fffaf6;
  font-family: var(--font-soft);
  font-size: 14px;
  line-height: 1.55;
}

.msg-input:focus { border: 0; outline: none; }
.msg-input::placeholder { color: rgba(255,244,238,.32); }

.char-count {
  color: rgba(255,255,255,.25);
  font-size: 9px;
}

.send-btn {
  min-width: 94px;
  min-height: 44px;
  padding: 0 15px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 9px;
  border: 1px solid rgba(255,230,213,.18);
  border-radius: 12px;
  background: linear-gradient(135deg, #e73e65, #ee5d5f 52%, #e77e6e);
  color: #fff;
  font-size: 12px;
  font-weight: 900;
  box-shadow: 0 8px 24px rgba(231,62,101,.22), inset 0 1px 0 rgba(255,255,255,.22);
}

.send-btn i {
  font-size: 12px;
  font-style: normal;
  transition: transform .2s;
}

.send-btn:not(:disabled):hover { opacity: 1; transform: translateY(-1px); }
.send-btn:not(:disabled):hover i { transform: translateX(2px); }
.send-btn:disabled { filter: saturate(.35); opacity: .34; }

.img-preview {
  width: 100%;
  margin: 0 0 9px;
  padding: 8px 38px 8px 8px;
  display: flex;
  align-items: center;
  gap: 10px;
  border: 1px solid rgba(255,255,255,.1);
  border-radius: 12px;
  background: rgba(255,255,255,.04);
}

.img-preview img {
  width: 48px;
  height: 48px;
  object-fit: cover;
  border-radius: 8px;
}

.img-preview > div {
  display: grid;
  gap: 2px;
  font-size: 11px;
}

.img-preview > div span { color: rgba(255,255,255,.4); font-size: 10px; }
.img-preview-remove { top: 50%; right: 10px; transform: translateY(-50%); }

.suggest-chip {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  border-radius: 10px;
  border-color: rgba(246,196,119,.32);
  background: rgba(246,196,119,.08);
  color: #f6cf91;
  font-size: 11px;
  font-weight: 800;
}

.is-secret .chat-stage {
  border-color: rgba(158,184,255,.19);
  box-shadow: 0 28px 80px rgba(2,5,24,.5), inset 0 1px 0 rgba(255,255,255,.07);
}

.is-secret .companion-panel {
  border-color: rgba(158,184,255,.15);
  background:
    radial-gradient(circle at 50% 30%, rgba(113,143,224,.16), transparent 42%),
    linear-gradient(165deg, rgba(31,42,91,.55), rgba(8,12,43,.84));
}

.is-secret .input-zone,
.is-secret .dialogue-topbar { border-color: rgba(158,184,255,.14); }

.is-secret .input-bar:focus-within { border-color: rgba(158,184,255,.46); }

.is-secret .send-btn {
  border-color: rgba(220,230,255,.2);
  background: linear-gradient(135deg, #6f8bd4, #91a9e9);
  color: #08102c;
  box-shadow: 0 8px 24px rgba(83,111,185,.25), inset 0 1px 0 rgba(255,255,255,.3);
}

@keyframes auraBreathe {
  0%, 100% { transform: scale(.96); opacity: .55; }
  50% { transform: scale(1.02); opacity: .82; }
}

@keyframes orbit { to { transform: rotate(360deg); } }

@media (max-width: 1040px) {
  .chat-page { min-height: 560px; }
  .chat-shell { width: min(100% - 28px, 1560px); padding-bottom: 14px; }
  .chat-stage { grid-template-columns: 240px minmax(0, 1fr); }
  .companion-panel { padding: 18px; }
  .character-stage { min-height: 170px; }
  .companion-info p, .bond-meter { display: none; }
  .prompt-deck { padding-inline: 16px; }
  .chat-thread { padding-inline: 28px; }
}

@media (max-width: 760px) {
  .chat-page {
    height: auto;
    min-height: calc(100dvh - var(--bt-header-h, 88px));
    overflow: visible;
  }

  .chat-shell {
    width: calc(100% - 20px);
    height: auto;
    min-height: calc(100dvh - var(--bt-header-h, 88px));
    padding: 10px 0;
  }

  .scene-header { min-height: 48px; }
  .scene-heading-row h1 { font-size: 25px; }
  .scene-kicker, .scene-number { display: none; }
  .scene-status { min-height: 32px; padding: 0 10px; }
  .scene-status .status-divider,
  .scene-status span:last-child { display: none; }

  .chat-stage {
    min-height: calc(100dvh - var(--bt-header-h, 88px) - 68px);
    display: flex;
    flex-direction: column;
    border-radius: 20px;
    overflow: visible;
  }

  .companion-panel {
    min-height: 102px;
    padding: 12px 14px;
    display: grid;
    grid-template-columns: 78px minmax(0, 1fr) auto;
    grid-template-rows: 1fr;
    align-items: center;
    gap: 12px;
    border-right: 0;
    border-bottom: 1px solid var(--scene-line);
    border-radius: 20px 20px 0 0;
  }

  .companion-status, .bond-meter, .panel-corner { display: none; }
  .character-stage { grid-column: 1; min-height: 76px; height: 76px; }
  .character-aura { width: 72px; }
  .char-face { width: 82px; }
  .stage-shadow { bottom: 2px; }
  .companion-info { grid-column: 2; padding: 0; border: 0; }
  .companion-label { font-size: 8px; }
  .companion-name-row h2 { font-size: 22px; }
  .companion-info p { display: block; font-size: 11px; }

  .secret-mode-btn,
  .secret-note {
    grid-column: 3;
    width: 42px;
    height: 42px;
    margin: 0;
    padding: 0;
    justify-content: center;
    border-radius: 12px;
  }

  .secret-mode-btn > span:nth-child(2),
  .secret-mode-btn .button-arrow,
  .secret-note p { display: none; }

  .dialogue-panel {
    min-height: 560px;
    flex: 1;
    grid-template-rows: auto minmax(310px, 1fr) auto auto;
    border-radius: 0 0 20px 20px;
  }

  .dialogue-topbar { min-height: 48px; padding: 8px 14px; }
  .chat-thread { padding: 16px 14px 20px; gap: 14px; }
  .bubble-wrap { max-width: 88%; }
  .bubble { padding: 12px 14px; font-size: 14px; }
  .prompt-deck { display: block; padding: 9px 12px; }
  .prompt-deck > span { display: none; }
  .input-zone { padding: 9px 10px 12px; border-radius: 0 0 20px 20px; }
  .input-guide { display: none; }
  .tool-row { overflow-x: auto; scrollbar-width: none; }
  .tool-btn { flex: 0 0 auto; }
  .input-bar { padding-left: 13px; gap: 7px; }
  .char-count { display: none; }
  .send-btn { min-width: 48px; width: 48px; padding: 0; }
  .send-btn span { display: none; }
}

@media (max-height: 720px) and (min-width: 761px) {
  .chat-page { min-height: 540px; }
  .chat-shell { padding-top: 8px; padding-bottom: 12px; }
  .scene-header { min-height: 48px; }
  .scene-heading-row h1 { font-size: 28px; }
  .companion-panel { padding-block: 16px; }
  .character-stage { min-height: 170px; }
  .companion-info p, .bond-meter { display: none; }
  .chat-thread { padding-block: 15px; }
  .prompt-deck { padding-block: 8px; }
  .input-zone { padding-block: 9px 11px; }
}

@media (prefers-reduced-motion: reduce) {
  .character-aura,
  .character-aura::before,
  .character-aura::after { animation: none; }
  .chat-thread { scroll-behavior: auto; }
}

/* ── Visual novel mind-room experience ─────────────────────── */
.vn-shell {
  width: min(1620px, calc(100% - 36px));
  flex: 1 1 auto;
  min-height: 0;
  margin: 0 auto;
  padding: 14px 0 18px;
}

.mind-room {
  position: relative;
  width: 100%;
  height: 100%;
  min-height: 0;
  overflow: hidden;
  border: 1px solid rgba(255, 220, 204, .2);
  border-radius: 30px;
  background: linear-gradient(180deg, rgba(42, 15, 57, .16), rgba(13, 5, 32, .42));
  box-shadow:
    0 30px 100px rgba(5, 1, 17, .5),
    inset 0 1px 0 rgba(255, 255, 255, .1);
  backdrop-filter: none;
  isolation: isolate;
}

.mind-room::before,
.mind-room::after {
  content: "";
  position: absolute;
  inset: 0;
  pointer-events: none;
}

.mind-room::before {
  z-index: 1;
  opacity: .26;
  background: radial-gradient(circle at 50% 43%, rgba(231, 126, 110, .22), transparent 38%);
  transition: background 1.2s ease, opacity 1.2s ease;
}

.mind-room::after {
  z-index: 2;
  display: none;
  opacity: 0;
  background-image:
    linear-gradient(rgba(255,255,255,.028) 1px, transparent 1px),
    linear-gradient(90deg, rgba(255,255,255,.022) 1px, transparent 1px);
  background-size: 52px 52px;
  mask-image: linear-gradient(to bottom, #000, transparent 74%);
}

.mood-joy .mind-room::before {
  opacity: .34;
  background:
    radial-gradient(circle at 50% 43%, rgba(255, 206, 105, .3), transparent 38%);
}

.mood-sadness .mind-room::before {
  opacity: .34;
  background:
    radial-gradient(circle at 50% 43%, rgba(101, 136, 211, .28), transparent 38%);
}

.mood-anger .mind-room::before {
  opacity: .34;
  background:
    radial-gradient(circle at 50% 43%, rgba(222, 82, 83, .3), transparent 38%);
}

.is-secret .mind-room {
  border-color: rgba(159, 184, 255, .22);
  background: linear-gradient(180deg, rgba(25, 30, 77, .22), rgba(5, 7, 28, .48));
  box-shadow: 0 30px 100px rgba(1, 3, 17, .6), inset 0 1px 0 rgba(255,255,255,.08);
}

.is-secret .mind-room::before {
  background: radial-gradient(circle at 50% 43%, rgba(131, 158, 229, .24), transparent 38%);
}

.room-atmosphere {
  position: absolute;
  inset: 0;
  z-index: 0;
  overflow: hidden;
  pointer-events: none;
}

.window-glow,
.curtain,
.floor-light,
.light-mote { display: none; }

.window-glow {
  position: absolute;
  top: -12%;
  right: 4%;
  width: 42%;
  height: 70%;
  transform: skewX(-8deg);
  opacity: .46;
  background: linear-gradient(155deg, rgba(255, 222, 180, .32), rgba(244, 112, 118, .08) 54%, transparent 70%);
  filter: blur(3px);
  transition: opacity 1s ease, filter 1s ease;
}

.time-morning .window-glow { opacity: .72; filter: hue-rotate(-12deg) brightness(1.18); }
.time-day .window-glow { opacity: .58; filter: brightness(1.06); }
.time-dawn .window-glow,
.time-night .window-glow { opacity: .33; filter: hue-rotate(24deg); }
.mood-sadness .window-glow { opacity: .22; filter: hue-rotate(45deg); }
.mood-joy .window-glow { opacity: .78; filter: saturate(1.18) brightness(1.1); }

.curtain {
  position: absolute;
  top: -4%;
  width: 17%;
  height: 83%;
  opacity: .38;
  filter: blur(1px);
  background:
    repeating-linear-gradient(90deg, rgba(34,10,54,.85) 0 24px, rgba(91,35,92,.62) 24px 44px);
  box-shadow: 0 0 50px rgba(4,1,14,.38);
}

.curtain--left { left: -10%; transform: skewX(4deg); }
.curtain--right { right: -11%; transform: skewX(-5deg); }

.floor-light {
  position: absolute;
  left: 7%;
  right: 7%;
  bottom: 0;
  height: 30%;
  opacity: .35;
  transform: perspective(420px) rotateX(62deg);
  transform-origin: bottom;
  background:
    linear-gradient(90deg, transparent, rgba(255, 190, 155, .15), transparent),
    repeating-linear-gradient(90deg, transparent 0 98px, rgba(255,255,255,.05) 99px 100px);
  mask-image: linear-gradient(to bottom, transparent, black);
}

.light-mote {
  position: absolute;
  width: 4px;
  height: 4px;
  z-index: 2;
  border-radius: 50%;
  background: #ffe3a8;
  opacity: 0;
  box-shadow: 0 0 12px rgba(255, 213, 139, .9);
  animation: moteFloat 7s ease-in-out infinite;
}

.mood-sadness .light-mote,
.is-secret .light-mote {
  background: #c9d9ff;
  box-shadow: 0 0 12px rgba(157,185,255,.9);
}

.room-header {
  position: absolute;
  z-index: 12;
  top: 0;
  left: 0;
  right: 0;
  min-height: 70px;
  padding: 14px 20px 12px 24px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 18px;
  border-bottom: 1px solid rgba(255,255,255,.08);
  background: linear-gradient(180deg, rgba(10,3,25,.48), rgba(10,3,25,.12));
}

.room-plaque {
  display: flex;
  align-items: center;
  gap: 11px;
}

.room-symbol {
  width: 37px;
  height: 37px;
  display: grid;
  place-items: center;
  border: 1px solid rgba(246,196,119,.26);
  border-radius: 50%;
  background: rgba(246,196,119,.08);
  color: #f6cb8a;
  box-shadow: 0 0 20px rgba(246,196,119,.08);
}

.room-plaque > span:last-child { display: grid; gap: 1px; }
.room-plaque small { color: rgba(255,243,233,.4); font-size: 9px; font-weight: 800; letter-spacing: .1em; }
.room-plaque strong { font-family: var(--font-soft); font-size: 15px; font-weight: 700; }

.room-controls {
  display: flex;
  align-items: center;
  gap: 7px;
}

.presence-state {
  margin-right: 7px;
  display: inline-flex;
  align-items: center;
  gap: 7px;
  color: rgba(255,255,255,.43);
  font-size: 10px;
  font-weight: 700;
}

.presence-state i {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: #70ddb0;
  box-shadow: 0 0 10px rgba(112,221,176,.75);
}

.room-control {
  min-height: 34px;
  padding: 0 10px;
  display: inline-flex;
  align-items: center;
  gap: 6px;
  border: 1px solid rgba(255,255,255,.1);
  border-radius: 10px;
  background: rgba(255,255,255,.045);
  color: rgba(255,247,241,.57);
  font-size: 10px;
  transition: color .2s, background .2s, border-color .2s;
}

.room-control span { color: #f3c989; }
.room-control b { font-weight: 800; }
.room-control:hover { border-color: rgba(246,196,119,.3); background: rgba(246,196,119,.08); color: #fff7ef; }
.room-control.muted { opacity: .58; }
.room-control--secret span { color: #aebff3; }
.room-control--exit { border-color: rgba(158,184,255,.24); color: #d7e1ff; }
.room-control--exit span { color: #9eb8ff; }

.story-lights {
  position: absolute;
  z-index: 11;
  top: 50%;
  left: 22px;
  display: none;
  gap: 9px;
  transform: translateY(-50%);
}

.story-lights span {
  width: 5px;
  height: 5px;
  border: 1px solid rgba(255,255,255,.2);
  border-radius: 50%;
  transition: background .5s ease, box-shadow .5s ease, transform .5s ease;
}

.story-lights span.lit {
  transform: scale(1.18);
  border-color: #f4c983;
  background: #f4c983;
  box-shadow: 0 0 12px rgba(244,201,131,.76);
}

.character-presence {
  position: absolute;
  z-index: 14;
  top: 76px;
  right: auto;
  bottom: 104px;
  left: 0;
  width: clamp(225px, 22vw, 340px);
  height: auto;
  min-height: 0;
  max-height: none;
  box-sizing: border-box;
  display: grid;
  place-items: end center;
  overflow: hidden;
  pointer-events: none;
  transform-origin: left bottom;
  transition: filter .8s ease, transform .8s ease;
}

.character-presence::before {
  content: "";
  position: absolute;
  right: auto;
  bottom: 2%;
  left: -10%;
  width: min(27vw, 340px);
  aspect-ratio: 1;
  border-radius: 50%;
  background: radial-gradient(circle, color-mix(in srgb, var(--character-color), transparent 78%), transparent 69%);
  opacity: .36;
  filter: blur(18px);
}

.character-presence::after {
  content: "";
  position: absolute;
  z-index: 1;
  top: 16%;
  bottom: 15%;
  left: clamp(16px, 2vw, 32px);
  width: clamp(180px, 17vw, 265px);
  border-top: 1px solid color-mix(in srgb, var(--character-color), transparent 76%);
  border-left: 1px solid color-mix(in srgb, var(--character-color), transparent 82%);
  border-radius: 16px 0 0 0;
  opacity: .68;
}

.presence-ring {
  display: none;
  position: absolute;
  width: clamp(260px, 34vw, 460px);
  max-width: calc(100% - 40px);
  max-height: calc(100% - 28px);
  aspect-ratio: 1;
  border: 1px solid color-mix(in srgb, var(--character-color), transparent 72%);
  border-radius: 50%;
  opacity: .48;
  box-shadow:
    0 0 90px color-mix(in srgb, var(--character-color), transparent 86%),
    inset 0 0 100px color-mix(in srgb, var(--character-color), transparent 91%);
  animation: presenceBreathe 5s ease-in-out infinite;
}

.presence-ring::before,
.presence-ring::after {
  content: "";
  position: absolute;
  inset: 16px;
  border: 1px dashed color-mix(in srgb, var(--character-color), transparent 78%);
  border-radius: 50%;
  animation: orbit 34s linear infinite;
}

.presence-ring::after {
  inset: -10px;
  border-style: solid;
  border-color: transparent color-mix(in srgb, var(--character-color), transparent 64%);
  animation-direction: reverse;
  animation-duration: 22s;
}

.vn-character {
  position: absolute;
  z-index: 2;
  top: clamp(24px, 5vh, 62px);
  right: auto;
  bottom: 28px;
  left: clamp(14px, 1.8vw, 30px);
  width: clamp(185px, 17vw, 265px);
  min-width: 0;
  max-width: none;
  height: auto;
  min-height: 0;
  max-height: none;
  display: grid;
  place-items: center;
  transform: none;
}

.vn-character img {
  position: absolute;
  inset: 0;
  display: block;
  width: 100%;
  height: 100%;
  min-width: 0;
  min-height: 0;
  max-width: 100%;
  max-height: 100%;
  object-fit: contain;
  object-position: center bottom;
  transform-origin: center bottom;
  opacity: .94;
  filter: drop-shadow(0 20px 24px rgba(4,1,14,.46)) saturate(1.02);
  -webkit-mask-image: linear-gradient(to bottom, #000 0%, #000 86%, transparent 100%);
  mask-image: linear-gradient(to bottom, #000 0%, #000 86%, transparent 100%);
  transition: filter .8s ease, transform .8s ease, opacity .45s ease;
}

.character-hud {
  position: absolute;
  z-index: 4;
  right: auto;
  bottom: 16px;
  left: clamp(22px, 2.8vw, 44px);
  min-width: 104px;
  padding: 7px 12px 7px 9px;
  display: flex;
  align-items: center;
  gap: 8px;
  border: 1px solid color-mix(in srgb, var(--character-color), transparent 68%);
  border-radius: 10px;
  background: linear-gradient(100deg, rgba(12, 4, 27, .68), rgba(12, 4, 27, .34));
  color: rgba(255, 250, 247, .78);
  box-shadow: 0 8px 24px rgba(4, 1, 14, .18);
  backdrop-filter: blur(10px);
}

.character-hud > i {
  width: 6px;
  height: 6px;
  flex: 0 0 auto;
  border-radius: 50%;
  background: var(--character-color);
  box-shadow: 0 0 10px color-mix(in srgb, var(--character-color), transparent 24%);
}

.character-hud > span { min-width: 0; display: grid; gap: 1px; }
.character-hud b {
  overflow: hidden;
  color: rgba(255, 250, 247, .88);
  font-family: var(--font-soft);
  font-size: 9px;
  font-weight: 900;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.character-hud small {
  color: color-mix(in srgb, var(--character-color), white 28%);
  font-size: 8px;
  font-weight: 800;
  letter-spacing: .05em;
}

.emotion-shift-enter-active,
.emotion-shift-leave-active {
  transition: opacity .28s ease, transform .38s cubic-bezier(.22, .8, .24, 1), filter .38s ease;
}

.emotion-shift-enter-from {
  opacity: 0;
  transform: translateY(8px) scale(.975);
  filter: blur(3px);
}

.emotion-shift-leave-to {
  opacity: 0;
  transform: translateY(-4px) scale(.99);
  filter: blur(2px);
}

.character-ground {
  display: none;
  position: absolute;
  z-index: 1;
  bottom: 18%;
  width: min(34%, 200px);
  height: 28px;
  border-radius: 50%;
  background: rgba(4,1,14,.45);
  filter: blur(12px);
}

.character-state {
  position: absolute;
  z-index: 5;
  left: 50%;
  bottom: 0;
  min-height: 29px;
  padding: 0 12px;
  display: none;
  align-items: center;
  justify-content: center;
  border: 1px solid rgba(255,255,255,.1);
  border-radius: 999px;
  background: rgba(12,4,27,.52);
  color: rgba(255,247,241,.45);
  font-size: 9px;
  font-weight: 800;
  white-space: nowrap;
  transform: translateX(-50%);
  backdrop-filter: blur(10px);
}

.thought-dots,
.voice-wave {
  display: inline-flex;
  align-items: center;
  gap: 4px;
}

.thought-dots i {
  width: 5px;
  height: 5px;
  border-radius: 50%;
  background: rgba(255,255,255,.66);
  animation: thoughtBounce 1.1s ease-in-out infinite;
}
.thought-dots i:nth-child(2) { animation-delay: .16s; }
.thought-dots i:nth-child(3) { animation-delay: .32s; }

.voice-wave i {
  width: 2px;
  height: 8px;
  border-radius: 2px;
  background: #f4c983;
  animation: voiceWave .7s ease-in-out infinite alternate;
}
.voice-wave i:nth-child(2), .voice-wave i:nth-child(4) { animation-delay: .18s; height: 13px; }
.voice-wave i:nth-child(3) { animation-delay: .3s; height: 17px; }

.character-presence.speaking .vn-character img { animation: characterTalk 1.8s ease-in-out infinite alternate; }
.character-presence.thinking { filter: saturate(.78); transform: translateY(3px); }
.character-presence.listening .vn-character img { transform: rotate(-1deg) translateX(5px) scale(1.01); }
.mood-sadness .vn-character img { filter: drop-shadow(0 28px 34px rgba(4,1,14,.52)) saturate(.88); }
.mood-joy .vn-character img { filter: drop-shadow(0 30px 38px rgba(110,57,18,.42)) saturate(1.08); }

.user-whisper {
  position: absolute;
  z-index: 9;
  top: 17%;
  right: 6%;
  width: min(32%, 410px);
  padding: 13px 16px;
  border: 1px solid rgba(255,197,176,.16);
  border-radius: 18px 18px 5px 18px;
  background: rgba(72,24,76,.38);
  box-shadow: 0 18px 45px rgba(5,1,16,.2);
  backdrop-filter: blur(16px);
}

.user-whisper span {
  display: block;
  margin-bottom: 3px;
  color: #f2bda9;
  font-size: 9px;
  font-weight: 900;
}

.user-whisper p {
  display: -webkit-box;
  overflow: hidden;
  color: rgba(255,248,244,.7);
  font-family: var(--font-soft);
  font-size: 12px;
  line-height: 1.55;
  -webkit-box-orient: vertical;
  -webkit-line-clamp: 2;
}

.vn-dialogue {
  position: absolute;
  z-index: 15;
  top: 70px;
  right: 0;
  bottom: 0;
  left: 0;
  width: auto;
  min-height: 0;
  padding: 0;
  display: grid;
  grid-template-rows: minmax(0, 1fr) auto;
  overflow: hidden;
  border: 0;
  border-radius: 0;
  background: transparent;
  box-shadow: none;
  backdrop-filter: none;
}

.vn-dialogue::before {
  content: "";
  position: absolute;
  top: 0;
  left: 24px;
  right: 24px;
  height: 1px;
  display: none;
  background: none;
}

.is-secret .vn-dialogue {
  border-color: transparent;
  background: transparent;
}

.user-whisper { display: none; }

.chat-console-header {
  min-height: 58px;
  padding: 10px clamp(20px, 6vw, 96px);
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  border-bottom: 1px solid rgba(255,255,255,.08);
  background: rgba(10,3,28,.78);
  backdrop-filter: blur(14px);
}

.chat-peer {
  min-width: 0;
  display: flex;
  align-items: center;
  gap: 10px;
}

.chat-peer-avatar,
.chat-message-avatar {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  flex: 0 0 auto;
  border: 1px solid color-mix(in srgb, var(--character-color), transparent 54%);
  border-radius: 50%;
  background: color-mix(in srgb, var(--character-color), rgba(39,13,57,.82) 76%);
  color: #ffe0a8;
  box-shadow: 0 0 18px color-mix(in srgb, var(--character-color), transparent 82%);
  overflow: hidden;
}

.chat-peer-avatar { width: 36px; height: 36px; font-size: 12px; }
.chat-message-avatar { width: 26px; height: 26px; margin-top: 16px; font-size: 8px; }
.chat-peer-avatar img,
.chat-message-avatar img { width: 100%; height: 100%; padding: 2px; object-fit: contain; }

.chat-peer > span:last-child { min-width: 0; display: grid; gap: 2px; }
.chat-peer strong { overflow: hidden; color: #fff9f5; font-family: var(--font-soft); font-size: 13px; text-overflow: ellipsis; white-space: nowrap; }
.chat-peer small { overflow: hidden; color: rgba(255,255,255,.4); font-size: 9px; text-overflow: ellipsis; white-space: nowrap; }

.chat-online {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  flex: 0 0 auto;
  color: rgba(255,255,255,.46);
  font-size: 9px;
  font-weight: 800;
}
.chat-online i { width: 6px; height: 6px; border-radius: 50%; background: #64e6af; box-shadow: 0 0 9px rgba(100,230,175,.8); }

.chat-thread {
  min-height: 0;
  padding: 18px clamp(20px, 5vw, 76px) 22px clamp(225px, 23.5vw, 365px);
  display: flex;
  flex-direction: column;
  gap: 13px;
  overflow-x: hidden;
  overflow-y: auto;
  scroll-behavior: smooth;
  scrollbar-width: thin;
  scrollbar-color: rgba(246,196,119,.28) transparent;
  background: transparent;
}
.chat-thread::-webkit-scrollbar {
  width: 6px;
}
.chat-thread::-webkit-scrollbar-track {
  background: rgba(255, 255, 255, 0.02);
  border-radius: 4px;
}
.chat-thread::-webkit-scrollbar-thumb {
  background: rgba(246, 196, 119, 0.25);
  border-radius: 4px;
}
.chat-thread::-webkit-scrollbar-thumb:hover {
  background: rgba(246, 196, 119, 0.5);
}

.chat-empty {
  margin: auto;
  padding: 20px;
  display: grid;
  justify-items: center;
  gap: 8px;
  color: rgba(255,255,255,.38);
  font-family: var(--font-soft);
  font-size: 11px;
  text-align: center;
}
.chat-empty span { color: #f6cb8a; font-size: 16px; }

.chat-message {
  position: relative;
  z-index: 2;
  max-width: min(85%, 800px);
  display: flex;
  align-items: flex-start;
  gap: 10px;
  animation: messageSlideUp 0.4s cubic-bezier(0.2, 0.8, 0.2, 1) forwards;
}
.chat-message.assistant { align-self: flex-start; transform-origin: left bottom; }
.chat-message.user { align-self: flex-end; justify-content: flex-end; transform-origin: right bottom; }

@keyframes messageSlideUp {
  0% { opacity: 0; transform: translateY(16px) scale(0.97); filter: blur(3px); }
  100% { opacity: 1; transform: translateY(0) scale(1); filter: blur(0); }
}

.chat-message-stack { min-width: 0; display: grid; gap: 6px; }
.chat-message.user .chat-message-stack { justify-items: end; }
.chat-message-stack > small { padding-inline: 5px; color: rgba(255,255,255,.5); font-size: 10px; font-weight: 700; letter-spacing: 0.03em; text-shadow: 0 1px 2px rgba(0,0,0,0.5); }

.chat-bubble {
  min-width: 48px;
  padding: 14px 20px;
  display: flex;
  align-items: flex-end;
  border: 1px solid rgba(255, 255, 255, 0.15);
  border-radius: 22px 22px 22px 6px;
  background: linear-gradient(135deg, rgba(38, 15, 66, 0.82), rgba(20, 6, 38, 0.88));
  box-shadow: 0 12px 34px rgba(0, 0, 0, 0.25), inset 0 1px 1px rgba(255, 255, 255, 0.18);
  backdrop-filter: blur(16px);
  transition: transform 0.25s ease, box-shadow 0.25s ease;
}
.chat-bubble:hover {
  transform: translateY(-2px);
  box-shadow: 0 16px 40px rgba(0, 0, 0, 0.3), inset 0 1px 1px rgba(255, 255, 255, 0.2);
}

.chat-message.user .chat-bubble {
  border-color: rgba(255, 170, 130, 0.35);
  border-radius: 22px 22px 6px 22px;
  background: linear-gradient(135deg, rgba(240, 85, 115, 0.82), rgba(190, 55, 105, 0.88));
  box-shadow: 0 12px 34px rgba(240, 85, 115, 0.2), inset 0 1px 1px rgba(255, 255, 255, 0.2);
}

.chat-bubble p {
  color: rgba(255,250,247,.95);
  font-family: var(--font-soft);
  font-size: 15px;
  line-height: 1.65;
  overflow-wrap: anywhere;
  white-space: pre-wrap;
}
.chat-bubble img { max-width: 240px; max-height: 220px; margin: 0 0 10px; object-fit: cover; border-radius: 12px; box-shadow: 0 4px 12px rgba(0,0,0,0.2); }
.chat-bubble:has(img) { display: grid; }
.chat-bubble .type-caret { width: 5px; height: 14px; margin: 0 0 3px 5px; }
.chat-message--typing .chat-bubble { min-width: 64px; min-height: 44px; align-items: center; justify-content: center; }

.chat-console-footer {
  padding: 16px clamp(20px, 6vw, 96px);
  display: grid;
  gap: 12px;
  border-top: 1px solid rgba(255, 255, 255, 0.1);
  background: linear-gradient(180deg, rgba(12, 4, 30, 0), rgba(12, 4, 30, 0.8) 20%, rgba(12, 4, 30, 0.95) 100%);
  backdrop-filter: blur(12px);
}

.speaker-name {
  position: absolute;
  top: -17px;
  left: 24px;
  min-width: 116px;
  height: 34px;
  padding: 0 16px;
  display: flex;
  align-items: center;
  gap: 8px;
  border: 1px solid rgba(246,196,119,.28);
  border-radius: 10px 10px 3px 3px;
  background: linear-gradient(135deg, rgba(113,37,98,.95), rgba(52,18,72,.96));
  color: #fff5ec;
  font-family: var(--font-soft);
  font-size: 13px;
  font-weight: 800;
  box-shadow: 0 8px 20px rgba(4,1,14,.28);
}

.speaker-name span { color: #f6cb8a; font-size: 10px; }

.dialogue-copy {
  min-height: 58px;
  padding: 7px 2px 11px;
  display: flex;
  align-items: flex-start;
  cursor: pointer;
}

.dialogue-copy p {
  color: rgba(255,250,247,.94);
  font-family: var(--font-soft);
  font-size: clamp(14px, 1.08vw, 17px);
  line-height: 1.72;
  white-space: pre-wrap;
}

.type-caret {
  width: 7px;
  height: 15px;
  margin: 8px 0 0 4px;
  flex: 0 0 auto;
  background: #f6cb8a;
  animation: caretBlink .8s steps(1) infinite;
}

.story-link {
  position: relative;
  width: 100%;
  min-width: 0;
  padding: 8px 11px;
  display: grid;
  grid-template-columns: 1fr auto;
  gap: 1px 12px;
  border: 1px solid rgba(246,196,119,.24);
  border-radius: 11px;
  background: rgba(246,196,119,.07);
  text-align: left;
}
.story-link span { color: rgba(255,255,255,.38); font-size: 8px; font-weight: 800; }
.story-link strong { color: #f6d59d; font-size: 10px; }
.story-link i { grid-column: 2; grid-row: 1 / 3; align-self: center; color: #f6cb8a; font-style: normal; }

.choice-deck {
  display: flex;
  align-items: center;
  gap: 7px;
  margin: 0;
  overflow-x: auto;
  scrollbar-width: none;
}
.choice-deck::-webkit-scrollbar { display: none; }

.choice-guide {
  padding-right: 4px;
  color: rgba(255,255,255,.36);
  font-size: 9px;
  font-weight: 900;
  white-space: nowrap;
}

.choice-deck button {
  min-width: 150px;
  min-height: 38px;
  flex: 0 0 auto;
  padding: 0 11px;
  display: grid;
  grid-template-columns: auto 1fr auto;
  align-items: center;
  gap: 8px;
  border: 1px solid rgba(255,255,255,.1);
  border-radius: 11px;
  background: rgba(255,255,255,.045);
  color: rgba(255,247,242,.7);
  text-align: left;
  transition: transform .18s ease, border-color .18s ease, background .18s ease, color .18s ease;
}

.choice-deck button > span { color: rgba(246,196,119,.48); font-size: 8px; font-weight: 900; }
.choice-deck button strong { overflow: hidden; font-size: 10.5px; font-weight: 800; text-overflow: ellipsis; white-space: nowrap; }
.choice-deck button i { color: rgba(255,255,255,.28); font-size: 18px; font-style: normal; }
.choice-deck button:hover { transform: translateY(-2px); border-color: rgba(246,196,119,.35); background: rgba(246,196,119,.09); color: #fff7ee; }
.choice-deck button:hover i { color: #f6cb8a; }

.vn-composer {
  min-height: 52px;
  display: flex;
  align-items: center;
  gap: 10px;
}

.world-action {
  min-width: 44px;
  width: 44px;
  height: 44px;
  padding: 0;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 6px;
  border: 1px solid rgba(255, 255, 255, 0.15);
  border-radius: 50%;
  background: rgba(255, 255, 255, 0.08);
  color: rgba(255, 255, 255, 0.6);
  font-size: 16px;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
  transition: transform 0.25s cubic-bezier(0.34, 1.56, 0.64, 1), background 0.25s, border-color 0.25s, box-shadow 0.25s, color 0.25s;
}
.world-action span { color: #f6cb8a; font-size: 15px; }
.world-action b { display: none; }
.world-action:hover:not(:disabled) {
  transform: translateY(-2px) scale(1.05);
  border-color: rgba(246, 196, 119, 0.5);
  background: rgba(246, 196, 119, 0.15);
  color: #fff;
  box-shadow: 0 6px 16px rgba(246, 196, 119, 0.25);
}
.world-action.active {
  animation: sttPulse 1.2s ease-in-out infinite;
  background: rgba(248, 113, 113, 0.2);
  border-color: rgba(248, 113, 113, 0.6);
}
.world-action:disabled { opacity: 0.3; transform: scale(0.95); }

.composer-field {
  position: relative;
  min-width: 0;
  min-height: 48px;
  flex: 1;
  padding: 10px 52px 10px 18px;
  display: flex;
  align-items: center;
  border: 1px solid rgba(255, 255, 255, 0.15);
  border-radius: 24px;
  background: rgba(10, 3, 28, 0.6);
  box-shadow: inset 0 2px 4px rgba(0, 0, 0, 0.2), 0 8px 24px rgba(0, 0, 0, 0.15);
  transition: border-color 0.3s, box-shadow 0.3s, background 0.3s;
  backdrop-filter: blur(12px);
}

.composer-field:focus-within {
  border-color: rgba(246, 196, 119, 0.6);
  background: rgba(20, 8, 48, 0.7);
  box-shadow: inset 0 2px 4px rgba(0, 0, 0, 0.1), 0 0 0 4px rgba(246, 196, 119, 0.15), 0 8px 24px rgba(0, 0, 0, 0.2);
}

.composer-field .msg-input {
  min-height: 24px;
  max-height: 90px;
  padding: 2px 0;
  border: 0;
  border-radius: 0;
  background: transparent;
  color: #fff;
  font-family: var(--font-soft);
  font-size: 15px;
  line-height: 1.5;
}
.composer-field .msg-input:focus { border: 0; }
.composer-field .msg-input::placeholder { color: rgba(255, 255, 255, 0.35); font-weight: 300; }
.composer-field > span { position: absolute; right: 16px; bottom: 12px; color: rgba(255, 255, 255, 0.3); font-size: 10px; font-weight: 600; }

.vn-send {
  min-width: 48px;
  width: 48px;
  height: 48px;
  padding: 0;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  background: linear-gradient(135deg, #f06a5b, #f6946a);
  color: #fff;
  border: none;
  box-shadow: 0 6px 16px rgba(240, 106, 91, 0.35);
  transition: transform 0.25s cubic-bezier(0.34, 1.56, 0.64, 1), box-shadow 0.25s, opacity 0.25s;
}
.vn-send i { font-size: 18px; margin-left: 2px; }
.vn-send span { display: none; }
.vn-send:not(:disabled):hover {
  transform: translateY(-2px) scale(1.05);
  box-shadow: 0 10px 24px rgba(240, 106, 91, 0.5);
}
.vn-send:disabled {
  opacity: 0.3;
  transform: scale(0.95);
  box-shadow: none;
  cursor: not-allowed;
}
.composer-hint {
  margin-top: 5px;
  color: rgba(255,255,255,.24);
  font-size: 8px;
  text-align: center;
  letter-spacing: .03em;
}

.vn-image-preview {
  position: relative;
  right: auto;
  bottom: auto;
  width: 100%;
  padding: 8px 34px 8px 8px;
  display: flex;
  align-items: center;
  gap: 9px;
  border: 1px solid rgba(255,255,255,.13);
  border-radius: 14px;
  background: rgba(24,8,44,.82);
  box-shadow: 0 16px 38px rgba(4,1,14,.34);
  backdrop-filter: blur(16px);
}
.vn-image-preview img { width: 48px; height: 48px; object-fit: cover; border-radius: 9px; }
.vn-image-preview > div { display: grid; gap: 2px; }
.vn-image-preview strong { color: rgba(255,255,255,.76); font-size: 10px; }
.vn-image-preview div span { color: rgba(255,255,255,.34); font-size: 8px; }
.vn-image-preview button { position: absolute; right: 9px; color: rgba(255,255,255,.42); font-size: 11px; }

.story-log-backdrop {
  position: fixed !important;
  z-index: 120 !important;
  inset: 0;
  display: flex;
  justify-content: flex-end;
  background: rgba(4,1,14,.58);
  backdrop-filter: blur(7px);
}

.story-log {
  width: min(460px, 92vw);
  height: 100%;
  display: grid;
  grid-template-rows: auto minmax(0,1fr) auto;
  border-left: 1px solid rgba(255,218,202,.16);
  background:
    linear-gradient(160deg, rgba(53,18,72,.96), rgba(12,4,29,.98)),
    #14091f;
  box-shadow: -28px 0 80px rgba(3,1,12,.46);
}

.story-log > header {
  min-height: 82px;
  padding: 18px 20px 14px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  border-bottom: 1px solid rgba(255,255,255,.08);
}
.story-log header small { color: rgba(246,196,119,.56); font-size: 8px; font-weight: 900; letter-spacing: .16em; }
.story-log header h2 { margin-top: 2px; font-family: var(--font-display); font-size: 25px; font-weight: 400; }
.story-log header button { width: 34px; height: 34px; border: 1px solid rgba(255,255,255,.1); border-radius: 50%; color: rgba(255,255,255,.54); }

.story-log-list {
  padding: 20px;
  display: flex;
  flex-direction: column;
  gap: 16px;
  overflow-y: auto;
}

.story-log article { max-width: 88%; display: grid; gap: 5px; }
.story-log article.user { align-self: flex-end; justify-items: end; }
.story-log article.assistant { align-self: flex-start; }
.story-log article > span { padding-inline: 3px; color: rgba(255,255,255,.34); font-size: 9px; font-weight: 800; }
.story-log article > div { padding: 11px 13px; border: 1px solid rgba(255,255,255,.1); border-radius: 15px; background: rgba(255,255,255,.055); }
.story-log article.user > div { border-color: rgba(240,122,113,.22); border-bottom-right-radius: 4px; background: rgba(231,62,101,.18); }
.story-log article.assistant > div { border-top-left-radius: 4px; }
.story-log article p { color: rgba(255,250,247,.82); font-family: var(--font-soft); font-size: 12px; line-height: 1.65; white-space: pre-wrap; }
.story-log article img { max-width: 220px; max-height: 220px; margin-bottom: 7px; border-radius: 10px; }
.story-log > footer { padding: 14px 20px; border-top: 1px solid rgba(255,255,255,.07); color: rgba(255,255,255,.28); font-size: 9px; text-align: center; }
.story-log footer span { margin-right: 5px; color: #f4c983; }
.empty-log, .log-thinking { margin: auto; color: rgba(255,255,255,.36); font-family: var(--font-soft); font-size: 12px; text-align: center; }

.whisper-enter-active, .whisper-leave-active { transition: opacity .28s ease, transform .28s ease; }
.whisper-enter-from, .whisper-leave-to { opacity: 0; transform: translateY(8px); }
.log-drawer-enter-active, .log-drawer-leave-active { transition: opacity .25s ease; }
.log-drawer-enter-active .story-log, .log-drawer-leave-active .story-log { transition: transform .3s ease; }
.log-drawer-enter-from, .log-drawer-leave-to { opacity: 0; }
.log-drawer-enter-from .story-log, .log-drawer-leave-to .story-log { transform: translateX(100%); }

@keyframes moteFloat {
  0% { opacity: 0; transform: translateY(16px) scale(.6); }
  20%, 72% { opacity: .66; }
  100% { opacity: 0; transform: translate(12px, -40px) scale(1.1); }
}
@keyframes presenceBreathe { 0%,100% { transform: scale(.96); opacity: .45; } 50% { transform: scale(1.02); opacity: .78; } }
@keyframes thoughtBounce { 0%,100% { transform: translateY(0); opacity:.35; } 50% { transform: translateY(-4px); opacity:1; } }
@keyframes voiceWave { from { transform: scaleY(.45); opacity:.5; } to { transform: scaleY(1); opacity:1; } }
@keyframes characterTalk { from { transform: translateY(0) scale(1); } to { transform: translateY(-1px) scale(1.003); } }
@keyframes caretBlink { 0%,48% { opacity:1; } 49%,100% { opacity:0; } }

@media (max-width: 1100px) {
  .vn-shell { width: calc(100% - 24px); }
  .character-presence { right: auto; left: 0; width: clamp(215px, 25vw, 280px); }
  .presence-state { display: none; }
  .room-control b { display: none; }
  .room-control { width: 36px; padding: 0; justify-content: center; }
  .choice-deck { grid-template-columns: repeat(3,minmax(0,1fr)); }
  .choice-guide { display: none; }
  .user-whisper { right: 4%; width: 34%; }
}

@media (max-width: 1040px) {
  .character-presence {
    top: 68px;
    right: auto;
    left: 0;
    height: auto;
    min-height: 0;
    bottom: 98px;
  }
  .vn-dialogue {
    top: 70px;
    right: 0;
    bottom: 0;
    left: 0;
    width: auto;
    height: auto;
  }
  .chat-console-header,
  .chat-console-footer { padding-inline: clamp(16px, 5vw, 48px); }
  .chat-thread {
    padding-right: clamp(18px, 5vw, 48px);
    padding-left: clamp(205px, 27vw, 285px);
  }
  .chat-message { max-width: min(84%, 680px); }
}

@media (max-width: 760px) {
  .chat-page { min-height: calc(100dvh - var(--bt-header-h, 88px)); }
  .vn-shell { width: calc(100% - 14px); min-height: 780px; padding: 7px 0 10px; }
  .mind-room { min-height: 770px; border-radius: 20px; }
  .room-header { min-height: 56px; padding: 9px 10px 8px 13px; }
  .room-symbol { width: 31px; height: 31px; }
  .room-plaque small { display: none; }
  .room-plaque strong { font-size: 12px; }
  .room-controls { gap: 4px; }
  .room-control { width: 32px; min-height: 32px; }
  .story-lights { display: none; }
  .character-presence {
    top: 58px;
    right: auto;
    bottom: auto;
    left: 0;
    width: min(42vw, 185px);
    height: 164px;
    min-height: 0;
    opacity: .9;
  }
  .presence-ring { width: min(68vw, 280px); }
  .vn-character {
    top: 8px;
    right: auto;
    bottom: 8px;
    left: 8px;
    width: min(36vw, 160px);
    max-width: none;
    height: auto;
  }
  .character-presence::after { top: 10px; bottom: 16px; left: 7px; width: min(36vw, 160px); }
  .character-hud { right: auto; bottom: 6px; left: 11px; min-width: 88px; padding: 4px 8px 4px 6px; }
  .character-hud b { font-size: 8px; }
  .character-hud small { font-size: 7px; }
  .character-state { display: none; }
  .user-whisper { display: none; }
  .curtain { width: 27%; }
  .window-glow { width: 80%; right: -16%; height: 52%; }
  .vn-dialogue { top: 56px; left: 0; right: 0; bottom: 0; width: auto; height: auto; padding: 0; border-radius: 0; }
  .chat-console-header { min-height: 52px; padding: 8px 11px; }
  .chat-peer-avatar { width: 32px; height: 32px; }
  .chat-thread { padding: 102px 10px 14px; gap: 10px; }
  .chat-message { max-width: 88%; }
  .chat-bubble { padding: 9px 11px; }
  .chat-bubble p { font-size: 11.5px; }
  .chat-console-footer { padding: 8px; gap: 6px; }
  .speaker-name { left: 14px; top: -15px; height: 31px; min-width: 100px; padding: 0 13px; font-size: 11px; }
  .dialogue-copy { min-height: 58px; padding-top: 3px; }
  .dialogue-copy p { font-size: 13px; line-height: 1.62; }
  .story-link { position: relative; top: auto; right: auto; width: 100%; margin: 0 0 8px; }
  .choice-deck { gap: 5px; margin: 0; }
  .choice-deck button { min-width: 142px; }
  .choice-deck button { min-height: 37px; }
  .choice-deck button strong { font-size: 10px; }
  .vn-composer { gap: 5px; }
  .world-action { min-width: 40px; width: 40px; height: 43px; padding: 0; }
  .world-action b { display: none; }
  .composer-field { min-height: 45px; padding-left: 11px; padding-right: 34px; }
  .composer-field .msg-input { font-size: 12px; }
  .vn-send { min-width: 45px; width: 45px; height: 43px; padding: 0; }
  .vn-send span { display: none; }
  .composer-hint { display: none; }
  .vn-image-preview { right: auto; left: auto; width: 100%; }
  .secret-banner { font-size: 10px; padding: 7px 10px; }
  .secret-banner span { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
  .secret-exit-btn { padding: 4px 8px; }
}

@media (max-height: 720px) and (min-width: 1041px) {
  .vn-shell { padding-block: 7px 10px; }
  .room-header { min-height: 56px; padding-block: 9px; }
  .character-presence { top: 64px; right: auto; bottom: 96px; left: 0; height: auto; min-height: 0; }
  .vn-character { top: 18px; right: auto; bottom: 18px; left: 20px; width: clamp(185px, 16vw, 250px); height: auto; }
  .vn-dialogue { top: 56px; right: 0; bottom: 0; left: 0; width: auto; padding: 0; }
  .dialogue-copy { min-height: 48px; }
  .choice-deck button { min-height: 37px; }
  .vn-composer { min-height: 46px; }
}

@media (prefers-reduced-motion: reduce) {
  .light-mote,
  .presence-ring,
  .presence-ring::before,
  .presence-ring::after,
  .character-presence.speaking .vn-character img,
  .thought-dots i,
  .voice-wave i { animation: none !important; }
}


</style>

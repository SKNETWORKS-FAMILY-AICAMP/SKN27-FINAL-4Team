<template>
  <div class="chat-page" :class="{ 'is-secret': isSecret }" :style="charThemeVars"
       @dragover.prevent="onDragOver" @dragleave="onDragLeave" @drop.prevent="onDropImage">

    <!-- 📷 이미지 드래그&드롭 오버레이 -->
    <div v-if="isDragging" class="drop-overlay">
      <div class="drop-overlay-inner">📷 여기에 사진을 놓으면 첨부돼요</div>
    </div>

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

    <!-- 배경 무드: 어둠 그라데이션 + 떠오르는 빛 입자 (프로토타입 이식) -->
    <div class="bg-grade"></div>
    <div class="mote" style="left:16%; bottom:120px; width:9px; height:9px; animation-duration:12s;"></div>
    <div class="mote" style="left:64%; bottom:90px; width:11px; height:11px; animation-duration:15s; animation-delay:4s;"></div>
    <div class="mote" style="left:86%; bottom:150px; width:8px; height:8px; animation-duration:13s; animation-delay:2s;"></div>

    <!-- ═════ 마음방 A-레이아웃 (클로드 디자인 프로토타입 이식, 2026-07-20) ═════
         1순위 캐릭터(상단 중앙, 스크롤 시 접힘) → 2순위 대화 → 3순위 입력.
         기능 배선(기억 API·표정 스왑·TTS·시크릿·칩 펼침)은 전부 기존 것 유지. -->
    <div class="mind-header" :class="{ 'is-collapsed': isCollapsed }">
      <button v-if="!isSecret" class="secret-enter" @click="toggleSecret" aria-label="시크릿챗 열기">🔒 시크릿챗</button>

      <!-- 펼침: 큰 캐릭터 + 기억 별자리 칩 -->
      <template v-if="!isCollapsed">
        <div class="room-label">{{ timeGreeting }} · {{ displayCharacter.name }}의 마음방</div>
        <div class="hero-wrap" @click="pokeCharacter" title="쓰다듬기">
          <div class="hero-react" :style="reactStyle" :key="'r' + animKey">
            <div class="hero-circle">
              <img :src="displayCharacterImage"
                   :alt="`${displayCharacter.name} ${displayExpressionLabel}`"
                   :class="displayAnimationClass" />
            </div>
          </div>
          <div v-if="floatSymbol" class="float-symbol" :key="'f' + animKey">{{ floatSymbol }}</div>
        </div>
        <div class="char-name">{{ displayCharacter.name }}</div>
        <div class="char-status" :class="{ busy: isTyping || isSpeaking }">
          <span class="status-dot"></span>{{ charStatus }}
        </div>

        <template v-if="!isSecret">
          <div v-if="memoryPanelHasData" class="mem-chip-row">
            <span class="mem-chip-title">✦ {{ displayCharacter.name }}의 기억 별자리</span>
            <span v-for="c in memChips" :key="c.key" class="mem-chip" :class="{ glow: c.glow }">
              <span class="chip-star" :style="{ color: c.color, textShadow: '0 0 6px ' + c.color }">{{ c.star }}</span>
              {{ c.label }}
            </span>
            <span class="mem-more" role="button" aria-label="기억 전체 보기"
                  @click="memoryOpen = !memoryOpen">{{ memoryOpen ? '접기 ▴' : '더보기 ▾' }}</span>
          </div>
          <div class="mem-notice">대화 속 이야기가 자동으로 기억돼요 · '잊어줘'라고 말하면 지워져요</div>
        </template>
        <div v-else class="secret-note">🌙 비저장 모드 — 이 방의 이야기는 종료와 함께 흔적 없이 사라져요</div>
      </template>

      <!-- 접힘: 대화가 쌓이면 컴팩트 바 (클릭하면 다시 펼침) -->
      <div v-else class="collapsed-bar" @click="expandHeader" role="button" aria-label="캐릭터 영역 펼치기">
        <div class="hero-circle sm" :style="reactStyle">
          <img :src="displayCharacterImage" :alt="displayCharacter.name" />
        </div>
        <div class="cb-meta">
          <div class="cb-name">{{ displayCharacter.name }}</div>
          <div class="char-status" :class="{ busy: isTyping || isSpeaking }">
            <span class="status-dot"></span>{{ charStatus }}
          </div>
        </div>
        <div class="cb-right">
          <span v-if="!isSecret" class="mem-more" role="button" aria-label="기억 전체 보기"
                @click.stop="memoryOpen = !memoryOpen">✦ 기억 별자리</span>
          <span class="cb-expand">펼치기 ▾</span>
        </div>
      </div>

      <!-- 기억 영수증 토스트 — "'발표'를 기억했어요 / 잊었어요" -->
      <Transition name="toastfade">
        <div v-if="memToast" class="mem-toast">✦ {{ memToast }}</div>
      </Transition>
    </div>

    <!-- ===== 대화 스레드 (중앙 정렬 컬럼) ===== -->
    <section class="chat-thread" ref="threadRef" @scroll="onThreadScroll">
      <div class="thread-col">
        <div
          v-for="msg in messages"
          :key="msg.id ?? msg._tempId"
          class="bubble-wrap"
          :class="msg.role"
        >
          <!-- 감정 라벨(슬픔 모드 등)은 화면에 표시하지 않음 — 친구 컨셉 (분석은 뒤에서만) -->
          <div class="bubble-row">
            <img v-if="msg.role === 'assistant'" :src="displayCharacterImage" class="mini-avatar" alt="" />
            <div class="bubble" :class="msg.role === 'user' ? 'bubble-user' : 'bubble-char'">
              <img v-if="msg.image" :src="msg.image" class="bubble-img" alt="첨부 이미지" />
              <span v-if="msg.content" class="bubble-text">{{ (msg.displayed !== undefined ? msg.displayed : msg.content) || '…' }}</span>
            </div>
          </div>
          <div v-if="ttsEnabled && msg.role === 'assistant' && msg.displayed !== undefined && msg.displayed !== msg.content"
               class="speak-hint">
            <span class="eq"><i></i><i></i><i></i></span> 말하는 중
          </div>
          <!-- 기억 영수증 라벨 — 이 답변 직후 새로 기억된 것 (프로토타입 memLabel) -->
          <div v-if="msg.memLabel" class="mem-label">✦ '{{ msg.memLabel }}' 기억함</div>
          <!-- 대화 맥락 바로가기 칩 — 사용자가 관련 얘기를 꺼냈을 때만 (2026-07-12) -->
          <button v-if="msg.suggestPage && msg.displayed === msg.content" class="suggest-chip"
                  @click="router.push(msg.suggestPage === 'report' ? '/report' : '/mypage')">
            {{ msg.suggestLabel }}
          </button>

        </div>

        <div v-if="isTyping" class="typing-indicator">
          <span></span><span></span><span></span>
        </div>
      </div>
    </section>

    <!-- ===== 기억 별자리 팝오버 (더보기 — 카드형 상세, 정보량 전부 유지) ===== -->
    <div v-if="memoryOpen && !isSecret" class="mem-overlay" @click="memoryOpen = false"></div>
    <div v-if="memoryOpen && !isSecret" class="mem-popover">
      <div class="mem-pop-head">
        <span class="mp-title">✦ {{ displayCharacter.name }}의 기억 별자리</span>
        <button class="mem-pop-close" @click="memoryOpen = false" aria-label="닫기">✕</button>
      </div>
      <div v-if="memoryPanelData.upcoming.length" class="mp-sec">
        <div class="mp-label">다가오는 일</div>
        <div v-for="u in memoryPanelData.upcoming" :key="'u' + u.name" class="mp-item">
          <span class="chip-star" style="color:#FCD34D; text-shadow:0 0 8px #FCD34D;">✦</span>
          <span class="mp-text">{{ u.name }}</span>
          <span class="mp-dday" :class="{ soon: u.dday <= 2 }">{{ u.dday === 0 ? '오늘' : 'D-' + u.dday }}</span>
        </div>
      </div>
      <div v-if="memoryPanelData.people.length" class="mp-sec">
        <div class="mp-label">소중한 사람</div>
        <div v-for="p in memoryPanelData.people" :key="'p' + p.name" class="mp-item">
          <span class="chip-star" style="color:#7dd3fc; text-shadow:0 0 8px #7dd3fc;">✦</span>
          <span class="mp-text">{{ p.name }}</span>
          <span v-if="p.relation" class="mp-sub">· {{ p.relation }}</span>
        </div>
      </div>
      <div v-if="memoryPanelData.prefs.length" class="mp-sec">
        <div class="mp-label">요즘 좋아하는 것</div>
        <div v-for="t in memoryPanelData.prefs" :key="'t' + t.topic" class="mp-item">
          <span class="chip-star" style="color:#f9a8d4; text-shadow:0 0 8px #f9a8d4;">{{ t.polarity === '오' ? '💧' : '♥' }}</span>
          <span class="mp-text">{{ t.topic }}</span>
        </div>
      </div>
      <div v-if="memoryPanelData.recent.length" class="mp-sec">
        <div class="mp-label">최근 이야기</div>
        <div v-for="n in memoryPanelData.recent" :key="'r' + n" class="mp-item mp-dim">
          <span class="mp-text">{{ n }}</span>
        </div>
      </div>
      <div class="mp-note">대화 속 이야기가 자동으로 기억돼요 · "잊어줘"라고 말하면 지워져요</div>
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
        <!-- + 메뉴 (프로토타입): 사진·음성입력·음성켜기를 한 버튼에 -->
        <div class="plus-wrap">
          <button class="attach-btn plus-btn" :class="{ 'stt-recording': isRecording }"
                  @click="plusOpen = !plusOpen" aria-label="첨부와 음성 메뉴">＋</button>
          <div v-if="plusOpen" class="plus-overlay" @click="plusOpen = false"></div>
          <div v-if="plusOpen" class="plus-menu">
            <div class="plus-item" :class="{ disabled: isTyping }"
                 @click="!isTyping && (fileInputRef?.click(), plusOpen = false)">
              <span class="pi-ico">🖼️</span><span class="pi-label">파일 또는 사진 추가</span>
            </div>
            <div v-if="sttSupported" class="plus-item" :class="{ disabled: isTyping }"
                 @click="!isTyping && (toggleStt(), plusOpen = false)">
              <span class="pi-ico">🎤</span><span class="pi-label">{{ isRecording ? '음성 입력 중지' : '음성으로 입력' }}</span>
              <span v-if="isRecording" class="pi-state rec">● 녹음 중</span>
            </div>
            <div class="plus-divider"></div>
            <div class="plus-item" @click="toggleTtsPref()">
              <span class="pi-ico">{{ ttsEnabled ? '🔊' : '🔇' }}</span>
              <span class="pi-label">음성 {{ ttsEnabled ? '끄기' : '켜기' }}</span>
              <span class="pi-state">{{ ttsEnabled ? '켜짐' : '꺼짐' }}</span>
            </div>
          </div>
        </div>
        <textarea
          ref="inputRef"
          v-model="inputText"
          class="msg-input"
          :placeholder="isSecret ? '여기서 한 얘기는 흔적 없이 사라져요' : '오늘 어땠어? 무슨 얘기든 괜찮아'"
          maxlength="300"
          rows="1"
          @keydown.enter.exact.prevent="sendMessage"
          @input="autoResize"
        />
        <span class="char-count">{{ inputText.length }}/300</span>
        <button class="send-btn" :disabled="(!inputText.trim() && !attachedImage) || isTyping"
                @click="sendMessage" aria-label="메시지 전송">
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

// ── 기억 패널 (UI #3, 2026-07-20) — 그래프 기억을 좌측에 실시간 표시 ──
const memoryPanelData = ref({ upcoming: [], prefs: [], people: [], recent: [] })
const memoryPanelHasData = computed(() =>
  memoryPanelData.value.upcoming.length || memoryPanelData.value.prefs.length ||
  memoryPanelData.value.people.length || memoryPanelData.value.recent.length)
async function refreshMemoryPanel() {
  if (isSecret.value) return   // 시크릿 = 무저장 — 패널도 침묵
  try {
    const next = await chatApi.memoryPanel()
    _diffToast(memoryPanelData.value, next)   // 기억 영수증 (추가/삭제 알림)
    memoryPanelData.value = next
    stickBottom()   // 칩 로드로 헤더가 커지면 스레드가 줄어듦 — 바닥 재고정
  } catch { /* 패널은 부가 기능 — 실패해도 대화 흐름 무영향 */ }
}

// 캐릭터 쓰다듬기 (UI #60) — 클릭하면 폴짝 (애착 소품, 기능 무관)
const isPoked = ref(false)
function pokeCharacter() {
  if (isPoked.value) return
  isPoked.value = true
  reactTo('surprise')   // A-레이아웃: 쓰다듬으면 폴짝+❕ (프로토타입 poke)
  setTimeout(() => { isPoked.value = false }, 600)
}

// ── 마음방 리디자인 (2026-07-20) — 캐릭터 색 테마 · 방 라벨 · 상태 뱃지 ──
// 캐릭터마다 말풍선·글로우 색이 달라진다 (까미 보라 / 포리 주황 / 토토 청록 / 여울 분홍)
const CHAR_THEME = {
  kkami: { accent: '#a78bfa', bubble: 'rgba(64,40,110,0.78)' },
  pori:  { accent: '#ffab6b', bubble: 'rgba(120,62,26,0.72)' },
  toto:  { accent: '#5eead4', bubble: 'rgba(16,84,74,0.72)' },
  yeoul: { accent: '#f9a8d4', bubble: 'rgba(112,44,74,0.72)' },
}
const charThemeVars = computed(() => {
  const t = CHAR_THEME[displayCharacterId.value] || CHAR_THEME.kkami
  return { '--char-accent': t.accent, '--char-bubble': t.bubble }
})
// 시간대 인사 — 방문할 때마다 다른 방 (팀원 시안의 '느긋한 오후' 아이디어)
const timeGreeting = computed(() => {
  const h = new Date().getHours()
  if (h < 6) return '고요한 새벽'
  if (h < 11) return '맑은 아침'
  if (h < 17) return '느긋한 오후'
  if (h < 21) return '노을 지는 저녁'
  return '포근한 밤'
})
// 캐릭터 상태 뱃지 — 생각 중(응답 대기) / 말하는 중(타이핑 연출) / 듣고 있어요
const isSpeaking = computed(() => {
  const last = messages.value[messages.value.length - 1]
  return !!(last && last.role === 'assistant'
            && last.displayed !== undefined && last.displayed !== last.content)
})
const charStatus = computed(() =>
  isTyping.value ? '생각을 고르는 중…' : (isSpeaking.value ? '말하는 중' : '네 이야기를 듣고 있어'))

// ── A-레이아웃: 접힘 헤더 (프로토타입 이식 — 스크롤 40px↑ 접힘, 12px↓ 펼침) ──
const isCollapsed = ref(false)
const userExpanded = ref(false)
const nearBottom = ref(true)   // 사용자가 위로 올려 읽는 중인지 추적 (바닥 고정 여부)
function onThreadScroll(e) {
  const el = e.target
  const st = el.scrollTop
  nearBottom.value = (el.scrollHeight - st - el.clientHeight) < 80
  if (!userExpanded.value && st > 40 && !isCollapsed.value) isCollapsed.value = true
  else if (st < 12 && isCollapsed.value) { isCollapsed.value = false; userExpanded.value = false }
}
function expandHeader() { isCollapsed.value = false; userExpanded.value = true }
// 바닥 고정 (2026-07-20 실측 수정): 기억 칩 로드·입력창 확장·헤더 접힘 등으로
// 주변 높이가 변하면 스레드가 줄어도 스크롤이 보정 안 돼 마지막 메시지가
// 입력바에 깔렸다 → 높이가 변하는 모든 지점에서, 바닥 근처였다면 다시 붙인다.
function stickBottom() { if (nearBottom.value) scrollToBottom() }
watch(isCollapsed, () => stickBottom())

// ── 감정 리액션 (프로토타입 이식) — 봇 답변·쓰다듬기마다 캐릭터가 감정대로 움직인다 ──
const EMO_FX = {
  normal:   { r: 'reactCalm', s: '',   c: '#a78bfa' },
  joy:      { r: 'reactJoy',  s: '✨', c: '#FCD34D' },
  sadness:  { r: 'reactSad',  s: '🫂', c: '#93c5fd' },
  anger:    { r: 'reactPop',  s: '💢', c: '#f9a8d4' },   // 편들기 에너지 (봇이 화내는 게 아님)
  surprise: { r: 'reactPop',  s: '❕', c: '#f9a8d4' },
}
const animKey = ref(0)
const reactEmo = ref('normal')
function reactTo(emo) {
  reactEmo.value = EMO_FX[emo] ? emo : 'normal'
  animKey.value += 1
}
const reactStyle = computed(() => {
  const fx = EMO_FX[reactEmo.value] || EMO_FX.normal
  const suf = animKey.value % 2 ? 'B' : 'A'
  return {
    animation: `${fx.r}${suf} .95s ease both`,
    transformOrigin: 'center bottom',
    filter: `drop-shadow(0 14px 18px rgba(0,0,0,.32)) drop-shadow(0 0 26px ${fx.c}77)`,
  }
})
const floatSymbol = computed(() => (EMO_FX[reactEmo.value] || EMO_FX.normal).s)

// ── 기억 별자리 칩 (요약 3개) + 팝오버 열림 상태 ──
const memoryOpen = ref(false)
const plusOpen = ref(false)   // 입력바 + 메뉴 (프로토타입)
const glowName = ref(null)
const memChips = computed(() => {
  const d = memoryPanelData.value
  const chips = []
  for (const u of d.upcoming.slice(0, 2)) {
    chips.push({ key: 'u' + u.name, star: '✦', color: '#FCD34D',
                 label: `${u.name} ${u.dday === 0 ? '오늘' : 'D-' + u.dday}`, glow: u.name === glowName.value })
  }
  if (d.people[0]) chips.push({ key: 'p' + d.people[0].name, star: '✦', color: '#7dd3fc',
                                label: d.people[0].name, glow: d.people[0].name === glowName.value })
  if (d.prefs[0]) chips.push({ key: 't' + d.prefs[0].topic, star: '♥', color: '#f9a8d4',
                               label: d.prefs[0].topic, glow: d.prefs[0].topic === glowName.value })
  return chips.slice(0, 3)
})

// ── 기억 영수증 토스트 — 패널 전후 비교로 "기억했어요/잊었어요" 알림 ──
const memToast = ref(null)
let _toastT = null
const _flatten = (d) => [
  ...d.upcoming.map(u => u.name), ...d.people.map(p => p.name),
  ...d.prefs.map(t => t.topic), ...d.recent,
]
let _panelLoaded = false
function _diffToast(prev, next) {
  if (!_panelLoaded) { _panelLoaded = true; return }   // 첫 로드는 알림 없음
  const a = _flatten(prev); const b = _flatten(next)
  const added = b.find(x => !a.includes(x))
  const removed = a.find(x => !b.includes(x))
  let msg = null
  if (added) {
    msg = `${displayCharacter.value.name}가 '${added}'을(를) 기억했어요`
    glowName.value = added
    const last = [...messages.value].reverse().find(m => m.role === 'assistant')
    if (last) last.memLabel = added   // 말풍선 밑 "✦ '○○' 기억함" 라벨 (프로토타입)
  }
  else if (removed) { msg = `'${removed}' 이야기를 잊었어요`; glowName.value = null }
  if (msg) {
    memToast.value = msg
    clearTimeout(_toastT)
    _toastT = setTimeout(() => { memToast.value = null; glowName.value = null }, 3400)
  }
}
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
    const notes = [261.63, 329.63, 392.00, 523.25]
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
    const sess = await chatApi.startSession(character.value, isSecret.value, coords, route.query.checkinId || null, ttsEnabled.value)
    sessionId.value = sess.session_id
    coldStartDone.value = true
    userTurnCount.value = 0

    // 서버가 만든 친구 첫인사를 바로 표시 (+ 음성 자동 재생)
    const opener = sess.opener || OPENER_MSG[character.value]?.(isSecret.value) || '안녕! 뭐 하고 있었어?'
    pushAssistant(opener, { tts_task_id: sess.tts_task_id })
    refreshMemoryPanel()   // 기억 패널 (UI #3) — 진입 시 현재 기억 표시
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
      reactTo(res.emotion_label)   // 캐릭터 감정 리액션 (A-레이아웃)
      if (res.emotion_label === 'joy') {
        triggerJoyCelebration()
      }
    }
  } catch {
    messages.value.push({ _tempId: Date.now(), role: 'assistant', content: '잠시 연결이 끊겼어요. 다시 시도해 줄래요? 🙏' })
  } finally {
    isTyping.value = false
    await scrollToBottom()
    // 기억 패널 갱신 (UI #3) — 그래프 저장이 비동기라 잠깐 뒤에 (말한 게 기억으로 뜨는 순간)
    setTimeout(refreshMemoryPanel, 4000)
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

function autoResize(e) {
  e.target.style.height = 'auto'
  e.target.style.height = e.target.scrollHeight + 'px'
  stickBottom()   // 입력창이 여러 줄로 커지면 스레드가 줄어듦 — 바닥 재고정
}
async function scrollToBottom() { await nextTick(); if (threadRef.value) threadRef.value.scrollTop = threadRef.value.scrollHeight }

</script>

<style scoped>
.chat-page {
  display: flex;
  flex-direction: column;
  /* 입력창 잘림 수정 (UI #4, 2026-07-20): 헤더 실측 89px인데 54px로 가정 → 35px 잘림.
     실측값 + dvh(모바일 주소창 대응)로 교정 */
  height: calc(100dvh - 89px);
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
  flex: 0 0 340px;   /* 리디자인: 460→340 — 대화 공간 확대, 비율 개선 */
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
  font-size: 26px;
  color: #fff;
}

/* 상태 뱃지 — 듣고 있어요 / 생각하는 중 / 말하는 중 (살아있는 느낌의 핵심) */
.char-status {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  font-size: 12px;
  color: #86efac;
  background: rgba(34,84,61,0.35);
  border: 1px solid rgba(134,239,172,0.25);
  border-radius: 999px;
  padding: 3px 12px;
  margin-top: -12px;
}
.char-status .status-dot {
  width: 6px; height: 6px; border-radius: 50%;
  background: currentColor;
  animation: statusPulse 2.4s ease infinite;
}
.char-status.busy {
  color: #FFD9A8;
  background: rgba(120,72,20,0.35);
  border-color: rgba(255,217,168,0.3);
}
@keyframes statusPulse { 50% { opacity: 0.35; } }

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

/* ── 기억 패널 (UI #3) — 좌측 빈 공간에 '기억하는 것' 카드 ── */
.memory-panel {
  width: 100%;
  background: rgba(13,5,32,0.45);
  border: 1px solid rgba(192,132,252,0.22);
  border-radius: 16px;
  padding: 16px 18px;
  display: flex;
  flex-direction: column;
  gap: 14px;
}
.mp-title {
  font-size: 14.5px;
  font-weight: 700;
  color: #E9D5FF;
}
.mp-sec { display: flex; flex-direction: column; gap: 7px; }
.mp-label {
  font-size: 11.5px;
  font-weight: 600;
  letter-spacing: 0.04em;
  color: rgba(233,213,255,0.55);
}
.mp-item {
  display: flex;
  align-items: baseline;
  gap: 8px;
  font-size: 13.5px;
  color: rgba(255,255,255,0.9);
  line-height: 1.45;
}
.mp-item .mp-text { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.mp-dim .mp-text { color: rgba(255,255,255,0.6); }
.mp-dday {
  flex: 0 0 auto;
  font-size: 11px;
  font-weight: 700;
  color: #C4B5FD;                       /* 여유 있는 일정 = 차분한 보라 */
  background: rgba(167,139,250,0.14);
  border-radius: 7px;
  padding: 2px 7px;
}
.mp-dday.soon {                          /* D-2 이내 = 타오르는 주황 */
  color: #FFB347;
  background: rgba(255,179,71,0.16);
}
.mp-note {
  font-size: 10px;
  color: rgba(233,213,255,0.45);
  line-height: 1.55;
  border-top: 1px solid rgba(192,132,252,0.14);
  padding-top: 9px;
}
.mp-chips { display: flex; flex-wrap: wrap; gap: 6px; }
.mp-chip {
  font-size: 12.5px;
  color: rgba(255,255,255,0.88);
  background: rgba(255,255,255,0.08);
  border: 1px solid rgba(255,255,255,0.13);
  border-radius: 999px;
  padding: 4px 11px;
  white-space: nowrap;
}
.mp-chip small { color: rgba(255,255,255,0.5); }

/* ── 대화 스레드 ── */
.chat-thread {
  flex: 1;
  padding: 36px 56px;
  display: flex;
  flex-direction: column;
  gap: 22px;
  overflow-y: auto;
  /* 가독성 (UI #2): 배경 일러스트가 텍스트를 침식 → 오버레이 강화 (그림은 가장자리로 살아있음) */
  background: rgba(13,5,32,0.38);
}

.bubble-wrap {
  display: flex;
  flex-direction: column;
  max-width: 62%;   /* 폭 제한 (UI #15): 한 줄이 너무 길어 눈 피로 → 82%에서 축소 */
  animation: bubbleIn 0.28s ease both;   /* 등장 페이드 (UI #56) */
}

/* 방 라벨 — "노을 지는 저녁 · 까미의 마음방" (시간대별로 바뀜) */
.room-label {
  align-self: center;
  font-size: 12px;
  color: rgba(233,213,255,0.6);
  background: rgba(13,5,32,0.5);
  border: 1px solid rgba(192,132,252,0.18);
  border-radius: 999px;
  padding: 5px 16px;
  margin-bottom: 4px;
}

/* 말풍선 행 — 봇은 미니 아바타와 나란히 */
.bubble-row { display: flex; align-items: flex-end; gap: 9px; }
.mini-avatar {
  width: 34px; height: 34px;
  flex: 0 0 auto;
  border-radius: 11px;
  background: rgba(13,5,32,0.55);
  border: 1px solid var(--char-accent, #a78bfa);
  object-fit: contain;
  padding: 2px;
}

/* 말하는 중 표시 (UI #21) — 이퀄라이저 점 3개 */
.speak-hint {
  display: flex;
  align-items: center;
  gap: 7px;
  margin: 5px 0 0 43px;
  font-size: 11.5px;
  color: var(--char-accent, #a78bfa);
}
.speak-hint .eq { display: inline-flex; gap: 2px; align-items: flex-end; height: 11px; }
.speak-hint .eq i {
  width: 3px;
  background: currentColor;
  border-radius: 2px;
  animation: eqBar 0.9s ease-in-out infinite;
}
.speak-hint .eq i:nth-child(1) { height: 6px; }
.speak-hint .eq i:nth-child(2) { height: 11px; animation-delay: 0.15s; }
.speak-hint .eq i:nth-child(3) { height: 8px;  animation-delay: 0.3s; }
@keyframes eqBar { 50% { transform: scaleY(0.4); } }
@keyframes bubbleIn {
  from { opacity: 0; transform: translateY(8px); }
  to   { opacity: 1; transform: none; }
}

/* 캐릭터 쓰다듬기 반응 (UI #60) */
.char-face { cursor: pointer; }
.char-poke {
  animation: charPoke 0.55s ease;
}
@keyframes charPoke {
  0%   { transform: scale(1); }
  30%  { transform: scale(1.08) rotate(-3deg); }
  55%  { transform: scale(0.97) rotate(2deg); }
  100% { transform: scale(1); }
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
  border-radius: 18px;
  padding: 14px 20px;
  font-size: 16.5px;
  line-height: 1.65;
}
.bubble-user {
  /* 유저 = 코랄 + 오른쪽 꼬리 (말하는 방향 모서리만 각지게) */
  background: rgba(96,44,22,0.78);
  color: #FFE4D6;
  border: 1px solid rgba(255,138,101,0.5);
  border-radius: 18px 18px 5px 18px;
}
.bubble-char {
  /* 캐릭터 = 자기 색 + 왼쪽 꼬리 (까미 보라 / 포리 주황 / 토토 청록 / 여울 분홍) */
  background: var(--char-bubble, rgba(64,40,110,0.78));
  border: 1px solid var(--char-accent, #a78bfa);
  color: rgba(255,255,255,0.96);
  border-radius: 18px 18px 18px 5px;
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
  border: 1.5px solid rgba(255,255,255,0.15);
  border-radius: 999px;   /* 알약형 — 부드러운 인상 */
  padding: 14px 22px;
  font-size: 16.5px;
  font-family: inherit;
  color: #fff;
  resize: none;
  line-height: 1.5;
  max-height: 160px;
  overflow-y: auto;
  transition: border-color 0.2s, box-shadow 0.2s;
}
.msg-input::placeholder { color: rgba(255,255,255,0.35); }
.msg-input:focus {
  outline: none;
  border-color: var(--char-accent, #a78bfa);
  box-shadow: 0 0 14px color-mix(in srgb, var(--char-accent, #a78bfa) 25%, transparent);
}

.char-count {
  font-size: 10.5px;
  color: rgba(255,255,255,0.3);
  flex-shrink: 0;
  white-space: nowrap;
}

.send-btn {
  background: linear-gradient(135deg, #FF8A65, #FFB347);
  color: #1a0a00;
  border-radius: 999px;   /* 알약형 — 입력창과 짝 */
  padding: 14px 26px;
  font-size: 16px;
  font-weight: 700;
  flex-shrink: 0;
  transition: opacity 0.2s, transform 0.12s, box-shadow 0.2s;
}
.send-btn:not(:disabled):hover {
  opacity: 0.92;
  transform: translateY(-1px);
  box-shadow: 0 4px 16px rgba(255,138,101,0.35);
}
.send-btn:not(:disabled):active { transform: scale(0.96); }
.send-btn:disabled { opacity: 0.3; cursor: not-allowed; }

/* 📷 사진 첨부 (MVP) */
.file-hidden { display: none; }

.attach-btn {
  background: rgba(255,255,255,0.07);
  border: 1px solid rgba(255,255,255,0.15);
  border-radius: 50%;   /* 원형 아이콘 버튼 */
  width: 48px;
  height: 48px;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 0;
  font-size: 18px;
  line-height: 1;
  flex-shrink: 0;
  transition: background 0.2s, transform 0.12s;
}
.attach-btn:not(:disabled):hover { background: rgba(255,255,255,0.14); transform: translateY(-1px); }
.attach-btn:disabled { opacity: 0.3; cursor: not-allowed; }

/* ═════════ A-레이아웃 (클로드 디자인 프로토타입 이식, 2026-07-20) ═════════ */
/* 감정 리액션 키프레임 — A/B 교대로 같은 감정 연속에도 재발동 */
@keyframes breathe { 0%,100% { transform: scale(1); } 50% { transform: scale(1.03); } }
@keyframes reactCalmA { 0%{transform:translateY(0) scale(1);} 50%{transform:translateY(-4px) scale(1.02);} 100%{transform:none;} }
@keyframes reactCalmB { 0%{transform:translateY(0) scale(1);} 50%{transform:translateY(-4px) scale(1.02);} 100%{transform:none;} }
@keyframes reactJoyA { 0%{transform:translateY(0) scale(1);} 25%{transform:translateY(-18px) scale(1.07) rotate(-3deg);} 45%{transform:translateY(0) scale(1);} 65%{transform:translateY(-9px) rotate(2deg);} 100%{transform:none;} }
@keyframes reactJoyB { 0%{transform:translateY(0) scale(1);} 25%{transform:translateY(-18px) scale(1.07) rotate(3deg);} 45%{transform:translateY(0) scale(1);} 65%{transform:translateY(-9px) rotate(-2deg);} 100%{transform:none;} }
@keyframes reactSadA { 0%{transform:translateY(0) rotate(0);} 45%{transform:translateY(6px) rotate(-5deg) scale(.98);} 100%{transform:translateY(3px) rotate(-3deg);} }
@keyframes reactSadB { 0%{transform:translateY(0) rotate(0);} 45%{transform:translateY(6px) rotate(5deg) scale(.98);} 100%{transform:translateY(3px) rotate(3deg);} }
@keyframes reactPopA { 0%{transform:scale(1);} 20%{transform:scale(1.13) translateY(-8px);} 38%{transform:translateX(-5px);} 55%{transform:translateX(5px);} 72%{transform:translateX(-3px);} 100%{transform:none;} }
@keyframes reactPopB { 0%{transform:scale(1);} 20%{transform:scale(1.13) translateY(-8px);} 38%{transform:translateX(5px);} 55%{transform:translateX(-5px);} 72%{transform:translateX(3px);} 100%{transform:none;} }
@keyframes floatUp { 0%{opacity:0;transform:translate(-50%,0) scale(.5);} 18%{opacity:1;} 100%{opacity:0;transform:translate(-50%,-84px) scale(1.15);} }
@keyframes pillPulse { 0%,100%{box-shadow:0 0 0 0 rgba(255,179,71,0);} 50%{box-shadow:0 0 0 5px rgba(255,179,71,.28);} }
@keyframes toastIn { from{opacity:0;transform:translate(-50%,6px);} to{opacity:1;transform:translate(-50%,0);} }
@keyframes dotBounce { 0%,80%,100%{transform:translateY(0);opacity:.4;} 40%{transform:translateY(-6px);opacity:1;} }

/* 캐릭터 헤더 (1순위) — 접히면 컴팩트 바 */
.mind-header {
  position: relative;
  z-index: 2;
  flex: 0 0 auto;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 8px;
  padding: 20px 24px 10px;
  transition: padding 0.3s ease, background 0.3s ease;
  border-bottom: 1px solid transparent;
}
.mind-header.is-collapsed {
  padding: 10px 24px;
  border-bottom: 1px solid rgba(192,132,252,0.16);
  background: rgba(13,5,32,0.42);
  backdrop-filter: blur(16px);
}
.secret-enter {
  position: absolute;
  top: 14px; right: 20px;
  z-index: 5;
  display: inline-flex; align-items: center; gap: 6px;
  padding: 7px 14px;
  border-radius: 999px;
  background: rgba(20,9,31,0.5);
  border: 1px solid rgba(255,138,101,0.4);
  color: #FFD9C0;
  font-size: 12.5px;
  backdrop-filter: blur(6px);
}
.hero-wrap { position: relative; cursor: pointer; animation: breathe 5.5s ease-in-out infinite; }
.hero-circle {
  width: 172px; height: 172px;
  border-radius: 50%;
  overflow: hidden;
  position: relative;
  background: radial-gradient(circle at 50% 38%, #fef7ef, #f6e6d6);
  box-shadow: 0 0 0 7px rgba(255,240,225,0.14), inset 0 -16px 26px rgba(205,150,120,0.4);
}
.hero-circle img {
  position: absolute; left: -9%; top: -4%;
  width: 118%; height: 118%;
  object-fit: contain; object-position: 50% 45%;
}
.hero-circle.sm { width: 48px; height: 48px; flex: 0 0 auto; box-shadow: 0 0 0 3px rgba(255,240,225,0.16); }
.float-symbol {
  position: absolute; left: 50%; top: 4px;
  font-size: 30px; pointer-events: none; opacity: 0;
  animation: floatUp 1.5s ease forwards;
}
.mind-header .char-name { font-size: 24px; }
.mem-chip-row {
  display: flex; align-items: center; justify-content: center;
  gap: 7px; flex-wrap: wrap; max-width: 680px;
}
.mem-chip-title { color: rgba(255,225,200,0.55); font-size: 11.5px; white-space: nowrap; }
.mem-chip {
  display: inline-flex; align-items: center; gap: 5px;
  padding: 5px 12px; border-radius: 999px;
  white-space: nowrap; font-size: 12.5px;
  color: rgba(255,232,219,0.9);
  background: rgba(255,255,255,0.08);
  border: 1px solid rgba(255,255,255,0.15);
}
.mem-chip.glow {
  color: #fff;
  background: rgba(252,211,77,0.18);
  border-color: rgba(252,211,77,0.6);
  animation: pillPulse 1s ease infinite;
}
.chip-star { font-size: 12px; }
.mem-more {
  cursor: pointer;
  padding: 5px 13px; border-radius: 999px;
  background: rgba(20,9,31,0.4);
  border: 1px dashed rgba(192,132,252,0.4);
  color: rgba(233,213,255,0.85);
  font-size: 12px; white-space: nowrap;
  backdrop-filter: blur(6px);
}
.mem-notice { font-size: 10.5px; color: rgba(255,225,200,0.5); }
.collapsed-bar {
  display: flex; align-items: center; gap: 12px;
  width: 100%; max-width: 880px;
  cursor: pointer;
  padding: 2px 4px;
}
.cb-meta { display: flex; flex-direction: column; gap: 2px; min-width: 0; align-items: flex-start; }
.cb-name { color: #fff; font-size: 16px; font-weight: 700; line-height: 1.2; }
.collapsed-bar .char-status { margin-top: 0; }
.cb-right { margin-left: auto; display: flex; align-items: center; gap: 8px; }
.cb-expand { color: rgba(255,255,255,0.4); font-size: 12px; white-space: nowrap; }
.mem-toast {
  position: absolute; left: 50%; bottom: -32px; transform: translateX(-50%);
  z-index: 6; white-space: nowrap;
  padding: 7px 14px; border-radius: 999px;
  background: rgba(20,9,31,0.88);
  border: 1px solid rgba(255,179,71,0.5);
  color: #ffd9a8; font-size: 12.5px;
  animation: toastIn 0.3s ease;
  backdrop-filter: blur(6px);
}
.toastfade-leave-active { transition: opacity 0.4s; }
.toastfade-leave-to { opacity: 0; }

/* 대화 스레드 — 중앙 정렬 컬럼 (A-레이아웃 재정의) */
.chat-thread { align-items: center; padding: 14px 40px 20px; background: transparent; min-height: 0; }
/* (위/아래 밝기 경계 수정: 무드는 .bg-grade 그라데이션 하나만 담당 — 스레드 자체 배경 제거.
    말풍선이 크림 불투명이라 가독성은 배경 없이도 충분) */
.thread-col {
  width: 100%; max-width: 880px;
  display: flex; flex-direction: column; gap: 18px;
}
.bubble-wrap { max-width: 82%; }
.bubble-char {
  background: rgba(255,250,244,0.95);   /* 크림 불투명 — 가독성 최상 (프로토타입) */
  color: #41283f;
  border: 1px solid rgba(255,255,255,0.7);
  border-left: 5px solid var(--char-accent, #a78bfa);   /* 캐릭터 색 정체성 */
  border-radius: 20px 20px 20px 6px;
  box-shadow: 0 10px 28px rgba(80,30,60,0.24);
}
.bubble-user {
  background: linear-gradient(135deg, #FF8A65, #FFB347);
  color: #2a0f00;
  border: none;
  border-radius: 20px 20px 6px 20px;
  box-shadow: 0 12px 26px rgba(255,138,101,0.3);
}
.mini-avatar { border-radius: 12px; background: #efe9fb; box-shadow: 0 0 0 2px var(--char-accent, #a78bfa); border: none; }
.speak-hint { color: var(--char-accent, #a78bfa); }
.typing-indicator {
  align-self: flex-start;
  display: flex; align-items: center; gap: 5px;
  background: rgba(255,250,244,0.9);
  border: 1px solid rgba(255,255,255,0.6);
  border-radius: 14px; padding: 12px 16px;
}
.typing-indicator span {
  display: block; width: 7px; height: 7px; border-radius: 50%;
  background: var(--char-accent, #a78bfa);
  animation: dotBounce 1.2s infinite;
}
.typing-indicator span:nth-child(2) { animation-delay: 0.2s; }
.typing-indicator span:nth-child(3) { animation-delay: 0.4s; }

/* 기억 별자리 팝오버 */
.chat-page > .mem-overlay {
  position: absolute; inset: 0; z-index: 8;
  background: rgba(8,4,18,0.4);
  backdrop-filter: blur(2px);
}
.chat-page > .mem-popover {
  position: absolute; z-index: 9;
  left: 50%; top: 88px; transform: translateX(-50%);
  animation: none;   /* bubbleIn의 transform이 가운데 정렬(translateX)을 깨서 제거 */
  width: 392px; max-height: 72vh; overflow-y: auto;
  background: rgba(20,9,31,0.94);
  border: 1px solid rgba(192,132,252,0.3);
  border-radius: 18px;
  padding: 18px 18px 14px;
  box-shadow: 0 24px 60px rgba(0,0,0,0.5);
  display: flex; flex-direction: column; gap: 13px;
}
.mem-pop-head { display: flex; align-items: center; justify-content: space-between; }
.mem-popover .mp-title { font-size: 15px; font-weight: 700; color: #E9D5FF; }
.mem-pop-close { color: rgba(255,255,255,0.5); font-size: 17px; line-height: 1; background: none; border: none; cursor: pointer; }
.mp-sub { color: rgba(255,255,255,0.5); font-size: 12px; }
.mem-popover .mp-dday { margin-left: auto; }

/* 배경 무드 (프로토타입) — 어둠 그라데이션 + 빛 입자 */
.chat-page > .bg-grade {   /* ★.chat-page > :not(.chat-bg) 의 relative 덮어쓰기 이김 */
  position: absolute; inset: 0; z-index: 0; pointer-events: none;
  background: linear-gradient(180deg, rgba(13,5,32,0.16), rgba(20,8,48,0.32) 46%, rgba(13,5,32,0.6) 100%);
}
.chat-page > .mote {
  position: absolute; z-index: 1; pointer-events: none;
  border-radius: 50%;
  background: radial-gradient(circle, #ffe6c2, transparent 70%);
  animation: riseMote 12s linear infinite;
}
@keyframes riseMote {
  0% { transform: translateY(0) scale(1); opacity: 0; }
  12% { opacity: 0.8; }
  100% { transform: translateY(-520px) scale(0.4); opacity: 0; }
}

/* 감성 폰트 (프로토타입) — 이름은 바탕, 대화·라벨은 도담 */
.mind-header .char-name, .cb-name { font-family: 'Gowun Batang', serif; }
.bubble, .room-label, .char-status, .mem-chip, .mem-chip-title, .mem-notice, .secret-note { font-family: 'Gowun Dodum', sans-serif; }

/* 기억함 라벨 (말풍선 밑 영수증) */
.mem-label {
  margin: 6px 0 0 46px;
  display: inline-flex; align-self: flex-start; align-items: center; gap: 5px;
  padding: 4px 11px; border-radius: 999px;
  background: rgba(252,211,77,0.16);
  border: 1px solid rgba(252,211,77,0.4);
  color: #ffe08a; font-size: 11.5px; white-space: nowrap;
}

/* + 메뉴 (프로토타입 입력바) */
.plus-wrap { position: relative; flex: 0 0 auto; }
.plus-btn { font-size: 24px; color: #fff; }
.plus-btn.stt-recording { border-color: #f87171; box-shadow: 0 0 10px rgba(248,113,113,0.5); }
.plus-overlay { position: fixed; inset: 0; z-index: 10; }
.plus-menu {
  position: absolute; left: 0; bottom: calc(100% + 12px); z-index: 11;
  width: 250px;
  background: rgba(20,9,31,0.95);
  border: 1px solid rgba(192,132,252,0.28);
  border-radius: 16px; padding: 7px;
  box-shadow: 0 20px 50px rgba(0,0,0,0.5);
  backdrop-filter: blur(10px);
  animation: bubbleIn 0.16s ease;
}
.plus-item {
  cursor: pointer;
  display: flex; align-items: center; gap: 12px;
  padding: 11px 12px; border-radius: 11px;
  color: #f0e6f5; font-size: 14.5px;
}
.plus-item:hover { background: rgba(255,255,255,0.08); }
.plus-item.disabled { opacity: 0.4; cursor: not-allowed; }
.pi-ico { font-size: 17px; width: 20px; text-align: center; }
.pi-label { flex: 1; }
.pi-state { font-size: 11.5px; color: rgba(255,255,255,0.42); }
.pi-state.rec { color: #f87171; }
.plus-divider { height: 1px; background: rgba(192,132,252,0.16); margin: 4px 6px; }

/* ═════ 긴 텍스트 전수 방어 (2026-07-20 감사) — 어떤 길이가 와도 잘리거나 넘치지 않게 ═════ */
/* ① 기억 칩: 긴 이름은 말줄임 (칩 폭 상한 220px) — 전체 이름은 더보기 팝오버에서 */
.mem-chip {
  max-width: 220px;
  overflow: hidden;
  text-overflow: ellipsis;
}
.mem-chip .chip-star { flex: 0 0 auto; }
/* ② 팝오버 상세: 여기선 절대 안 자름 — 줄바꿈으로 전체 표시 (칩과 역할 분담) */
.mem-popover .mp-item { align-items: flex-start; }
.mem-popover .mp-text {
  white-space: normal;
  overflow: visible;
  text-overflow: clip;
  word-break: break-word;
  flex: 1;
  min-width: 0;
}
.mem-popover .mp-dday { margin-top: 1px; }
/* ③ 토스트·기억함 라벨: 화면 폭 초과 방지 + 말줄임 */
.mem-toast { max-width: min(86vw, 560px); overflow: hidden; text-overflow: ellipsis; }
.mem-label { max-width: 70%; overflow: hidden; text-overflow: ellipsis; }
/* ④ 말풍선: 공백 없는 긴 문자열(URL 등)도 강제 줄바꿈 */
.bubble { word-break: break-word; overflow-wrap: anywhere; min-width: 0; }
.bubble-row { min-width: 0; width: 100%; }
.bubble-row .bubble { min-width: 0; }
/* ⑤ 접힘 바: 이름·상태 긴 경우 말줄임 (우측 버튼 안 밀리게) */
.cb-meta { flex: 1; min-width: 0; }
.cb-name { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; max-width: 100%; }
.collapsed-bar .char-status { max-width: 100%; overflow: hidden; }
/* ⑥ 방 라벨·상태 뱃지: 좁은 화면에서 줄바꿈 허용 */
.room-label { white-space: normal; text-align: center; max-width: 90%; }
.char-status { max-width: 92%; }
/* ⑦ + 메뉴 항목: 긴 라벨 줄바꿈 */
.pi-label { word-break: keep-all; overflow-wrap: break-word; }

/* 낮은 노트북 (1366×768 이하) — 캐릭터 축소로 대화 공간 확보 */
@media (max-height: 800px) {
  .hero-circle { width: 128px; height: 128px; }
  .mind-header { padding-top: 12px; gap: 6px; }
  .mind-header .char-name { font-size: 20px; }
}

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



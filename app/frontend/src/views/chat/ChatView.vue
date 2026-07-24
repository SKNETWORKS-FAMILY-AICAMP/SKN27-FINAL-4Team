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
        <div class="room-label">{{ isSecret ? '밤하늘 아래 · 비밀 이야기' : timeGreeting }}</div>
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
          <!-- (기억함 라벨 제거 2026-07-20 — 저장은 조용히, 패널 고지·칩 반짝임으로 충분.
               삭제(잊어줘)만 토스트로 확인해준다) -->
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
  nearBottom.value = (el.scrollHeight - el.scrollTop - el.clientHeight) < 80
  // (접힘 동작 제거 2026-07-20 — 사용자 결정: 캐릭터·기억 별자리는 상시 고정,
  //  대화만 그 아래에서 스크롤. 낮은 화면은 @media가 캐릭터를 축소해 커버)
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
  // 저장은 조용히 (2026-07-20 결정) — 칩 반짝임만, 토스트·라벨 없음.
  // 삭제(잊어줘)만 토스트로 확인 (잊힐 권리의 영수증).
  if (added) {
    glowName.value = added
    clearTimeout(_toastT)
    _toastT = setTimeout(() => { glowName.value = null }, 3400)
    return
  }
  if (removed) { msg = `'${removed}' 이야기를 잊었어요`; glowName.value = null }
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

// 본문이 다 드러난 뒤 콜백 실행 — MBTI 질문을 '두 번째 말풍선'으로 띄울 때 쓴다 (2026-07-21).
// 바로 밀어넣으면 본문이 타이핑 중인데 질문이 먼저 떠서 순서가 어색하다.
function afterReveal(m, fn, maxWaitMs = 30000) {
  const started = Date.now()
  const timer = setInterval(() => {
    if (m.displayed === m.content || Date.now() - started > maxWaitMs) {
      clearInterval(timer)
      setTimeout(fn, 600)     // 살짝 뜸 들였다가 — 한 번 더 말 거는 느낌
    }
  }, 200)
}

function pushAssistant(text, extra = {}) {
  const m = { _tempId: Date.now(), role: 'assistant', content: text, ...extra }
  if (m.tts_task_id && ttsEnabled.value) {
    m.displayed = ''                    // 음성 시작까지 잠깐 '…' 표시
    messages.value.push(m)
    const target = messages.value[messages.value.length - 1]   // 반응형 프록시로 조작
    playTask(m.tts_task_id, {
      onStart: (d, alignment, audioEl) => {
        // 2026-07-23: 5초 폴백으로 이미 타이핑이 시작됐으면 재시작하지 않는다
        // (animateReveal을 다시 걸면 진행도가 0부터라 글자가 뒤로 감긴다). 음성만 합류.
        if (target._revealTimer || target.displayed === target.content) return
        animateReveal(target, d, alignment, audioEl)
      },
      onFail: () => {
        if (target._revealTimer || target.displayed === target.content) return
        animateReveal(target, null, null, null)   // 실패해도 즉시 덤프 대신 타이핑 (2026-07-12)
      },
    })
    // 2026-07-23: 음성이 글자를 인질로 잡던 구조 해체 — TTS가 5초 안에 시작 안 되면
    // 글자부터 타이핑한다 (팀원 체감 "답변이 안 나옴"의 주범: 최대 28초 '…' 대기).
    // 음성은 준비되는 대로 재생만 합류 (위 onStart 가드가 이중 타이핑을 막는다).
    setTimeout(() => {
      if (!target._revealTimer && target.displayed !== target.content) {
        animateReveal(target, null, null, null)
      }
    }, 5000)
    setTimeout(() => {                  // 최후 안전장치 (2026-07-23: `_revealTimer 없음` 조건 제거 —
      // 타이머가 살아있는 채 멈춘 케이스(오디오 스톨)에선 영영 안 풀리던 결함)
      if (target.displayed !== target.content) revealNow(target)
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
  // 2026-07-23: 끼어들기 정책 — 앞 말풍선이 아직 타이핑/재생 중이면 곱게 마무리.
  // (전엔 새 턴의 playTask가 stop()으로 앞 음성·폴링만 끊고 글자는 미완성으로
  //  방치되는 경로가 있었다 → "말하다 마는" 팀원 보고의 원인 중 하나. 스킵 버튼과 동일 동작.)
  const prevSpeaking = [...messages.value].reverse().find(x => x.role === 'assistant')
  if (prevSpeaking && prevSpeaking.displayed !== undefined
      && prevSpeaking.displayed !== prevSpeaking.content) revealNow(prevSpeaking)
  ttsStop()
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
    // MBTI 질문 — 본문 말풍선에 이어붙이지 않고 별도 버블로 (2026-07-21).
    // 백엔드가 mbti_probe로 따로 내려준다. TTS는 본문만 재생된다.
    if (res.mbti_probe?.text) {
      afterReveal(m, () => { pushAssistant(res.mbti_probe.text); scrollToBottom() })
    }
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

<style scoped src="./ChatView.css"></style>



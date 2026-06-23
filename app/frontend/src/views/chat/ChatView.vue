<template>
  <div class="chat-page" :class="{ 'is-secret': isSecret }">

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
      종료 시 마음 카드·리포트가 생성되지 않습니다.</span>
      <button class="secret-exit-btn" @click="showExitModal = true">✕ 시크릿챗 종료</button>
    </div>

    <!-- 시크릿챗 종료 확인 모달 -->
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

    <div class="chat-layout">
      <!-- ===== 왼쪽 패널: 캐릭터 영역 ===== -->
      <aside class="left-panel">
        <div class="char-face" :style="{ background: CHARACTER_META[character].bg, color: CHARACTER_META[character].color }">
          {{ CHARACTER_META[character].faces[currentEmotion] }}
        </div>
        <div class="char-name">{{ CHARACTER_META[character].name }}</div>
        <div class="char-faces">표정 4분기 : 응원 · 속상 · 화남 · 계획</div>

        <div class="opener-bubble">
          {{ openerText }}
          <small>{{ isSecret ? 'opener · 비저장 안내' : 'opener · 운세/날씨' }}</small>
        </div>

        <div class="rec-btns">
          <button class="rec-btn" @click="requestTea">🍵 힐링 차 추천</button>
          <button class="rec-btn" @click="requestBgm">🎵 BGM 추천</button>
        </div>

        <template v-if="!isSecret">
          <div class="intimacy-row">
            <span class="intimacy-label">♥ 친밀도</span>
            <div class="intimacy-bar">
              <div class="intimacy-fill" style="width:60%"></div>
            </div>
          </div>
          <div class="ctrl-btns">
            <button class="ctrl-btn" @click="toggleSecret">🔒 시크릿챗</button>
            <button class="ctrl-btn" @click="goCouncil">👥 이너 카운슬</button>
          </div>
        </template>

        <div v-else class="secret-note">
          🔒 비저장 모드 — 친밀도·메모리 적립 정지<br>(시크릿챗·이너 카운슬 비활성)
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

          <div v-if="msg._teaCard" class="tea-card">
            <strong>🍵 {{ msg._teaCard.name }}</strong>
            <div class="tea-desc">{{ msg._teaCard.desc }}</div>
          </div>

          <div v-else class="bubble" :class="msg.role === 'user' ? 'bubble-user' : 'bubble-char'">
            {{ msg.content }}
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
        <button class="icon-btn" title="음성 입력">🎤</button>
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
        <button class="icon-btn" title="계획 모드">📋 계획</button>
        <button class="send-btn" :disabled="!inputText.trim() || isTyping" @click="sendMessage">
          전송 ➤
        </button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, nextTick, onMounted } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { chatApi } from '../../api/chat.js'
import chatBg from '../../assets/chat-bg.png'

const router = useRouter()
const route  = useRoute()

const CHARACTER_META = {
  haeon: {
    name: '해온이', color: '#5EEAD4', bg: 'rgba(94,234,212,0.18)',
    faces: {
      default:   '◠‿◠',
      encourage: '✧◠‿◠✧',
      sad:       '(╥_╥)',
      angry:     '(；∀；)',
      plan:      '(•̀ᴗ•́)و',
    }
  },
  greung: {
    name: '그릉이', color: '#FCA5A5', bg: 'rgba(252,165,165,0.18)',
    faces: {
      default:   '◣_◢',
      encourage: '◣▽◢',
      sad:       '◣；◢',
      angry:     '◣益◢',
      plan:      '◣ω◢',
    }
  },
  dalkong: {
    name: '달콩이', color: '#C4B5FD', bg: 'rgba(196,181,253,0.18)',
    faces: {
      default:   '◕‿◕',
      encourage: '◕ᴗ◕✨',
      sad:       '◕︵◕',
      angry:     '◕皿◕',
      plan:      '◕‿↗',
    }
  },
}
const EMOTION_LABELS = {
  encourage: '✦ 응원 모드',
  sad:       '✦ 속상 모드',
  angry:     '✦ 화남 모드',
  plan:      '✦ 계획 모드',
}

const character      = ref(route.query.character || 'haeon')
const isSecret       = ref(route.query.secret === 'on')
const sessionId      = ref(null)
const showExitModal  = ref(false)
const messages       = ref([])
const inputText      = ref('')
const isTyping       = ref(false)
const suggestLoading = ref(false)
const suggestedQuestions = ref([])
const currentEmotion = ref('default')
const threadRef = ref(null)
const inputRef  = ref(null)

const openerText = computed(() =>
  isSecret.value ? '여긴 아무 기록도 안 남아. 편하게 다 털어놔도 돼.' : '오늘 어떤 하루였어?'
)

async function refreshSuggestions() {
  if (!sessionId.value || isSecret.value) return
  suggestLoading.value = true
  try {
    const result = await chatApi.suggestQuestions(sessionId.value)
    suggestedQuestions.value = result.questions ?? []
  } catch {
    suggestedQuestions.value = []
  } finally {
    suggestLoading.value = false
  }
}

onMounted(async () => {
  try {
    const sess = await chatApi.createSession(character.value, isSecret.value)
    sessionId.value = sess.id
    refreshSuggestions()
  } catch { /* 백엔드 미연결 시 무시 */ }
})

async function sendMessage() {
  const content = inputText.value.trim()
  if (!content || isTyping.value) return
  messages.value.push({ _tempId: Date.now(), role: 'user', content })
  inputText.value = ''
  isTyping.value = true
  await scrollToBottom()
  try {
    const reply = await chatApi.sendMessage(sessionId.value, content)
    messages.value.push(reply)
    if (reply.emotion_label) currentEmotion.value = reply.emotion_label
    refreshSuggestions()
  } catch {
    messages.value.push({ _tempId: Date.now(), role: 'assistant', content: '잠시 연결이 끊겼어요. 다시 시도해 줄래요? 🙏' })
  } finally {
    isTyping.value = false
    await scrollToBottom()
  }
}

async function requestTea() {
  isTyping.value = true
  await scrollToBottom()
  try {
    const tea = await chatApi.recommendTea(sessionId.value)
    messages.value.push({
      _tempId: Date.now(), role: 'assistant',
      content: `${tea.emoji ?? '🍵'} **${tea.name}**\n${tea.reason}\n효능: ${tea.effect}`,
      _teaCard: { name: tea.name, desc: tea.reason },
    })
  } catch {
    messages.value.push({ _tempId: Date.now(), role: 'assistant', content: '차 추천을 불러오지 못했어요.' })
  } finally { isTyping.value = false; await scrollToBottom() }
}

async function requestBgm() {
  isTyping.value = true
  await scrollToBottom()
  try {
    const bgm = await chatApi.recommendBgm(sessionId.value)
    messages.value.push({
      _tempId: Date.now(), role: 'assistant',
      content: `🎵 **${bgm.title}** — ${bgm.artist}\n${bgm.mood}`,
    })
  } catch {
    messages.value.push({ _tempId: Date.now(), role: 'assistant', content: 'BGM 추천을 불러오지 못했어요.' })
  } finally { isTyping.value = false; await scrollToBottom() }
}

async function toggleSecret() {
  isSecret.value = !isSecret.value
  messages.value = []
  try {
    const sess = await chatApi.createSession(character.value, isSecret.value)
    sessionId.value = sess.id
  } catch {}
  router.replace({ query: { character: character.value, secret: isSecret.value ? 'on' : undefined } })
}

async function confirmExitSecret() {
  showExitModal.value = false
  isSecret.value = false
  messages.value = []
  try {
    const sess = await chatApi.createSession(character.value, false)
    sessionId.value = sess.id
  } catch {}
  router.replace({ query: { character: character.value } })
}

function goCouncil() {
  router.push({ path: '/chat/council', query: { sessionId: sessionId.value } })
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
    rgba(13, 5, 32, 0.55) 0%,
    rgba(20, 8, 48, 0.70) 45%,
    rgba(13, 5, 32, 0.86) 100%);
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
.is-secret .rec-btn { color: #bcd2ff; }
.is-secret .rec-btn:hover { background: rgba(150,180,255,0.14); }
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

.rec-btns { display: flex; gap: 12px; width: 100%; }
.rec-btn {
  flex: 1;
  font-size: 15.5px;
  border: 1px solid rgba(255,255,255,0.14);
  border-radius: 14px;
  padding: 15px 8px;
  background: rgba(255,255,255,0.07);
  color: #FCD34D;
  transition: background 0.2s;
}
.rec-btn:hover { background: rgba(252,211,77,0.12); }

.intimacy-row {
  display: flex;
  align-items: center;
  gap: 8px;
  width: 100%;
  font-size: 14px;
  color: rgba(255,255,255,0.5);
}
.intimacy-bar {
  flex: 1;
  height: 6px;
  border-radius: 4px;
  background: rgba(255,255,255,0.12);
  position: relative;
  overflow: hidden;
}
.intimacy-fill {
  height: 100%;
  border-radius: 4px;
  background: linear-gradient(90deg, #f472b6, #fb7185);
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

.icon-btn {
  font-size: 22px;
  color: rgba(255,255,255,0.45);
  padding: 12px;
  border-radius: 14px;
  flex-shrink: 0;
  transition: background 0.2s;
}
.icon-btn:hover { background: rgba(255,255,255,0.1); color: rgba(255,255,255,0.8); }

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
</style>

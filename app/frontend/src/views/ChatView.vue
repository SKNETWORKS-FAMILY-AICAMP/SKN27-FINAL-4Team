<template>
  <div class="chat-page">

    <!-- 시크릿챗 경고 배너 (SCR-003-S ②) -->
    <div v-if="isSecret" class="secret-banner">
      🔒 <strong>시크릿챗</strong> — 이 대화와 분석은 <strong>저장되지 않으며</strong>,
      종료 시 마음 카드·리포트가 생성되지 않습니다.
    </div>

    <div class="chat-layout">
      <!-- ===== 왼쪽 패널: 캐릭터 영역 ===== -->
      <aside class="left-panel">
        <div class="char-face" :style="{ background: CHARACTER_META[character].bg, color: CHARACTER_META[character].color }">
          {{ CHARACTER_META[character].face }}
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
            <div class="tea-bgm">▶ 마음 달래는 BGM 들으러 가기</div>
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
      <span class="suggest-label">✦ 이런 얘기 어때요?</span>
      <button v-for="q in suggestedQuestions" :key="q" class="q-chip" @click="fillInput(q)">
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
import { chatApi } from '../api/chat.js'

const router = useRouter()
const route  = useRoute()

const CHARACTER_META = {
  haeon:   { name: '해온이', face: '◠‿◠', color: '#5EEAD4', bg: 'rgba(94,234,212,0.18)'  },
  greung:  { name: '그릉이', face: '◣_◢', color: '#FCA5A5', bg: 'rgba(252,165,165,0.18)' },
  dalkong: { name: '달콩이', face: '◕‿◕', color: '#C4B5FD', bg: 'rgba(196,181,253,0.18)' },
}
const EMOTION_LABELS = {
  encourage: '✦ 응원 모드',
  sad:       '✦ 속상 모드',
  angry:     '✦ 화남 모드',
  plan:      '✦ 계획 모드',
}

const character = ref(route.query.character || 'haeon')
const isSecret  = ref(route.query.secret === 'on')
const sessionId = ref(null)
const messages  = ref([])
const inputText = ref('')
const isTyping  = ref(false)
const threadRef = ref(null)
const inputRef  = ref(null)

const SUGGEST_NORMAL = ['오늘 회사에서 무슨 일 있었어?', '요즘 제일 힘든 게 뭐야?', '그냥 가볍게 수다 떨까?']
const SUGGEST_SECRET = ['털어놓고 싶은 비밀이 있어', '요즘 너무 지쳐', '그냥 들어줘']
const suggestedQuestions = computed(() => isSecret.value ? SUGGEST_SECRET : SUGGEST_NORMAL)
const openerText = computed(() =>
  isSecret.value ? '여긴 아무 기록도 안 남아. 편하게 다 털어놔도 돼.' : '오늘 서울 비 온대~ 우산 챙겼어?'
)

onMounted(async () => {
  try {
    const sess = await chatApi.createSession(character.value, isSecret.value)
    sessionId.value = sess.id
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
    const reply = await chatApi.sendMessage(sessionId.value, '힐링 차 추천해줘')
    messages.value.push({ ...reply, _teaCard: { name: '캐모마일 차', desc: '긴장 완화 · 수면 도움 · 카페인 없음' } })
  } finally { isTyping.value = false; await scrollToBottom() }
}

async function requestBgm() {
  isTyping.value = true
  await scrollToBottom()
  try {
    const reply = await chatApi.sendMessage(sessionId.value, 'BGM 추천해줘')
    messages.value.push(reply)
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
}

/* 시크릿챗 배너 */
.secret-banner {
  background: rgba(248, 113, 113, 0.15);
  border-bottom: 1px solid rgba(248,113,113,0.3);
  color: #FCA5A5;
  font-size: 13px;
  text-align: center;
  padding: 9px 16px;
  flex-shrink: 0;
}
.secret-banner strong { color: #fff; }

.chat-layout {
  display: flex;
  flex: 1;
  overflow: hidden;
}

/* ── 왼쪽 패널 (글래스모피즘) ── */
.left-panel {
  flex: 0 0 260px;
  border-right: 1px solid rgba(255,255,255,0.1);
  padding: 20px 16px;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 12px;
  overflow-y: auto;
  background: rgba(255,255,255,0.04);
  backdrop-filter: blur(10px);
}

.char-face {
  width: 110px;
  height: 110px;
  border-radius: 28px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 46px;
  border: 1px solid rgba(255,255,255,0.15);
  margin-top: 4px;
}

.char-name {
  font-weight: 700;
  font-size: 16px;
  color: #fff;
}

.char-faces {
  font-size: 11.5px;
  color: rgba(255,255,255,0.45);
  text-align: center;
}

.opener-bubble {
  background: rgba(255,255,255,0.07);
  border: 1px solid rgba(255,255,255,0.14);
  border-radius: 14px;
  padding: 10px 13px;
  font-size: 12.5px;
  color: #5EEAD4;
  text-align: center;
  width: 100%;
  line-height: 1.5;
}
.opener-bubble small {
  display: block;
  color: rgba(255,255,255,0.38);
  font-size: 10.5px;
  margin-top: 4px;
}

.rec-btns { display: flex; gap: 8px; width: 100%; }
.rec-btn {
  flex: 1;
  font-size: 12px;
  border: 1px solid rgba(255,255,255,0.14);
  border-radius: 10px;
  padding: 8px 4px;
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
  font-size: 12px;
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

.ctrl-btns { display: flex; gap: 8px; width: 100%; }
.ctrl-btn {
  flex: 1;
  font-size: 12px;
  border: 1px solid rgba(255,255,255,0.14);
  border-radius: 10px;
  padding: 8px 4px;
  background: rgba(255,255,255,0.07);
  color: rgba(255,255,255,0.75);
  transition: background 0.2s;
}
.ctrl-btn:hover { background: rgba(255,255,255,0.13); }

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
  padding: 20px 22px;
  display: flex;
  flex-direction: column;
  gap: 12px;
  overflow-y: auto;
  background: rgba(0,0,0,0.12);
}

.bubble-wrap {
  display: flex;
  flex-direction: column;
  max-width: 72%;
}
.bubble-wrap.user      { align-self: flex-end;   align-items: flex-end; }
.bubble-wrap.assistant { align-self: flex-start;  align-items: flex-start; }

.emotion-tag {
  font-size: 10.5px;
  background: rgba(94,234,212,0.18);
  color: #5EEAD4;
  border-radius: 6px;
  padding: 2px 8px;
  margin-bottom: 5px;
  display: inline-block;
}

.bubble {
  border-radius: 16px;
  padding: 10px 14px;
  font-size: 13.5px;
  line-height: 1.55;
}
.bubble-user {
  background: rgba(94,234,212,0.18);
  color: #A7F3D0;
  border: 1px solid rgba(94,234,212,0.25);
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
.tea-desc { font-size: 11px; color: rgba(255,255,255,0.5); margin: 4px 0 8px; }
.tea-bgm  { font-size: 12px; color: #93C5FD; cursor: pointer; }
.tea-bgm:hover { text-decoration: underline; }

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
  padding: 10px 20px;
  border-top: 1px solid rgba(255,255,255,0.08);
  background: rgba(0,0,0,0.15);
  backdrop-filter: blur(10px);
  flex-shrink: 0;
}
.suggest-label {
  font-size: 11px;
  color: rgba(255,255,255,0.4);
  font-weight: 600;
  white-space: nowrap;
}
.q-chip {
  font-size: 11.5px;
  border: 1px solid rgba(94,234,212,0.35);
  border-radius: 999px;
  padding: 5px 13px;
  color: #5EEAD4;
  background: rgba(94,234,212,0.08);
  transition: background 0.2s;
}
.q-chip:hover { background: rgba(94,234,212,0.18); }

/* ── 입력바 ── */
.input-zone {
  border-top: 1px solid rgba(255,255,255,0.08);
  padding: 11px 20px 16px;
  background: rgba(18,8,38,0.7);
  backdrop-filter: blur(20px);
  flex-shrink: 0;
}
.input-bar { display: flex; align-items: flex-end; gap: 10px; }

.icon-btn {
  font-size: 16px;
  color: rgba(255,255,255,0.45);
  padding: 8px;
  border-radius: 10px;
  flex-shrink: 0;
  transition: background 0.2s;
}
.icon-btn:hover { background: rgba(255,255,255,0.1); color: rgba(255,255,255,0.8); }

.msg-input {
  flex: 1;
  background: rgba(255,255,255,0.07);
  border: 1px solid rgba(255,255,255,0.15);
  border-radius: 12px;
  padding: 10px 14px;
  font-size: 13px;
  font-family: inherit;
  color: #fff;
  resize: none;
  line-height: 1.5;
  max-height: 120px;
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
  background: linear-gradient(135deg, #5EEAD4, #3BBFAD);
  color: #0d1a2e;
  border-radius: 12px;
  padding: 10px 18px;
  font-size: 13px;
  font-weight: 700;
  flex-shrink: 0;
  transition: opacity 0.2s, transform 0.1s;
}
.send-btn:not(:disabled):hover { opacity: 0.88; transform: translateY(-1px); }
.send-btn:disabled { opacity: 0.3; cursor: not-allowed; }
</style>

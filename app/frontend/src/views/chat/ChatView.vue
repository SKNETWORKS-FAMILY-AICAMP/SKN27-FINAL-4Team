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
import chatBg from '../../assets/chat-bg.png'
import { useChatRoom } from './composables/useChatRoom.js'

const {
  attachedImage,
  autoResize,
  canChooseAction,
  chooseSceneAction,
  clearImage,
  confirmExitSecret,
  displayAnimationClass,
  displayCharacter,
  displayCharacterImage,
  displayExpressionLabel,
  fileInputRef,
  inputRef,
  inputText,
  isCharacterSpeaking,
  isDragging,
  isRecording,
  isSecret,
  isTyping,
  latestAssistantMessage,
  latestSuggestion,
  latestUserMessage,
  logThreadRef,
  messages,
  moteStyle,
  onDragLeave,
  onDragOver,
  onDropImage,
  onPickImage,
  openChatLog,
  router,
  sceneActions,
  sceneMoodClass,
  sceneStatusText,
  sendMessage,
  showChatLog,
  showExitModal,
  skipCurrentDialogue,
  storyLightCount,
  sttSupported,
  threadRef,
  timeSceneClass,
  timeSceneLabel,
  toggleSecret,
  toggleStt,
  toggleTtsPref,
  ttsEnabled,
} = useChatRoom()
</script>

<style scoped src="./styles/chat-view.css"></style>

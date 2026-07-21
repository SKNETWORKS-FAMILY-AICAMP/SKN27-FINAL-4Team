import { computed, nextTick, onMounted, onUnmounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { chatApi } from '../../../api/chat.js'
import { useSecret } from '../../../composables/useSecret.js'
import { useStt } from '../../../composables/useStt.js'
import { useTts } from '../../../composables/useTts.js'
import {
  ACTIONS_BY_EMOTION,
  DISPLAY_CHARACTER_META,
  EMOTION_TO_EXPRESSION,
  EXPRESSION_ANIMATION,
  EXPRESSION_LABELS,
  OPENER_MSG,
} from '../config/chat.constants.js'
import { normalizeCharacterId, readStoredCharacter } from '../utils/chatCharacter.js'
import { getMoteStyle, getTimeScene } from '../utils/chatScene.js'
import { useChatImageAttachment } from './useChatImageAttachment.js'

export function useChatRoom() {
  const router = useRouter()
  const route = useRoute()

  const storedCharacter = readStoredCharacter()
  const displayCharacterId = ref(normalizeCharacterId(route.query.character || storedCharacter.characterId))
  const selectedExpression = ref('default')
  const { secret: isSecret, setSecret } = useSecret()
  const { playTask, stop: ttsStop } = useTts()
  const { isSupported: sttSupported, isRecording, start: sttStart, stop: sttStop } = useStt()

  const ttsEnabled = ref(localStorage.getItem('binteum_tts') !== 'off')
  const sessionId = ref(null)
  const coldStartDone = ref(false)
  const showExitModal = ref(false)
  const messages = ref([])
  const inputText = ref('')
  const isTyping = ref(false)
  const currentEmotion = ref('default')
  const threadRef = ref(null)
  const logThreadRef = ref(null)
  const inputRef = ref(null)
  const fileInputRef = ref(null)
  const showChatLog = ref(false)
  const userTurnCount = ref(0)
  const {
    attachedImage,
    clearImage,
    isDragging,
    onDragLeave,
    onDragOver,
    onDropImage,
    onPasteImage,
    onPickImage,
  } = useChatImageAttachment(isTyping)

  const displayCharacter = computed(() => (
    DISPLAY_CHARACTER_META[displayCharacterId.value] || DISPLAY_CHARACTER_META.otter
  ))
  const backendCharacter = computed(() => displayCharacter.value.backendCharacter)
  const character = backendCharacter
  const displayExpressionId = computed(() => (
    EMOTION_TO_EXPRESSION[currentEmotion.value] || selectedExpression.value
  ))
  const displayExpressionLabel = computed(() => (
    EXPRESSION_LABELS[displayExpressionId.value] || '기쁨'
  ))
  const displayCharacterImage = computed(() => (
    `/characters/${displayCharacterId.value}/${displayExpressionId.value}.png`
  ))
  const displayAnimationClass = computed(() => (
    EXPRESSION_ANIMATION[displayExpressionId.value] || 'anim-joy'
  ))

  const latestAssistantMessage = computed(() => (
    [...messages.value].reverse().find(message => message.role === 'assistant') || null
  ))
  const latestUserMessage = computed(() => (
    [...messages.value].reverse().find(message => message.role === 'user') || null
  ))
  const latestAssistantText = computed(() => {
    const message = latestAssistantMessage.value
    if (!message) return ''
    return (message.displayed !== undefined ? message.displayed : message.content) || ''
  })
  const isCharacterSpeaking = computed(() => {
    const message = latestAssistantMessage.value
    return !!message
      && message.displayed !== undefined
      && message.displayed !== message.content
      && !isTyping.value
  })
  const latestSuggestion = computed(() => {
    const message = [...messages.value]
      .reverse()
      .find(item => item.role === 'assistant' && item.suggestPage)
    if (!message) return null
    return message.displayed === undefined || message.displayed === message.content ? message : null
  })
  const canChooseAction = computed(() => {
    const message = latestAssistantMessage.value
    const revealDone = !!message
      && (message.displayed === undefined || message.displayed === message.content)
    return !!sessionId.value && revealDone && !isTyping.value && !isCharacterSpeaking.value
  })
  const sceneMoodClass = computed(() => `mood-${currentEmotion.value || 'normal'}`)
  const storyLightCount = computed(() => Math.min(5, Math.max(1, userTurnCount.value + 1)))
  const sceneActions = computed(() => (
    ACTIONS_BY_EMOTION[currentEmotion.value] || ACTIONS_BY_EMOTION.default
  ))

  const timeScene = getTimeScene()
  const timeSceneClass = timeScene.className
  const timeSceneLabel = timeScene.label

  const sceneStatusText = computed(() => {
    if (!sessionId.value) return '방으로 들어가는 중'
    if (isRecording.value) return '네 목소리를 듣는 중'
    if (isTyping.value) return `${displayCharacter.value.name}가 생각하는 중`
    if (isCharacterSpeaking.value) return `${displayCharacter.value.name}가 이야기하는 중`
    return `${displayCharacter.value.name}와 함께 머무는 중`
  })

  function toggleTtsPref() {
    ttsEnabled.value = !ttsEnabled.value
    localStorage.setItem('binteum_tts', ttsEnabled.value ? 'on' : 'off')
    if (!ttsEnabled.value) ttsStop()
  }

  let sttBaseText = ''
  function toggleStt() {
    if (isRecording.value) {
      sttStop()
      return
    }
    sttBaseText = inputText.value ? `${inputText.value.replace(/\s+$/, '')} ` : ''
    sttStart({
      onInterim: (text) => {
        inputText.value = (sttBaseText + text).slice(0, 300)
      },
      onFinal: (text) => {
        inputText.value = (sttBaseText + text).slice(0, 300)
        sttBaseText = `${inputText.value.replace(/\s+$/, '')} `
      },
      onEnd: () => {
        nextTick(() => autoResize())
      },
    })
  }

  // 기존 호출부와의 호환을 위해 유지하는 no-op이다.
  function clearIdleTimer() {}

  function animateReveal(message, durationSec, alignment, audioEl) {
    if (message.displayed === message.content) return
    if (message._revealTimer) clearInterval(message._revealTimer)

    const canSync = alignment
      && Array.isArray(alignment.chars)
      && alignment.chars.length > 0
      && audioEl
      && alignment.chars.join('') === message.content

    if (canSync) {
      const starts = alignment.starts
      message._revealTimer = setInterval(() => {
        const currentTime = audioEl.currentTime
        if (audioEl.ended || (audioEl.paused && currentTime === 0)) {
          clearInterval(message._revealTimer)
          message._revealTimer = null
          message.displayed = message.content
          return
        }
        let index = 0
        while (index < starts.length && starts[index] <= currentTime + 0.12) index += 1
        message.displayed = message.content.slice(0, index)
        scrollToBottom()
        if (index >= message.content.length) {
          clearInterval(message._revealTimer)
          message._revealTimer = null
        }
      }, 45)
      return
    }

    const total = message.content.length
    const durationMs = Math.max(
      800,
      (durationSec ? durationSec * 1000 : total * 55) * 0.93,
    )
    const startedAt = performance.now()
    message._revealTimer = setInterval(() => {
      const progress = Math.min(1, (performance.now() - startedAt) / durationMs)
      message.displayed = message.content.slice(0, Math.ceil(total * progress))
      scrollToBottom()
      if (progress >= 1) {
        clearInterval(message._revealTimer)
        message._revealTimer = null
      }
    }, 50)
  }

  function revealNow(message) {
    if (message._revealTimer) {
      clearInterval(message._revealTimer)
      message._revealTimer = null
    }
    message.displayed = message.content
  }

  function pushAssistant(text, extra = {}) {
    const message = { _tempId: Date.now(), role: 'assistant', content: text, ...extra }
    if (message.tts_task_id && ttsEnabled.value) {
      message.displayed = ''
      messages.value.push(message)
      const target = messages.value[messages.value.length - 1]
      playTask(message.tts_task_id, {
        onStart: (duration, alignment, audioEl) => (
          animateReveal(target, duration, alignment, audioEl)
        ),
        onFail: () => animateReveal(target, null, null, null),
      })
      setTimeout(() => {
        if (target.displayed !== target.content && !target._revealTimer) revealNow(target)
      }, 30000)
      return target
    }

    message.displayed = ''
    messages.value.push(message)
    const target = messages.value[messages.value.length - 1]
    animateReveal(target, null, null, null)
    return target
  }

  async function initSession() {
    try {
      const coords = await getCoordsOrNull()
      const session = await chatApi.startSession(
        character.value,
        isSecret.value,
        coords,
        ttsEnabled.value,
      )
      sessionId.value = session.session_id
      coldStartDone.value = true
      userTurnCount.value = 0

      const opener = session.opener
        || OPENER_MSG[character.value]?.(isSecret.value)
        || '안녕! 뭐 하고 있었어?'
      pushAssistant(opener, { tts_task_id: session.tts_task_id })
    } catch {
      sessionId.value = null
      messages.value.push({
        _tempId: Date.now(),
        role: 'assistant',
        content: '서버랑 연결이 잠깐 안 되고 있어요. 새로고침 한 번 해줄래요?',
      })
    }
  }

  function getCoordsOrNull() {
    return new Promise((resolve) => {
      if (!navigator.geolocation) {
        resolve(null)
        return
      }
      navigator.geolocation.getCurrentPosition(
        position => resolve({
          lat: position.coords.latitude,
          lon: position.coords.longitude,
        }),
        () => resolve(null),
        { timeout: 3000 },
      )
    })
  }

  function endSessionBeacon() {
    if (!sessionId.value) return
    const blob = new Blob(
      [JSON.stringify({ session_id: sessionId.value })],
      { type: 'application/json' },
    )
    navigator.sendBeacon('/api/session/end/', blob)
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
    if (logThreadRef.value) {
      logThreadRef.value.scrollTop = logThreadRef.value.scrollHeight
    }
  }

  async function sendMessage() {
    const content = inputText.value.trim()
    const image = attachedImage.value
    if ((!content && !image) || isTyping.value) return
    if (!sessionId.value) {
      messages.value.push({
        _tempId: Date.now(),
        role: 'assistant',
        content: '연결이 끊겨 있어요. 새로고침 해주세요!',
      })
      return
    }

    clearIdleTimer()
    userTurnCount.value += 1
    messages.value.push({ _tempId: Date.now(), role: 'user', content, image })
    inputText.value = ''
    attachedImage.value = null
    if (inputRef.value) inputRef.value.style.height = 'auto'
    isTyping.value = true
    await scrollToBottom()

    try {
      const response = await chatApi.sendChat(
        sessionId.value,
        content,
        character.value,
        isSecret.value,
        image,
        ttsEnabled.value,
      )
      pushAssistant(response.message.text, {
        id: response.message_id ?? undefined,
        emotion_label: response.emotion_label,
        tts_task_id: response.tts_task_id,
        suggestPage: response.ui?.suggest_page || null,
        suggestLabel: response.ui?.suggest_label || null,
      })
      if (response.emotion_label) currentEmotion.value = response.emotion_label
    } catch {
      messages.value.push({
        _tempId: Date.now(),
        role: 'assistant',
        content: '잠시 연결이 끊겼어요. 다시 시도해 줄래요? 🙏',
      })
    } finally {
      isTyping.value = false
      await scrollToBottom()
    }
  }

  async function toggleSecret() {
    clearIdleTimer()
    endSessionBeacon()
    setSecret(!isSecret.value)
    messages.value = []
    coldStartDone.value = false
    await initSession()
    router.replace({
      query: {
        character: displayCharacterId.value,
        secret: isSecret.value ? 'on' : undefined,
      },
    })
  }

  async function confirmExitSecret() {
    showExitModal.value = false
    clearIdleTimer()
    if (sessionId.value) {
      try {
        await chatApi.endSession(sessionId.value)
      } catch (error) {
        console.error('Failed to end secret session:', error)
      }
    }
    setSecret(false)
    messages.value = []
    coldStartDone.value = false
    await initSession()
    router.replace({ query: { character: displayCharacterId.value } })
  }

  function autoResize(event) {
    event.target.style.height = 'auto'
    event.target.style.height = `${event.target.scrollHeight}px`
  }

  async function scrollToBottom() {
    await nextTick()
    if (threadRef.value) threadRef.value.scrollTop = threadRef.value.scrollHeight
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
    endSessionBeacon()
  })

  return {
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
    latestAssistantText,
    latestSuggestion,
    latestUserMessage,
    logThreadRef,
    messages,
    moteStyle: getMoteStyle,
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
  }
}

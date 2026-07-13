// Web Speech API 기반 음성 입력(STT) — 중간발표 심사위원 피드백 반영 (2026-07-10)
// 브라우저 내장 인식기(ko-KR): 별도 서버·비용 없음. Chrome/Edge 지원, 미지원 브라우저는 버튼 숨김.
// TTS(귀로 듣기) + STT(말로 하기) = "지친 날엔 타이핑도 부담" 양방향 완성.
import { ref } from 'vue'

export function useStt() {
  const isSupported = typeof window !== 'undefined' &&
    !!(window.SpeechRecognition || window.webkitSpeechRecognition)
  const isRecording = ref(false)
  let recognition = null

  /** 음성 인식 시작.
   * handlers.onInterim(text) — 말하는 중간 결과 (실시간 미리보기용)
   * handlers.onFinal(text)   — 확정된 문장
   * handlers.onEnd()         — 인식 종료 (자동 침묵 감지 포함) */
  function start(handlers = {}) {
    if (!isSupported || isRecording.value) return
    const SR = window.SpeechRecognition || window.webkitSpeechRecognition
    recognition = new SR()
    recognition.lang = 'ko-KR'
    recognition.interimResults = true
    recognition.continuous = false          // 한 호흡 단위 — 침묵이 오면 자동 종료
    recognition.maxAlternatives = 1

    recognition.onresult = (e) => {
      let interim = '', final = ''
      for (let i = e.resultIndex; i < e.results.length; i++) {
        const r = e.results[i]
        if (r.isFinal) final += r[0].transcript
        else interim += r[0].transcript
      }
      if (interim) handlers.onInterim?.(interim)
      if (final) handlers.onFinal?.(final.trim())
    }
    recognition.onerror = (e) => {
      console.warn('[stt] 인식 오류:', e.error)   // no-speech / not-allowed 등
      isRecording.value = false
    }
    recognition.onend = () => {
      isRecording.value = false
      handlers.onEnd?.()
    }
    recognition.start()
    isRecording.value = true
  }

  function stop() {
    try { recognition?.stop() } catch (e) { /* noop */ }
    isRecording.value = false
  }

  return { isSupported, isRecording, start, stop }
}

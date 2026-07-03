// ElevenLabs TTS — 자동 1회 재생 (2026-07-02 확정).
// 메시지가 나타날 때 한 번 읽어주고 끝. 서버도 재생 후 즉시 파기하므로 다시 듣기 없음.
import { chatApi } from '../api/chat.js'

let currentAudio = null
let pollAbort = null

const POLL_INTERVAL_MS = 700
const POLL_MAX_TRIES = 40            // eleven_v3 생성이 느릴 수 있어 최대 ~28초 대기

export function useTts() {
  function stop() {
    if (pollAbort) { pollAbort.aborted = true; pollAbort = null }
    if (currentAudio) {
      try { currentAudio.pause(); currentAudio.currentTime = 0 } catch (e) { /* noop */ }
      currentAudio = null
    }
  }

  /** 새 메시지의 음성을 준비되는 대로 1회 자동 재생. */
  async function playTask(taskId) {
    if (!taskId) return
    stop()                            // 이전 재생 중이면 끊고 최신 메시지 우선

    const abort = { aborted: false }
    pollAbort = abort

    for (let i = 0; i < POLL_MAX_TRIES; i++) {
      if (abort.aborted) return
      try {
        const data = await chatApi.getTts(taskId)
        if (data.status === 'done' && data.audio_url) {
          if (abort.aborted) return
          currentAudio = new Audio(data.audio_url)   // 서버는 이 요청 후 즉시 파기
          currentAudio.onended = () => { currentAudio = null }
          currentAudio.play().catch(() => {
            // 자동재생 차단(페이지 로드 직후 첫인사 등) — 첫 상호작용 때 1회 재생 재시도.
            // 오디오 데이터는 이미 받아와 있어 서버 파기와 무관하게 재생 가능.
            const audio = currentAudio
            const resume = () => {
              cleanup()
              if (audio && audio === currentAudio) audio.play().catch(() => { currentAudio = null })
            }
            const cleanup = () => {
              window.removeEventListener('pointerdown', resume)
              window.removeEventListener('keydown', resume)
            }
            window.addEventListener('pointerdown', resume, { once: true })
            window.addEventListener('keydown', resume, { once: true })
          })
          return
        }
        if (data.status === 'failed') return   // 텍스트만으로 진행 (음성은 부가 기능)
      } catch (e) {
        return
      }
      await new Promise(r => setTimeout(r, POLL_INTERVAL_MS))
    }
  }

  return { playTask, stop }
}

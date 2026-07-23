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
      if (currentAudio._blobUrl) URL.revokeObjectURL(currentAudio._blobUrl)   // blob 메모리 회수 (2026-07-23)
      currentAudio = null
    }
  }

  /** 새 메시지의 음성을 준비되는 대로 1회 자동 재생.
   * handlers.onStart(durationSec) — 실제 재생이 시작될 때 (텍스트 동기 타이핑용)
   * handlers.onFail() — 생성 실패/타임아웃/자동재생 차단 (텍스트 즉시 표시용) */
  async function playTask(taskId, handlers = {}) {
    if (!taskId) { handlers.onFail?.(); return }
    stop()                            // 이전 재생 중이면 끊고 최신 메시지 우선

    const abort = { aborted: false }
    pollAbort = abort

    for (let i = 0; i < POLL_MAX_TRIES; i++) {
      if (abort.aborted) return
      try {
        const data = await chatApi.getTts(taskId)
        if (data.status === 'done' && data.audio_url) {
          if (abort.aborted) return
          // 2026-07-23: URL 직결 재생 → blob 통재생으로 교체.
          // 서버가 1회 응답 후 즉시 파기하는데, 크롬은 오디오를 두 번에 나눠
          // 요청할 때가 있어 두 번째 요청이 404 → 음성이 문장 중간에 끊겼다.
          // 통째로 받아 손에 쥐고 재생하면 서버 파기와 무관해진다 (파기 원칙 유지).
          const audioResp = await fetch(data.audio_url, { credentials: 'include' })
          if (!audioResp.ok) { handlers.onFail?.(); return }
          const blobUrl = URL.createObjectURL(await audioResp.blob())
          if (abort.aborted) { URL.revokeObjectURL(blobUrl); return }
          currentAudio = new Audio(blobUrl)
          currentAudio._blobUrl = blobUrl
          currentAudio.onended = () => { URL.revokeObjectURL(blobUrl); currentAudio = null }
          // 실제 소리가 나기 시작하는 순간 → 텍스트 동기 타이핑 시작
          const audioEl = currentAudio
          audioEl.addEventListener('playing', () => {
            const d = isFinite(audioEl.duration) && audioEl.duration > 0 ? audioEl.duration : null
            handlers.onStart?.(d, data.alignment || null, audioEl)
          }, { once: true })
          currentAudio.play().catch(() => {
            // 자동재생 차단(페이지 로드 직후 첫인사 등) — 첫 상호작용 때 1회 재생 재시도.
            // 오디오 데이터는 이미 받아와 있어 서버 파기와 무관하게 재생 가능.
            handlers.onFail?.()       // 차단 시 텍스트는 기다리지 않고 바로 표시
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
        if (data.status === 'failed') { handlers.onFail?.(); return }   // 텍스트만으로 진행
      } catch (e) {
        handlers.onFail?.()
        return
      }
      await new Promise(r => setTimeout(r, POLL_INTERVAL_MS))
    }
    handlers.onFail?.()               // 폴링 타임아웃
  }

  return { playTask, stop }
}

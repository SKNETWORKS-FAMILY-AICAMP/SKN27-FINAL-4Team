import axios from 'axios'
import { getCsrfToken, getClientId } from './client.js'

const http = axios.create({
  baseURL: '/api',
  withCredentials: true,
  headers: { 'Content-Type': 'application/json' },
})

http.interceptors.request.use((config) => {
  config.headers['X-Binteumsai-Client-Id'] = getClientId()
  const csrfToken = getCsrfToken()
  if (csrfToken) {
    config.headers['X-CSRFToken'] = csrfToken
  }
  return config
})

// v6.0 응답 래퍼 {success, data, error} 해제
function unwrap(res) {
  const body = res.data
  if (body && body.success === false) {
    const err = new Error(body.error?.message || 'API 오류')
    err.code = body.error?.code
    throw err
  }
  return body?.data ?? body
}

export const chatApi = {
  // ═══════════ v6.0 API (API_명세서 v6.0) ═══════════

  /** 세션 시작 — 친구 컨셉: 날씨/시간/닉네임 첫인사(opener) 반환.
   *  coords={lat,lon} 있으면 날씨 반영 (없어도 시간대 인사로 정상 동작)
   *  checkinId 있으면 오늘의 체크인 맥락을 반영, tts=false면 오프너 TTS 생성 스킵(음소거, 크레딧 절약) */
  async startSession(characterId, isSecret, coords = null, checkinId = null, tts = true) {
    return unwrap(await http.post('/session/start/', {
      character_id: characterId,
      is_secret: isSecret,
      checkin_id: checkinId,
      lat: coords?.lat,
      lon: coords?.lon,
      tts,
    }))
  },

  /** 대화 턴 (텍스트 즉시 + tts_task_id로 오디오 폴링)
   *  image: data URL(선택) — 사진 첨부 시 멀티모달로 전달, 저장은 안 함
   *  tts=false면 음소거 사용자용으로 서버가 TTS 생성 자체를 건너뜀 */
  async sendChat(sessionId, message, characterId, isSecret, image = null, tts = true) {
    return unwrap(await http.post('/chat/', {
      session_id: sessionId,
      character_id: characterId,
      message,
      is_secret: isSecret,
      image,
      tts,
    }))
  },

  /** TTS 오디오 폴링 */
  async getTts(taskId) {
    return unwrap(await http.get(`/tts/${taskId}/`))
  },

  /** MBTI 질문 요청 (10초 유휴 타이머에서 호출) */
  async mbtiNextQuestion(sessionId) {
    return unwrap(await http.get('/mbti/next-question/', {
      params: { session_id: sessionId },
    }))
  },

  /** 세션 종료 (시크릿 캐시 즉시 파기) */
  async endSession(sessionId) {
    return unwrap(await http.post('/session/end/', { session_id: sessionId }))
  },
}

import axios from 'axios'

const http = axios.create({
  baseURL: '/api',
  withCredentials: true,
  headers: { 'Content-Type': 'application/json' },
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

  /** 세션 시작 — 콜드스타트 미완료면 감정 선택지 반환.
   *  skipColdStart=true면 감정 선택 생략 (이미 답한 사용자의 새 세션) */
  async startSession(characterId, isSecret, skipColdStart = false) {
    return unwrap(await http.post('/session/start/', {
      character_id: characterId,
      is_secret: isSecret,
      skip_cold_start: skipColdStart,
    }))
  },

  /** 콜드스타트 감정 선택 제출 → 후속 질문 */
  async coldStart(sessionId, selectedEmotion) {
    return unwrap(await http.post('/session/cold-start/', {
      session_id: sessionId,
      selected_emotion: selectedEmotion,
    }))
  },

  /** 대화 턴 (텍스트 즉시 + tts_task_id로 오디오 폴링) */
  async sendChat(sessionId, message, characterId, isSecret) {
    return unwrap(await http.post('/chat/', {
      session_id: sessionId,
      character_id: characterId,
      message,
      is_secret: isSecret,
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

  /** MBTI 저장 동의/거부 (시크릿 모드) */
  async mbtiConsent(sessionId, consent) {
    return unwrap(await http.post('/mbti/consent/', {
      session_id: sessionId,
      consent,
    }))
  },

  /** 계획도움 (Tavily 장소 추천) */
  async planSupport(sessionId, locationContext) {
    return unwrap(await http.post('/plan-support/', {
      session_id: sessionId,
      location_context: locationContext,
    }))
  },

  /** 세션 종료 (시크릿 캐시 즉시 파기) */
  async endSession(sessionId) {
    return unwrap(await http.post('/session/end/', { session_id: sessionId }))
  },

  // ═══════════ 레거시 v5.x (유지 — 추천질문/날씨/피드백) ═══════════

  async suggestQuestions(sessionId) {
    const { data } = await http.post(`/chat/sessions/${sessionId}/questions/`)
    return data
  },

  async getWeatherOpener(lat = '', lon = '') {
    const { data } = await http.get('/chat/weather-opener/', {
      params: { lat, lon }
    })
    return data
  }
}

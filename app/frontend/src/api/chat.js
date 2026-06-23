import axios from 'axios'

const http = axios.create({
  baseURL: '/api',
  withCredentials: true,
  headers: { 'Content-Type': 'application/json' },
})

export const chatApi = {
  async createSession(character, isSecret) {
    const { data } = await http.post('/chat/sessions/create/', {
      character,
      is_secret: isSecret,
    })
    return data
  },

  async getSessions() {
    const { data } = await http.get('/chat/sessions/')
    return data
  },

  async sendMessage(sessionId, content) {
    const { data } = await http.post(`/chat/sessions/${sessionId}/messages/`, { content })
    return data
  },

  // SCR-004 이너 카운슬 — 백엔드 엔드포인트 추가 예정
  async runCouncil(sessionId, userInput, turn) {
    const { data } = await http.post(`/chat/sessions/${sessionId}/council/`, {
      user_input: userInput,
      turn,
    })
    return data
  },
}

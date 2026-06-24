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

  async recommendTea(sessionId) {
    const { data } = await http.post(`/chat/sessions/${sessionId}/tea/`)
    return data
  },

  async recommendBgm(sessionId) {
    const { data } = await http.post(`/chat/sessions/${sessionId}/bgm/`)
    return data
  },

  async suggestQuestions(sessionId) {
    const { data } = await http.post(`/chat/sessions/${sessionId}/questions/`)
    return data
  },

  async runCouncil(sessionId, userInput, turn) {
    const { data } = await http.post(`/chat/sessions/${sessionId}/council/`, {
      user_input: userInput,
      turn,
    })
    return data
  },
}

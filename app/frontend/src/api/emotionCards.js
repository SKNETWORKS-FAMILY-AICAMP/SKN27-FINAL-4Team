import axios from 'axios'
import { getClientId, getCsrfToken } from './client.js'

const http = axios.create({ baseURL: '/api/emotion-cards', withCredentials: true, headers: { 'Content-Type': 'application/json' } })

http.interceptors.request.use((config) => {
  config.headers['X-Binteumsai-Client-Id'] = getClientId()
  const csrfToken = getCsrfToken()
  if (csrfToken) config.headers['X-CSRFToken'] = csrfToken
  return config
})

export const emotionCardsApi = {
  analyze: async (payload) => (await http.post('/analyze/', payload)).data,
  updateAnalysis: async (id, payload) => (await http.patch(`/analyses/${id}/`, payload)).data,
  createScene: async (id) => (await http.post(`/analyses/${id}/scene/`)).data,
  generate: async (sceneId, payload) => (await http.post(`/scenes/${sceneId}/generate/`, payload)).data,
  getJob: async (jobId) => (await http.get(`/jobs/${jobId}/`)).data,
  getCard: async (cardId) => (await http.get(`/${cardId}/`)).data,
  feedback: async (cardId, payload) => (await http.post(`/${cardId}/feedback/`, payload)).data,
  today: async () => (await http.get('/today/')).data,
  resetTodayUsage: async () => (await http.post('/today/reset/')).data,
}

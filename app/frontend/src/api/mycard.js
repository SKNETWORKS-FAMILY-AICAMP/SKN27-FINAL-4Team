import axios from 'axios'
import { getClientId, getCsrfToken } from './client.js'

const http = axios.create({
  baseURL: '/api',
  withCredentials: true,
  headers: { 'Content-Type': 'application/json' },
})

http.interceptors.request.use((config) => {
  config.headers['X-Binteumsai-Client-Id'] = getClientId()
  const csrfToken = getCsrfToken()
  if (csrfToken) config.headers['X-CSRFToken'] = csrfToken
  return config
})

export const myCardApi = {
  async bootstrap() {
    const { data } = await http.get('/mycard/bootstrap/')
    return data
  },

  async generate(payload) {
    const { data } = await http.post('/mycard/generate/', payload)
    return data
  },

  async save(cardId) {
    const { data } = await http.post(`/mycard/${cardId}/save/`)
    return data
  },
}
